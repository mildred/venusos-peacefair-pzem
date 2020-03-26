#!/usr/bin/env python2

import pzem
import time

if __name__ == "__main__":
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
    (opts, args) = parser.parse_args()

    print("pzem-info: Display current device info")

    inst = pzem.Instrument(opts.device, opts.address, opts.type)

    print(inst.readings())
    print(inst.deviceinfo())

    if opts.change_address != None:
        inst.change_address(opts.change_address)

        time.sleep(1)
        print(inst.deviceinfo())
