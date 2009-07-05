# coding: utf-8
import ctypes
import logging
import string
import subprocess
import sys
import time
import usb

logger = logging.getLogger('PyCNiC')
logging.basicConfig(level=logging.DEBUG)

TIMEOUT = 500 # timeout for usb read or write
VENDOR_ID = 0x9999
PRODUCT_ID = 0x0002
PRODUCT_NAME = u'TinyCN'

def byte2hex(byteStr):
    """Converts a byte string to its hex representation

    >>> from pycnic import byte2hex
    >>> byte2hex('\xFF\xFF')
    'FF FF'
    >>> byte2hex('\xAA\xAA\xAA')
    'AA AA AA'

    """
    try:
        pretty = u' (%s)' % unicode(byteStr)
    except UnicodeDecodeError:
        pretty = ''
    return ''.join(["%02X " % ord(x) for x in byteStr] ).strip() #+ pretty


def byte2int(byteStr):
    """Converts a little endian (ie reversed) byte string to the corresponding integer

    >>> from pycnic import byte2int
    >>> byte2int('\xFF\xFF')
    65535
    >>> byte2int('\x40\x01')
    320
    >>> byte2int('\x40\x01\x01\x01')
    16843072
    """
    if len(byteStr) == 0:
        return None
    assert(len(byteStr) <= 4)
    return int(''.join(["%02X" % ord(x) for x in reversed(byteStr)]),16)


def int2byte(integer):
    """Converts an integer to its corresponding little endian (ie reversed) 4-byte string

    >>> from pycnic import int2byte
    >>> print int2byte(0x00)
    \x00\x00\x00\x00
    >>> print int2byte(0x01)
    \x01\x00\x00\x00
    >>> print int2byte(0xFF)
    \xff\x00\x00\x00
    >>> print int2byte(0x746F)
    \x6F\x74\x00\x00
    >>> print int2byte(0x746F746F)
    \x6F\x74\x6F\x74
    """
    #not reversed : return ''.join([ chr(integer%(256**i)/256**(i-1)) for i in range(4,0,-1)])
    return ''.join([ chr(integer%(256**i)/256**(i-1)) for i in range(1,5)])

def int2tuple(integer):
    """Converts an integer to its corresponding little endian (ie reversed) 4-byte tuple

    >>> from pycnic import int2tuple
    >>> print int2tuple(0x00)
    (0, 0, 0, 0)
    >>> print int2tuple(0x01)
    (1, 0, 0, 0)
    >>> print int2tuple(0xFF)
    (255, 0, 0, 0)
    >>> print int2tuple(0x746F)
    (111, 116, 0, 0)
    >>> print int2tuple(0x746F746F)
    (111, 116, 111, 116)
    """
    #not reversed : return ''.join([ chr(integer%(256**i)/256**(i-1)) for i in range(4,0,-1)])
    return tuple([ int(integer%(256**i)/256**(i-1)) for i in range(1,5)])


def tuple2hex(tup):
    """Converts a data tuple of integers to its hex representation

    >>> from pycnic import tuple2hex
    >>> tuple2hex( (1,2,3) )
    '01 02 03'
    >>> tuple2hex( (30,40,110) )
    '1E 28 6E'
    """
    return ' '.join(["%02X" % i for i in tup])

def tuple2str(tup):
    """Converts a data tuple of integers to its string representation

    >>> from pycnic import tuple2str
    >>> tuple2str( (84, 105, 110, 121, 67, 78) )
    'TinyCN'
    """
    return ''.join([chr(i) for i in tup])

def tuple2int(tup):
    """Converts a tuple of int to the equivalent int

    >>> from pycnic import tuple2int
    >>> tuple2int( (12, 01, 01) )
    786689
    >>> tuple2int( (01, 00) )
    256
    >>> tuple2int( (00, 02) )
    2
    """
    return int(''.join(["%02X" % i for i in tup]),16)


class Motor(object):
    res_x = None # resolution in step/mm
    res_y = None
    res_z = None
    res_a = None
    inv_x = None # direction
    inv_y = None
    inv_z = None
    inv_a = None
    dim_x = None # table dimension
    dim_y = None
    dim_z = None
    dim_a = None
    micro_step = None
    current_x = None
    current_y = None
    current_z = None
    current_a = None
    state = None
    path_length = None

class Tool(object):
    numerateur = 1
    denominateur = 1
    speed = None


