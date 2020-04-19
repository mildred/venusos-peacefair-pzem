#!/usr/bin/env python2

"""
A class to put a simple service on the dbus, according to victron standards, with constantly updating
paths. See example usage below. It is used to generate dummy data for other processes that rely on the
dbus. See files in dbus_vebus_to_pvinverter/test and dbus_vrm/test for other usage examples.
To change a value while testing, without stopping your dummy script and changing its initial value, write
to the dummy data via the dbus. See example.
https://github.com/victronenergy/dbus_vebus_to_pvinverter/tree/master/test
"""
import gobject
from gobject import idle_add
import platform
import argparse
import logging
import sys
import os
import pzem
import dbus
import dbus.service

import pzem
import time

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext/velib_python'))
from vedbus import VeDbusService, VeDbusItemImport

softwareVersion = '0.1'

AC_INPUT=0
AC_OUTPUT=1

class DbusPzemInverterService:
    def __init__(self, devname, address, position=AC_OUTPUT):
        bus = (dbus.SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus(private=True))
        self._dbusservice = VeDbusService("com.victronenergy.pvinverter.pzem-%s-%d" % (devname, address), bus=bus)
        self._error_message = ""
        self._disconnect = 0

        pre = ''

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path(pre+'/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path(pre+'/Mgmt/ProcessVersion', softwareVersion)
        self._dbusservice.add_path(pre+'/Mgmt/Connection', "Device %d on Modbus-RTU %s" % (address, devname))

        # Create the mandatory objects
        self._dbusservice.add_path(pre+'/DeviceInstance', address)
        self._dbusservice.add_path(pre+'/ProductId', address)
        self._dbusservice.add_path(pre+'/ProductName', "PZEM-016")
        self._dbusservice.add_path(pre+'/FirmwareVersion', 0)
        self._dbusservice.add_path(pre+'/HardwareVersion', 0)
        self._dbusservice.add_path(pre+'/Connected', 0)

        # Readings
        self._dbusservice.add_path(pre+'/Ac/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/Frequency', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L1/PowerFactor', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L2/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L2/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L2/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L2/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L3/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L3/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Ac/L3/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/Position', position)
        self._dbusservice.add_path(pre+'/StatusCode', 7)
        self._dbusservice.add_path(pre+'/DeviceType', "PZEM-016")
        self._dbusservice.add_path(pre+'/ErrorCode', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path(pre+'/ErrorMessage', "")

    def update(self, instr):
        pre = ''
        try:
            r = instr.readings()
            self._dbusservice[pre+'/Ac/Energy/Forward']    = r['energy']
            self._dbusservice[pre+'/Ac/Power']             = r['power']
            self._dbusservice[pre+'/Ac/Current']           = r['current']
            self._dbusservice[pre+'/Ac/Voltage']           = r['voltage']
            self._dbusservice[pre+'/Ac/L1/Current']        = r['current']
            self._dbusservice[pre+'/Ac/L1/Energy/Forward'] = r['energy']
            self._dbusservice[pre+'/Ac/L1/Power']          = r['power']
            self._dbusservice[pre+'/Ac/L1/Voltage']        = r['voltage']
            self._dbusservice[pre+'/Ac/L1/Frequency']      = r['frequency']
            self._dbusservice[pre+'/Ac/L1/PowerFactor']    = r['pow_factor']
            self._dbusservice[pre+'/ErrorCode']            = 0
            self._dbusservice[pre+'/ErrorMessage']         = ""
            self._dbusservice[pre+'/Connected']            = 1
            self._error_message = ""
        except Exception as e:
            self._dbusservice[pre+'/ErrorCode']            = 1
            self._dbusservice[pre+'/ErrorMessage']         = str(e)
            if self._disconnect > 60:
                self._dbusservice[pre+'/Connected']        = 0
            self._disconnect += 1
            self._error_message = str(e)

    def _get_text(self, path, value):
        pre = ''
        if path == pre+"/ErrorCode": return self._error_message
        if path == pre+"/Position":
            if value == 0: return "AC Input 1"
            if value == 1: return "AC Output"
            if value == 2: return "AC Input 2"
        if os.path.basename(path) == "Forward":     return ("%.3FkWh" % (float(value) / 1000.0))
        if os.path.basename(path) == "Reverse":     return ("%.3FkWh" % (float(value) / 1000.0))
        if os.path.basename(path) == "Power":       return ("%.1FW" % (float(value)))
        if os.path.basename(path) == "Current":     return ("%.3FA" % (float(value)))
        if os.path.basename(path) == "Voltage":     return ("%.1FV" % (float(value)))
        if os.path.basename(path) == "PowerFactor": return ("%.2F" % (float(value)))
        if os.path.basename(path) == "Frequency":   return ("%.1FHz" % (float(value)))
        return ("%.0F" % (float(value)))

class DbusPzemGridMeterService:
    def __init__(self, devname, address):
        bus = (dbus.SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus(private=True))
        self._dbusservice = VeDbusService("com.victronenergy.grid.pzem_%s_%d" % (devname, address))
        self._error_message = ""
        self._disconnect = 0

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', softwareVersion)
        self._dbusservice.add_path('/Mgmt/Connection', "Device %d on Modbus-RTU %s" % (address, devname))

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', address)
        self._dbusservice.add_path('/ProductId', address)
        self._dbusservice.add_path('/ProductName', "PZEM-016")
        self._dbusservice.add_path('/FirmwareVersion', 0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 0)

        # Readings
        self._dbusservice.add_path('/Ac/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Energy/Reverse', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Energy/Reverse', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/Frequency', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L1/PowerFactor', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L2/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L2/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L2/Energy/Reverse', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L2/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L2/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L3/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L3/Energy/Forward', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L3/Energy/Reverse', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/L3/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/DeviceType', "PZEM-016")
        self._dbusservice.add_path('/ErrorCode', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/ErrorMessage', "")

    def update(self, instr):
        try:
            r = instr.readings()
            self._dbusservice['/Ac/Energy/Forward']    = r['energy']
            self._dbusservice['/Ac/Power']             = r['power']
            self._dbusservice['/Ac/Current']           = r['current']
            self._dbusservice['/Ac/Voltage']           = r['voltage']
            self._dbusservice['/Ac/L1/Current']        = r['current']
            self._dbusservice['/Ac/L1/Energy/Forward'] = r['energy']
            self._dbusservice['/Ac/L1/Power']          = r['power']
            self._dbusservice['/Ac/L1/Voltage']        = r['voltage']
            self._dbusservice['/Ac/L1/Frequency']      = r['frequency']
            self._dbusservice['/Ac/L1/PowerFactor']    = r['pow_factor']
            self._dbusservice['/ErrorCode']            = 0
            self._dbusservice['/ErrorMessage']         = ""
            self._dbusservice['/Connected']            = 1
            self._error_message = ""
        except Exception as e:
            self._dbusservice['/ErrorCode']            = 1
            self._dbusservice['/ErrorMessage']         = str(e)
            if self._disconnect > 60:
                self._dbusservice['/Connected']        = 0
            self._disconnect += 1
            self._error_message = str(e)

    def _get_text(self, path, value):
        if path == "/ErrorCode": return self._error_message
        elif os.path.basename(path) == "Forward":     return ("%.3FkWh" % (float(value) / 1000.0))
        elif os.path.basename(path) == "Reverse":     return ("%.3FkWh" % (float(value) / 1000.0))
        elif os.path.basename(path) == "Power":       return ("%.1FW" % (float(value)))
        elif os.path.basename(path) == "Current":     return ("%.3FA" % (float(value)))
        elif os.path.basename(path) == "Voltage":     return ("%.1FV" % (float(value)))
        elif os.path.basename(path) == "PowerFactor": return ("%.2F" % (float(value)))
        elif os.path.basename(path) == "Frequency":   return ("%.1FHz" % (float(value)))
        else: return ("%.0F" % (float(value)))

class DbusPzem016Service:
    def __init__(self, devname, address):
        bus = (dbus.SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus(private=True))
        self._dbusname = "fr.mildred.pzemvictron2020.pzem016.%s-%d" % (devname, address)
        self._dbusservice = VeDbusService(self._dbusname, bus=bus)
        self._error_message = ""
        self._disconnect = 0

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', softwareVersion)
        self._dbusservice.add_path('/Mgmt/Connection', "Device %d on Modbus-RTU %s" % (address, devname))

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', address)
        self._dbusservice.add_path('/ProductId', address)
        self._dbusservice.add_path('/ProductName', "PZEM-016")
        self._dbusservice.add_path('/FirmwareVersion', 0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 0)

        # Readings
        self._dbusservice.add_path('/Ac/Current', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/TotalEnergy', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Power', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Voltage', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/Frequency', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/Ac/PowerFactor', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/DeviceType', "PZEM-016")
        self._dbusservice.add_path('/ErrorCode', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/ErrorMessage', "")

    def update(self, instr):
        try:
            #print("Updating %s" % self._dbusname)
            r = instr.readings()
            self._dbusservice['/Ac/TotalEnergy']    = r['energy']
            self._dbusservice['/Ac/Power']          = r['power']
            self._dbusservice['/Ac/Current']        = r['current']
            self._dbusservice['/Ac/Voltage']        = r['voltage']
            self._dbusservice['/Ac/Frequency']      = r['frequency']
            self._dbusservice['/Ac/PowerFactor']    = r['pow_factor']
            self._dbusservice['/ErrorCode']         = 0
            self._dbusservice['/ErrorMessage']      = ""
            self._dbusservice['/Connected']         = 1
            self._error_message = ""
        except Exception as e:
            #print("%s error: %s" % (self._dbusname, e))
            self._dbusservice['/ErrorCode']         = 1
            self._dbusservice['/ErrorMessage']      = str(e)
            if self._disconnect > 60:
                self._dbusservice['/Connected']     = 0
            self._disconnect += 1
            self._error_message = str(e)

    def _get_text(self, path, value):
        if path == "/ErrorCode": return self._error_message
        elif os.path.basename(path) == "TotalEnergy": return ("%.3FkWh" % (float(value) / 1000.0))
        elif os.path.basename(path) == "Power":       return ("%.1FW" % (float(value)))
        elif os.path.basename(path) == "Current":     return ("%.3FA" % (float(value)))
        elif os.path.basename(path) == "Voltage":     return ("%.1FV" % (float(value)))
        elif os.path.basename(path) == "PowerFactor": return ("%.2F" % (float(value)))
        elif os.path.basename(path) == "Frequency":   return ("%.1FHz" % (float(value)))
        else: return ("%.0F" % (float(value)))

class DbusMockMultiplusService:
    def __init__(self, devname, address):
        self.imported = {}
        self.bus = (dbus.SessionBus(private=True) if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus(private=True))
        self._dbusservice = VeDbusService("com.victronenergy.vebus.mock-multiplus-%s-%s" % (devname, address), bus=self.bus)
        self.bus.add_signal_receiver(self.dbus_name_owner_changed, signal_name='NameOwnerChanged')

        logging.info('Searching dbus for vebus devices...')
        for serviceName in self.bus.list_names():
            self.scan_dbus_service(serviceName)
        logging.info('Finished search for vebus devices')

        self._error_message = ""
        self._disconnect = 0

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', softwareVersion)
        self._dbusservice.add_path('/Mgmt/Connection', "Mock-Multiplus spawned by %s" % (devname,))

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', address)
        self._dbusservice.add_path('/ProductId', address)
        self._dbusservice.add_path('/ProductName', "MockMultiplus")
        self._dbusservice.add_path('/FirmwareVersion', 0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 0)

        # Readings
        self._dbusservice.add_path('/Energy/InverterToAcOut', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/DeviceType', "MockMultiplus")
        self._dbusservice.add_path('/ErrorCode', 0, gettextcallback=self._get_text)
        self._dbusservice.add_path('/ErrorMessage', "")

    def update(self, _instr):
        try:
            pass
        except Exception as e:
            self._dbusservice['/ErrorCode']         = 1
            self._dbusservice['/ErrorMessage']      = str(e)
            if self._disconnect > 60:
                self._dbusservice['/Connected']     = 0
            self._disconnect += 1
            self._error_message = str(e)

    def _get_text(self, path, value):
        if path == "/ErrorCode": return self._error_message
        elif path.startswith("/Energy/"): return ("%.3FkWh" % (float(value) / 1000.0))
        else: return ("%.0F" % (float(value)))

    def dbus_name_owner_changed(self, name, oldOwner, newOwner):
        # decouple, and process in main loop
        idle_add(self.process_name_owner_changed, name, oldOwner, newOwner)

    def process_name_owner_changed(self, name, oldOwner, newOwner):
        logging.debug('D-Bus name owner changed. Name: %s, oldOwner: %s, newOwner: %s' % (name, oldOwner, newOwner))

        if newOwner != '':
            self.scan_dbus_service(name)
        else:
            pass # Would remove imported service/path

    def is_service_pzem016(self, serviceName):
        return serviceName.split('.')[0:4] == ['fr', 'mildred', 'pzemvictron2020', 'pzem016']

    def is_service_battery(self, serviceName):
        return serviceName.split('.')[0:3] == ['com', 'victronenergy', 'battery']

    def scan_dbus_service(self, serviceName):
        if self.is_service_battery(serviceName):
            self.import_value(serviceName, '/History/DischargedEnergy')
            #self.import_value(serviceName, '/TimeToGo')

    def import_value(self, serviceName, path):
        if serviceName not in self.imported: self.imported[serviceName] = {}
        if path in self.imported[serviceName]: return
        self.imported[serviceName][path] = VeDbusItemImport(self.bus, serviceName, path, self.import_value_changed)

    def import_value_changed(self, serviceName, path, changes):
        if self.is_service_battery(serviceName):
            #if path == '/TimeToGo':
            #    print("%s%s = %s" % (serviceName, path, changes['Value']))
            if path == '/History/DischargedEnergy':
                self._dbusservice['/Energy/InverterToAcOut'] = changes['Value']


class DbusPzemService:
    def __init__(self, tty, devices):
        self._services = {}
        self._instruments = {}
        devname = os.path.basename(tty)

        for addr in devices:
            if devices[addr] == 'grid':
                self._services[addr] = DbusPzemGridMeterService(devname, addr)
                self._instruments[addr] = pzem.Instrument(tty, addr, 'ac')
            elif devices[addr] == 'inverter0':
                self._services[addr] = DbusPzemInverterService(devname, addr, position=AC_INPUT)
                self._instruments[addr] = pzem.Instrument(tty, addr, 'ac')
            elif devices[addr] == 'inverter':
                self._services[addr] = DbusPzemInverterService(devname, addr)
                self._instruments[addr] = pzem.Instrument(tty, addr, 'ac')
            elif devices[addr] == 'pzem-016':
                self._services[addr] = DbusPzem016Service(devname, addr)
                self._instruments[addr] = pzem.Instrument(tty, addr, 'ac')
            elif devices[addr] == 'mock-multiplus':
                self._services[addr] = DbusMockMultiplusService(devname, addr)
                self._instruments[addr] = None
            else:
                raise Exception("Unknown device type %s" % devices[addr])

        gobject.timeout_add(1000, self._update)

    def _update(self):
        for addr in self._services:
            service, instr = self._services[addr], self._instruments[addr]
            service.update(instr)
        return True

# === All code below is to simply run it from the commandline for debugging purposes ===

# It will created a dbus service called com.victronenergy.pvinverter.output.
# To try this on commandline, start this program in one terminal, and try these commands
# from another terminal:
# dbus com.victronenergy.pvinverter.output
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward GetValue
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward SetValue %20
#
# Above examples use this dbus client: http://code.google.com/p/dbus-tools/wiki/DBusCli
# See their manual to explain the % in %20

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--device", dest="device", default="/dev/ttyUSB0",
                      help="tty device", metavar="ADDRESS")
    parser.add_option("-a", "--address", dest="address", type="int",
                      help="device address", metavar="ADDRESS", default=0xF8)
    parser.add_option("--change-address", dest="change_address", type="int",
                      help="change device address", metavar="ADDRESS")
    parser.add_option("-t", "--type", dest="type",
                      help="Type (ac, dc)", metavar="TYPE")
    parser.add_option("--debug", dest="debug", action="store_true", help="set logging level to debug")
    (opts, args) = parser.parse_args()

    logging.basicConfig(level=(logging.DEBUG if opts.debug else logging.INFO))

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    DbusPzemService(
        tty=opts.device,
        devices={
            #10: "pzem-016",
            20: "pzem-016",
            'MultiPlus': "mock-multiplus"
        })

    logging.info("Starting mainloop, responding only on events")
    mainloop = gobject.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
