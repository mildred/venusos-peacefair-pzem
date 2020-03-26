import minimalmodbus

def instrument(serial, address):
    inst = minimalmodbus.Instrument(serial, address, debug=False)
    inst.serial.timeout = 0.1
    inst.serial.baudrate = 9600
    inst.serial.stopbits = 2
    return inst

def dc_decode_cur_range(range):
    if range == 0x0000: return 100.0
    if range == 0x0001: return  50.0
    if range == 0x0002: return 200.0
    if range == 0x0003: return 300.0
    return None

def dc_deviceinfo(inst):
    data = inst.read_registers(0x0000, 4, 0x03)
    return {
        "alarm_hiv": round((data[0]*0.01),1),                   # Voltage(0.01V)
        "alarm_lov": round((data[1]*0.01),1),                   # Voltage(0.01V)
        "address":   data[2],
        "cur_range": dc_decode_cur_range(data[3]),
    }

def change_address(inst, addr):
    inst.write_register(0x002, addr, functioncode=0x06)

def dc_readings(inst):
    data = inst.read_registers(0x0000, 8, 0x04)
    return {
        "voltage":   round((data[0]*0.01),1),                   # Voltage(0.01V)
        "current":   round((data[1]*65536+data[2]*0.01),3),     # Current(0.01A)
        "power":     round((data[3]*65536+data[4]*0.1),1),      # Power(0.1W)
        "energy":    round((data[5]*65536+data[6]*1),0),        # Energy(1Wh)
        "alarm_hiv": data[6] != 0,
        "alarm_lov": data[7] != 0,
    }

def ac_deviceinfo(inst):
    data = inst.read_registers(0x0001, 2, 0x03)
    return {
        "alarm_pow": round((data[0]*1),1),                      # Power(1W)
        "address":   data[1],
    }

def ac_readings(inst):
    data = inst.read_registers(0x0000, 10, 0x04)
    return {
        "voltage":    round((data[0]*0.1),1),                    # Voltage(0.1V)
        "current":    round((data[2]*65536+data[1]*0.001),3),    # Current(0.001A)
        "power":      round((data[4]*65536+data[3]*0.1),1),      # Power(0.1W)
        "energy":     round((data[6]*65536+data[5]*1),0),        # Energy(1Wh)
        "frequency":  round((data[7]*0.1),1),                    # Frequency(0.1Hz)
        "pow_factor": round((data[8]*0.01),1),                   # Power Factor(0.01)
        "alarm_pow":  data[9] != 0,
    }

class Instrument:
    def __init__(self, serial, address, typ):
        self.serial = serial
        self.address = address
        self.instr = instrument(serial, address)
        self.type = typ

    def readings(self):
        if self.type == 'ac': return ac_readings(self.instr)
        if self.type == 'dc': return dc_readings(self.instr)

    def deviceinfo(self):
        if self.type == 'ac': return ac_deviceinfo(self.instr)
        if self.type == 'dc': return dc_deviceinfo(self.instr)

    def change_address(self, addr):
        change_address(self.instr, addr)
        self.address = addr
        self.instr = instrument(self.serial, addr)