class TinyCN(object):

    handle = None
    device = None
    name = None
    motor = None
    tool = None
    res = None
    interface_num = 0

    def __init__(self, fake=False, debug=False):
        self.fake = fake
        self.debug = debug
        self.set_debug(self.debug)
        if not self.fake:
            self.on()

        self.motor = Motor()
        self.tool = Tool()


    def off(self):
        logger.debug(u'Switching off...')
        if self.handle is not None:
            logger.debug(u'Releasing interface...')
            self.handle.releaseInterface()
            self.handle = None


    def on(self):
        if self.handle is not None:
            return

        busses = usb.busses()

        # try to find the device
        self.device = None
        for bus in busses:
            for device in bus.devices:
                if device.idVendor == VENDOR_ID \
                  and device.idProduct == PRODUCT_ID:
                    logger.info(u"found %s!", PRODUCT_NAME)
                    self.device = device
                    break

        if self.device is None:
            raise IOError(u'No device found')

        self.handle = self.device.open()
        logger.debug(u'Claiming interface... %s' % self.interface_num)
        self.handle.claimInterface(self.interface_num)

        # misc tests and inits
        self.set_prompt(0)
        self.name = self.read_name()
        self.set_fifo_depth(255) # 255 pulses
        self.set_pulse_width(64) # 5µs (?)
        self.res = self.get_speed_calc()


    def set_debug(self, debug):
        """takes one arg : debug = True or False
        """
        assert(debug is True or debug is False)
        global DEBUG
        self.debug = debug
        if debug is True:
            DEBUG = True
        else:
            DEBUG = False

    def __del__(self):
        self.off()

    def write(self, buffer, alt=0):
        logger.debug(u'    we write the command %s...' % tuple2hex(buffer))
        if not self.fake:
            #P1 : in 0x81, out 0x01
            #P2 : in 0x82, out 0x02
            bytes = self.handle.bulkWrite(0x01+alt, buffer, TIMEOUT)
            logger.debug(u'    %s bytes written' % bytes)

    def read(self, size, alt=0):
        if self.fake: return
        logger.debug(u'    Now we read the result...')
        #P1 : in 0x81, out 0x01
        #P2 : in 0x82, out 0x02
        buffer = self.handle.bulkRead(0x81 + alt, size, TIMEOUT)
        logger.debug(u'    %s bytes read: %s' % (len(buffer), tuple2hex(buffer)))
        return buffer

    def read_firmware(self):
        logger.debug(u'Reading firmware version...')
        self.write((0x18, 0x82, 0x04, 0x00))
        version = self.read(32)
        logger.debug(u'  Got firmware version: %s' % tuple2str(version))
        return version

    def stop(self):
        logger.debug(u'Stopping...')
        self.write((0x80, 0x1B))

    def restart(self):
        logger.debug(u'Restarting...')
        self.write((0x80, 0x1C))

    def clear_cmd(self):
        logger.debug(u'Clearing cmd...')
        self.write((0x80, 0x09))

    def read_cmd(self):
        logger.debug(u'Reading cmd...')
        self.write((0x80, 0x08))
        return self.read(16)

    def open_buffer(self):
        logger.debug(u'Opening buffer...')
        self.write((0x80, 0x12))

    def close_buffer(self):
        logger.debug(u'Closing buffer...')
        self.write((0x80, 0x13))

    def clear_buffer_rx(self):
        logger.debug(u'Clearing rx buffer...')
        self.write((0x80, 0x14))

    def clear_buffer_tx(self):
        logger.debug(u'Clearing tx buffer...')
        self.write((0x80, 0x15))

    def set_prompt(self, prompt):
        logger.info(u'Setting prompt = "%s"' % prompt)
        command = (0x18, 0x03, 0x08, 0x00)
        state = (prompt, 0, 0, 0)
        self.write(command + state)

    def wait(self, pulses):
        """Wait during the specified number of pulses
        """
        logger.debug(u'Waiting %s pulses...' % tuple2str(pulses))
        command = (0x18, 0x06, 0x08, 0x00)
        self.write(command + int2tuple(pulses))

    def get_prompt(self):
        logger.debug(u'Reading prompt')
        self.write((0x18, 0x83, 0x04, 0x00))
        prompt = self.read(8)
        logger.debug(u'  Got prompt: %s' % tuple2str(prompt))
        return prompt

    def get_status(self):
        logger.debug(u'Reading status...')
        self.write((0x18, 0x89, 0x04, 0x00))
        value = tuple2int(self.read(8)[4:8])
        logger.debug(u'  Got status: %s' % value)
        return value

    def get_x(self):
        logger.debug(u'Reading X')
        self.write((0x10, 0x81, 0x04, 0x00))
        value = tuple2int(self.read(8)[4:8])
        logger.debug(u'  Got X: %s' % tuple2str(value))
        return value

    def zero_x(self):
        logger.debug(u'Resetting X to zero')
        command = (0x11, 0x01, 0x04, 0x00)
        self.write(command)

    def read_name(self):
        command = (0x18, 0x85, 0x04, 0x00)
        self.write(command)
        self.name = tuple2str(self.read(32))
        logger.debug(u'Read name = %s', self.name)
        return self.name

    def get_serial(self):
        self.write((0x18, 0x84, 0x04, 0x00))
        return self.read(10)

    def set_fifo_depth(self, depth):
        logger.debug(u'Setting fifo pulse generator to %s pulses' % depth)
        command = (0x18, 0x10, 0x08, 0x00)
        hex_depth = int2tuple(depth)
        self.write(command + hex_depth)

    def set_pulse_width(self, width):
        logger.debug(u'Setting pulse width to %s ' % width)
        command = (0x13, 0x08, 0x08, 0x00)
        hex_width = int2tuple(width)
        self.write(command + hex_width)

    def get_speed_max(self):
        """set the max speed for the ramp
        """
        logger.debug(u'Reading max speed...')
        self.write((0x12, 0x85, 0x04, 0x00))
        speed = self.read(8)[4:8]
        logger.debug(u'  Got max speed = %s' % byte2hex(speed))
        return tuple2int(speed)

    def set_speed_max(self, speed, resolution):
        logger.debug(u'Setting speed max to %s mm/min' % speed)
        command = (0x12, 0x05, 0x08, 0x00)
        speed = speed / 60.0 # convert to mm/s
        speed = speed * resolution * self.tool.numerateur / self.tool.denominateur # FIXME check
        hexspeed = int2tuple(int(speed))
        logger.debug(u'  hex speed max = %s' % byte2hex(hexspeed))
        self.write(command + hexspeed)

    def get_speed_calc(self):
        logger.debug(u'Reading speed calc...')
        self.write((0x12, 0x89, 0x04, 0x00))
        speed_calc = self.read(8)
        logger.debug(u'  Got speed calc = %s' % tuple2hex(speed_calc))
        return speed_calc

    def set_speed(self, speed, resolution):
        logger.debug(u'Setting speed to %s mm/min' % speed)
        command = (0x12, 0x06, 0x08, 0x00)
        speed = speed / 60.0 # convert to mm/s
        speed = speed * resolution * self.tool.numerateur / self.tool.denominateur # FIXME check
        tuplespeed = int2tuple(int(speed))
        logger.debug(u'  hex speed = %s' % tuple2hex(tuplespeed))
        self.write(command + tuplespeed)

    def get_speed_acca(self):
        logger.debug(u'Reading acca...')
        self.write((0x12, 0x81, 0x04, 0x00))
        value = tuple2int(self.read(8)[4:8])
        logger.debug(u'  Got acca : %s' % value)
        return value

    def set_speed_acca(self, acc):
        """Set the slope of the acceleration curve (1 to 10)
        """
        logger.debug(u'Setting acca to %s' % acc)
        command = (0x12, 0x01, 0x08, 0x00)
        tupleacc = int2tuple(int(acc))
        logger.debug(u'  hex acc = %s' % tuple2hex(tupleacc))
        self.write(command + tupleacc)

    def set_speed_accb(self, acc):
        """Set the slope of the acceleration curve.
        Must be 1 for a step motor
        """
        logger.debug(u'Setting accb to %s mm/min' % acc)
        command = (0x12, 0x02, 0x08, 0x00)
        tupleacc = int2tuple(int(acc))
        logger.debug(u'  hex acc = %s' % tuple2hex(tuplracc))
        self.write(command + tupleacc)

    def move_ramp_xyz(self, x, y, z):
        raise NotImplementedError

    def move_ramp_x(self, steps):
        """move to x using ramp
        """
        logger.debug(u'move x to step %s' % steps)
        self.write((0x14, 0x01, 0x08, 0x00) + int2tuple(steps))

    def move_var_x(self, steps, start, stop, direction):
        """move to x with variable speed
        steps : the target step
        start : the starting speed
        stop : the target speed
        direction : 'up' or 'down' (accelerate or decelerate)
        """
        if direction == 'up':
            cmd = (0x14, 0xA1, 0x10, 0x00)
        elif direction == 'down':
            cmd = (0x14, 0x21, 0x10, 0x00)
        else:
            raise Exception(u'Wrong direction')
        logger.debug(u'move var x to step %s' % steps)
        self.write(cmd + int2tuple(steps) + int2tuple(start) + int2tuple(stop))

    def move_const_x(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move x to step %s' % steps)
        self.write((0x14, 0x11, 0x08, 0x00) + int2tuple(steps))

    def move_const_y(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move y to step %s' % steps)
        self.write((0x14, 0x12, 0x08, 0x00) + int2tuple(steps))

    def move_const_z(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move z to step %s' % steps)
        self.write((0x14, 0x13, 0x08, 0x00) + int2tuple(steps))

    def move_const_a(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move a to step %s' % steps)
        self.write((0x14, 0x14, 0x08, 0x00) + int2tuple(steps))

    def get_state(self):
        logger.debug(u'get_state')
        self.write((0x80, 0x19))
        state = self.read(4, alt=1)
        logger.debug(byte2hex(state))
        return state

    def get_buffer_state(self):
        logger.debug(u'get_buffer_state')
        self.write((0x80, 0x18))
        state = self.read(4, alt=1)
        logger.debug(byte2hex(state))
        return state

    def get_fifo_count(self):
        logger.debug(u'get_fifo_count')
        self.write((0x80, 0x10), alt=1)
        state = self.read(4, alt=1)
        logger.debug(byte2hex(state))
        return tuple2int(state)

