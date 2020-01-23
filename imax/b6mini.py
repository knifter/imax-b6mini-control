import usb.core
import usb.util

IMAX_VID = 0x0000
IMAX_PID = 0x0001

CMD_GET_DEVINFO = 0x57
CMD_GET_CHG     = 0x55
CMD_GET_SYS     = 0x5A
CMD_U1          = 0x5F
CMD_STOP        = 0xFE
MODE_CHARGE     = 0x00
MODE_DISCHARGE  = 0x01
MODE_STORAGE    = 0x02
MODE_FASTCHARGE = 0x03
BAT_LIPO        = 0x00
BAT_LILO        = 0x01
BAT_LIFE        = 0x02
BAT_LIHV        = 0x03
BAT_NIMH        = 0x04
BAT_NICD        = 0x05
BAT_PB          = 0x06

class B6Mini:
    def __init__(self):
        self._device = get_usb_device(IMAX_VID, IMAX_PID)

    def stop(self):
        reply = self._send([0x03, CMD_STOP, 0x00])

    def charge(self, battery_type, cells, current, max_voltage):
        reply = self._charge_cmd(battery_type, cells, MODE_CHARGE, current, 0.0, 0.0, max_voltage)

    def discharge(self, battery_type, cells, current, min_voltage):
        reply = self._charge_cmd(battery_type, cells, MODE_DISCHARGE, 0.0, current, min_voltage, 0.0)

    def get_charge_info(self):
        reply = self._send([ 0x03, CMD_GET_CHG, 0x00 ])
        return ChargeInfo(reply)

    def print_charge_info(self):
        info = self.get_charge_info()
        print("state: ", info.state_str())
        print("mah: ", info.mah)
        print("time: ", info.time_sec)
        print("voltage: %.04f" % info.voltage)
        print("current: ", info.current)
        print("Cells:", info.cells)

    def get_sys_info(self):
        reply = self._send([ 0x03, CMD_GET_SYS, 0x00 ])
        return SysInfo(reply)

    def print_sys_info(self):
        info = self.get_sys_info
        print("cycleTime: ", info.cycleTime)
        print("timeLimitOn: ", info.timeLimitOn)
        print("timeLimit: ", info.timeLimit)
        print("capLimitOn: ", info.capLimitOn)
        print("capLimit: ", info.capLimit)
        print("keyBuzz: ", info.keyBuzz)
        print("sysBuzz: ", info.sysBuzz)
        print("inDClow: ", info.inDClow)
        print("tempLimit", info.tempLimit)
        print("voltage: ", info.voltage)
        print("cells: ", info.cells)

    def get_dev_info():
        reply = self._send([ 0x03, CMD_GET_DEVINFO, 0x00 ])
        return DevInfo(reply)

    def print_dev_info(self):
        info = get_dev_info()
        print("sw_version: ", info.sw_version)
        print("hw_version: ", info.hw_version)

    # PRIVATEs
    def _charge_cmd(self, bat, cells, mode, chg_current, dsc_current, voltage_low, voltage_high):
        cmd = [ 0x16, 0x05, 0x00 ]
        cmd.append(bat)
        cmd.append(cells)
        cmd.append(mode)
        append2b(cmd, int(chg_current * 1000))
        append2b(cmd, int(dsc_current * 1000))
        append2b(cmd, int(voltage_low * 1000))
        append2b(cmd, int(voltage_high * 1000))
        cmd = cmd + [0x00]*8
        return self._send(cmd, debug=True)

    def _send(self, cmd, debug = False):
        tries = 5
        data = [0x0F]
        data += cmd
        data.append(calc_checksum(data))
        data += [0xFF, 0xFF]
        while(1):
            tries -= 1
            try:
                if debug:
                    print("SEND: ", hexstr(data))
                assert self._device.write(0x1, data) == len(data)
                reply = self._device.read(0x81, 64, 500)
                break
            except usb.core.USBError:
                if tries == 0:
                    raise
                print("Send Failed... retry.")
                pass
        if debug:
            print("REPLY: ", hexstr(reply))
        return reply

# Helpers
def read2b(p):
    return next(p)*256 + next(p)

def append2b(arr, num):
    msb = int(num/256)
    arr.append(msb)
    arr.append(num - 256*msb)

def calc_checksum(cmd):
    sum = 0
    for v in cmd[2:]:
        sum += v
    return sum & 0x000000FF

def hexstr(d):
    r = []
    for v in d:
        r.append("0x%02X" % v)
    return r

def get_usb_device(vid, pid):
    # find our device
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if(dev == None):
        raise ValueError("Device %04x:%04x not found" % (vid, pid))
    print("Device: ", dev)

    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    try:
        dev.set_configuration()
    except usb.core.USBError as u:
        raise ValueError("Can't set (1st) configuration on device %04x:%04x: %s" % (vid, pid, str(u)))

    # get an endpoint instance
    #cfg = dev.get_active_configuration()
    #intf = cfg[(0,0)]
    # print("CONFIG:\n", cfg)

    return dev

class ChargeInfo:
    _STATES = ["0", "BUSY", "IDLE", "FINISH", "ERROR"]
    def __init__(self, b):
        assert len(b) > 29

        p = iter(b[4:])
        self.state = next(p)
        self.mah = read2b(p)
        self.time_sec = read2b(p)
        # print("time: %d:%d" % (int(secs/60), secs-60*int(secs/60) ))
        self.voltage = read2b(p) / 1000.0
        self.current = read2b(p)
        self.tempExt = next(p)
        self.tempInt = next(p)
        self.impedanceInt = read2b(p)
        self.cells = []
        for cellnr in range(6):
            self.cells.append(read2b(p)/1000.0)

    def state_str(self):
        try:
            return self._STATES[self.state]
        except IndexError:
            return "<%d>" % self.state

class SysInfo:
    def __init__(self, b):
        assert len(b) > 32

        p = iter(b[4:])
        self.cycleTime = next(p)
        self.timeLimitOn = next(p)
        self.timeLimit = read2b(p)
        self.capLimitOn = next(p)
        self.capLimit = read2b(p)
        self.keyBuzz = next(p)
        self.sysBuzz = next(p)
        self.inDClow = read2b(p) / 1000.0
        next(p)
        next(p)
        self.tempLimit = next(p)
        self.voltage = read2b(p) / 1000.0
        self.cells = []
        for cellnr in range(6):
            self.cells.append( read2b(p) / 1000.0 )

class DeviceInfo:
    def __init__(self, b):
        assert len(b) > 19
        p = iter(b[5:])
        self.core_type = [next(p) for n in range(6)]
        self.upgrade_type = next(p)
        self.is_encrypt = next(p)
        self.customer_id = read2b(p)
        self.language_id = next(p)
        self.sw_version = next(p) + next(p)/100.0;
        self.hw_version = next(p);
