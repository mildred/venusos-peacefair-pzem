Victron VenusOS driver for Peacefair energy meters
==================================================

This reposicoty contains the Venus OS system service to make the Peacefair
PZEM-016 and PZEM-017 data available on Venus OS and VRM.

The primary use case is to monitor the Victron MultiPlus AC input and output to
get energy consumption. newer MultiPlus have this built-in but older versions
don't. This data is necessary to know how much you consumed energy from your
solar panels or from the grid.

Secondary use case is to make use of the DC meter to monitor additional DC
battery chargers on the system, such as a wind turbine charger. This part is not
yet fully done.

TODO
----

- finish pzem service calculation MockMultiplus and put in separate service
- finish service to save energy timeseries
- service to display enery timeseries

Architecture
------------

The PZEM devices are set up on the system to monitor the MultiPlus AC input and
AC output. They are connected to an RS-485 bus, which is connected to the master
device, an RS-485 USB device that is made available on linux as a ttyUSB device.
On top of RS-485, it's talking using the Modbus-RTU protocol.

For some reason, I could not make the device connect on the same bus, and I had
to connect a single PZEM device to a single USB dongle.

On VenusOS, the serial-starter service monitors serial devices connected to the
board, and spawn a pzem service per serial device. This is thanks to the
configuration file in `/data/conf/serial-starter.d/pzem-usb.conf`.

The pzem service will talk to the PZEM devices using modbus-rtu and export the
information to the dBus system bus. This is automatically recognized as a sensor
and integrated in Venus/VRM.

### How the computations works

It takes two PZEM-016 (AC meters), one is connected to AcIn1 and the other to
AcOut ports of the MultiPlus. All the reports goes to:

- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/Current`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/EnergyTotal`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/Power`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/Voltage`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/Frequency`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/Ac/PowerFactor`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/ErrorCode`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/ErrorMessage`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/DeviceAddress`
- `fr.mildred.pzemvictron2020.pzem016.tty*-*/DeviceModel`

You need a BMV-700 too with:

- `com.victronenergy.battery.*/History/ChargedEnergy`
- `com.victronenergy.battery.*/History/DischargedEnergy`

It will measure energy and report a `com.victronenergy.vebus` bus name using:

- `com.victronenergy.vebus.*/Energy/InverterToAcOut`(t) = `com.victronenergy.battery.*/History/DischargedEnergy`(t)
- `com.victronenergy.vebus.*/Energy/AcIn1ToAcOut`(dt) = `fr.mildred.pzemvictron2020.pzem016.ACOut/Ac/EnergyTotal`(dt) - `com.victronenergy.battery.*/History/DischargedEnergy`(dt)
- `com.victronenergy.vebus.*/Energy/AcIn1ToInverter`(dt) = `fr.mildred.pzemvictron2020.pzem016.ACIn1/Ac/EnergyTotal`(dt) - `com.victronenergy.vebus.*/Energy/AcIn1ToAcOut`(dt)

Notation:

- `metric`(t): metric at time of computation
- `metric`(t-1): metric as it was last computation
- `metric`(dt) = `metric`(t) - `metric`(t-1)

It assumes that energy coming out of the battery is always going to AcOut
through the inverter. In case the VenusOS is not working, metrics are lost for
that time (unless the t-1 metrics are stored on disk).

Installation
------------

Copy the data directory over the data directory on your VenusOS device, then run
`rcS.local` to install the files not belonging to `/data` in the right place.
See `deploy.sh`.

PZEM devices have in persistent memory a modbus address which is by default 1.
You can use the tool in `data/pzem/pzem-info.py` to query that information and
change this address. To have this working, a single device must be connected to
the RS-485 bus at a time.

mapping from Modbus slave address and the sensor kind is done statically in
`data/pzem/pzem-dbus.py` at the end of the file:

    DbusPzemService(
        tty=opts.device,
        devices={
            10: "inverter0",
            20: "inverter",
        })

This means that device at address `10` is to be declared in Venus as the port 0
of an inverter (1st AC input of a MultiPlus). And the device at address `20` is
to be declared as default port of an inverter (port 1, AC output of a
MultiPlus).

Developement
------------

Quick feedback loop:

- edit source code
- push your code: `./deploy.sh`
- test your code on VenusOS: `/data/pzem/pzem-dbus.py -d /dev/ttyUSBx`

Useful commands:

- dBus introspection: `dbus --system [BUS_NAME [OBJECT_PATH [METHOD]]]`
- device introspection: `udevadm info /dev/ttyUSB0` (to find the USB device that
  is not vendored by Victron, for me that's the RS485 adapter)
- service management: `cd /service/.../`
    - bring up: `svc -u`
    - bring down: `svc -d`


Resources
---------

- PZEM-016 and PZEM-017 manuals are available as PDF scans here.
- Get root on Venus: https://www.victronenergy.com/live/ccgx:root_access
- Driver implem: https://github.com/victronenergy/venus/wiki/howto-add-a-driver-to-Venus
- Data structure: https://github.com/victronenergy/venus/wiki/dbus#vebus-systems-multis-quattros-inverters
    - com.victronenergy.grid
    - com.victronenergy.pvinverter
    - com.victronenergy.battery
    - com.victronenergy.vebus
- Get permission on tty for devloppment: `sudo setfacl -R -m u:$USER:rwx /dev/ttyUSB*`
- Nim: https://nim-lang.org/
- javascript charts: http://gionkunz.github.io/chartist-js
- timeseries logging:
    - http://discretelogics.com/doc/teafiles.py/teafiles.html
    - https://github.com/unicredit/nim-teafiles

Requirements
------------

- Python 2.7
- pyserial (pip2 install pyserial==3.4)
- pymodbus (pip2 install pymodbus==1.3.2)
- BMV-700 firmware at least 3.08: *Fixed issue with Charged/Discharged Energy & Cumulative Ah (aka Total Ah Drawn) counters: the counters could get stuck at a certain value and become 'insensitive' for (small) changes*
