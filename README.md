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

Installation
------------

Copy the data directory over the data directory on your VenusOS device, then run
`rcS.local` to install the files not belonging to `/data` in the right place.

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


Resources
---------

- PZEM-016 and PZEM-017 manuals are available as PDF scans here.
- Get root on Venus: https://www.victronenergy.com/live/ccgx:root_access
- Driver implem: https://github.com/victronenergy/venus/wiki/howto-add-a-driver-to-Venus
- Data structure: https://github.com/victronenergy/venus/wiki/dbus#vebus-systems-multis-quattros-inverters
    - com.victronenergy.grid
    - com.victronenergy.pvinverter
    - com.victronenergy.battery
- Get permission on tty for devloppment: `sudo setfacl -R -m u:$USER:rwx /dev/ttyUSB*`

Requirements
------------

- Python 2.7
- pyserial (pip2 install pyserial==3.4)
- pymodbus (pip2 install pymodbus==1.3.2)
