#!/usr/bin/env python2

import os
import sys
sys.path.insert(1, '/opt/victronenergy/vrmlogger/ext/velib_python')
for ext in os.listdir(os.path.join(os.path.dirname(__file__), 'ext')):
    sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext', ext))

###########################################################

import gobject
import platform
import argparse
import logging
import dbus
import dbus.service
import time
import datetime
import math

from teafiles.teafile import TeaFile
from vedbus import VeDbusService, VeDbusItemImport

###########################################################

class Metric:
    def __init__(self, path, datatype='f'):
        self._path = path
        self._datatype = datatype

    def name(self):
        return self._path[1:].replace('/', '_')

    def path(self):
        return self._path

    def datatype(self):
        return self._datatype

    def empty(self):
        return float('nan')

    def is_empty(self, val):
        return math.isnan(val)

    def cast(self, val):
        return float(val)

class TeaBusLogger:
    def __init__(self, fpath, bus, serviceName, metrics):
        self.metrics = metrics
        self.metric_imports = {}
        self.metric_values = {}
        self.bus = bus
        self.fpath = os.path.join(os.path.dirname(fpath), "by-minute-%s" % os.path.basename(fpath))
        if os.path.isfile(fpath):
            self.tf = TeaFile.openwrite(fpath)
        else:
            logging.debug('%s: fields=%s types=%s' % (fpath, ' '.join([m.name() for m in metrics]), ''.join([m.datatype() for m in metrics])))
            now = time.gmtime()
            self.tf = TeaFile.create(fpath,
                ' '.join([m.name() for m in metrics]),
                ''.join([m.datatype() for m in metrics]),
                serviceName,
                {
                    'year':  now.tm_year,
                    'month': now.tm_mon,
                    'day':   now.tm_mday,
                })

        self.startdate = datetime.date(
                int(self.tf.description.namevalues['year']),
                int(self.tf.description.namevalues['month']),
                int(self.tf.description.namevalues['day']))

        for m in metrics:
            logging.debug("Watch %s%s"%(serviceName, m.path()))
            self.metric_imports[m.path()] = VeDbusItemImport(self.bus, serviceName, m.path(), lambda x, y, z: self.import_value_changed(m, x, y, z))

        self.install_update()

    def close(self):
        self.started = False
        return self.tf.close()

    def install_update(self, _from_timer=False):
        self.started = True
        tick = time.time()
        now = time.gmtime(tick)
        if _from_timer or now.tm_sec == 0:
            if _from_timer: logging.debug("Install tick handler after initial timeout")
            else: logging.debug("Install tick handler")
            gobject.timeout_add_seconds(60, self.update)
            self.update()
        else:
            logging.debug("Install tick handler in %ds" % (60 - now.tm_sec))
            gobject.timeout_add(int(1e3 * (60 - now.tm_sec)), lambda: self.install_update(_from_timer=True))
        return not _from_timer

    def update(self):
        t = time.gmtime()
        n = self.slot_num(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
        num_empty = 0
        self.tf.seekend()
        while self.tf.itemcount < n:
            self.tf.write(*[m.empty() for m in self.metrics])
            num_empty += 1
        if num_empty > 0: logging.debug("Filled in with %d empty records", num_empty)
        values = [self.get_metric(m) for m in self.metrics]
        self.tf.seekitem(n)
        self.tf.write(*values)
        self.tf.flush()
        logging.debug("record %d: %s" % (n, repr(values)))
        #logging.debug("all items: %s" % ([ i for i in self.tf.items()]))
        #logging.debug("last 10 items: %s" % ([ i for i in self.tf.items(n - 10, n+1)]))
        return self.started

    def slot_num(self, year, month, day, hour, minute):
        dmin = hour * 60 + minute
        delta = datetime.date(year, month, day) - self.startdate
        num = delta.days * 24 * 60 + dmin
        #logging.debug("Slot num for %s %d/%d/%d %d:%d(%d) is %s %d" % (self.startdate, year, month, day, hour, minute, dmin, delta, num))
        return num

    def get_metric(self, metric):
        return metric.cast(self.metric_imports[metric.path()].get_value())
        #if metric.path() in self.metric_values:
        #    return metric.cast(self.metric_values[metric.path()])
        #else:
        #    return metric.empty()

    def import_value_changed(self, metric, serviceName, path, changes):
        logging.debug('%s%s imported %s' % (serviceName, path, changes['Value']))
        self.metric_values[metric.path()] = changes['Value']

class TeaBatteryBusLogger(TeaBusLogger):
    def __init__(self, fpath, bus, serviceName):
        TeaBusLogger.__init__(self, fpath, bus, serviceName, [
            Metric('/History/DischargedEnergy'),
            Metric('/History/ChargedEnergy')
        ])

class TeaLoggerService:
    def __init__(self, datadir, dbusPrivate=False):
        if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
            self.bus = dbus.SessionBus(private=dbusPrivate)
        else:
            self.bus = dbus.SystemBus(private=dbusPrivate)

        self.fpath = os.path.join(datadir, 'log-%s.tea')
        self.imported = {}
        self.bus.add_signal_receiver(self.dbus_name_owner_changed, signal_name='NameOwnerChanged')

        logging.info('Searching dbus for vebus devices...')
        for serviceName in self.bus.list_names():
            self.check_dbus_service(serviceName)
        logging.info('Finished search for vebus devices')

    def dbus_name_owner_changed(self, name, oldOwner, newOwner):
        # decouple, and process in main loop
        gobject.idle_add(self.process_name_owner_changed, name, oldOwner, newOwner)

    def process_name_owner_changed(self, name, oldOwner, newOwner):
        logging.debug('D-Bus name owner changed. Name: %s, oldOwner: %s, newOwner: %s' % (name, oldOwner, newOwner))

        if newOwner != '':
            self.check_dbus_service(name)
        else:
            pass # Would remove imported service/path

    def is_service_pzem016(self, serviceName):
        return serviceName.split('.')[0:4] == ['fr', 'mildred', 'pzemvictron2020', 'pzem016']

    def is_service_battery(self, serviceName):
        return serviceName.split('.')[0:3] == ['com', 'victronenergy', 'battery']

    def check_dbus_service(self, serviceName):
        if serviceName in self.imported:
            #logging.debug("%s already imported" % serviceName)
            return
        if self.is_service_battery(serviceName):
            self.imported[serviceName] = TeaBatteryBusLogger(self.fpath % serviceName, self.bus, serviceName)

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--datadir", dest="datadir", default="/data/tealog",
                      help="data directory", metavar="DIR")
    parser.add_option("--debug", dest="debug", action="store_true", help="set logging level to debug")
    (opts, args) = parser.parse_args()

    logging.basicConfig(level=(logging.DEBUG if opts.debug else logging.INFO))

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    TeaLoggerService(opts.datadir)

    logging.info("Starting mainloop, responding only on events")
    mainloop = gobject.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()

