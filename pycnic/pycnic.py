# coding: utf-8
import ctypes
import pylibusb as usb
import subprocess
import sys
import time
import logging

logger = logging.getLogger('PyCNiC')
logging.basicConfig(level=logging.DEBUG)

TIMEOUT = 500 # timeout for usb read or write
VENDOR_ID = 0x9999
PRODUCT_ID = 0x0002
PRODUCT_NAME = u'TinyCN'

def ByteToHex(byteStr):
    """Converts a byte string to its hex representation

        >>> from pycnic import ByteToHex
        >>> ByteToHex('\xFF\xFF')
        'FF FF'
        >>> ByteToHex('\xAA\xAA\xAA')
        'AA AA AA'

    """
    try:
        pretty = u' (%s)' % unicode(byteStr)
    except UnicodeDecodeError:
        pretty = ''
    return ''.join(["%02X " % ord(x) for x in byteStr] ).strip() #+ pretty


def ByteToInt(byteStr):
    """Converts a little endian (ie reversed) byte string to the corresponding integer

        >>> from pycnic import ByteToInt
        >>> ByteToInt('\xFF\xFF')
        65535
        >>> ByteToInt('\x40\x01')
        320
    """
    if len(byteStr) == 0:
        return None
    assert(len(byteStr) <= 4)
    return int(''.join(["%02X" % ord(x) for x in reversed(byteStr)]),16)


def IntToByte(integer):
    """Converts an integer to its corresponding little endian (ie reversed) byte string

    >>> from pycnic import IntToByte, ByteToHex
    >>> print IntToByte(0x00)
    \x00\x00\x00\x00
    >>> print IntToByte(0x01)
    \x01\x00\x00\x00
    >>> print IntToByte(0xFF)
    \xff\x00\x00\x00
    >>> print IntToByte(0x746F)
    \x6F\x74\x00\x00
    >>> print IntToByte(0x746F746F)
    \x6F\x74\x6F\x74
    """
    #not reversed : return ''.join([ chr(integer%(256**i)/256**(i-1)) for i in range(4,0,-1)])
    return ''.join([ chr(integer%(256**i)/256**(i-1)) for i in range(1,5)])

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
            usb.release_interface(self.handle, self.interface_num)

            logger.debug(u'closing handle...')
            usb.close(self.handle)

            self.handle = None


    def on(self):
        usb.init()
        if self.handle is not None:
            return

        if not usb.get_busses():
            usb.find_busses()
            usb.find_devices()

        busses = usb.get_busses()

        # try to find the device
        self.device = None
        for bus in busses:
            for device in bus.devices:
                if device.descriptor.idVendor == VENDOR_ID \
                  and device.descriptor.idProduct == PRODUCT_ID:
                    logger.info(u"found %s!", PRODUCT_NAME)
                    self.device = device
                    break

        if self.device is None:
            raise IOError(u'No device found')

        self.handle = usb.open(self.device)
        logger.debug(u'Claiming interface... %s' % self.interface_num)
        usb.claim_interface(self.handle, self.interface_num)

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
            usb.set_debug(True)
            DEBUG = True
        else:
            usb.set_debug(False)
            DEBUG = False

    def __del__(self):
        self.off()

    def write(self, command, alt=0):
        buffer = ctypes.create_string_buffer(len(command))
        buffer.value = command
        logger.debug(u'    we write the command %s...' % ByteToHex(buffer.raw))
        if not self.fake:
            #P1 : in 0x81, out 0x01
            #P2 : in 0x82, out 0x02
            bytes = usb.bulk_write(self.handle, 0x01+alt, buffer, TIMEOUT)
            logger.debug(u'    %s bytes written' % bytes)

    def read(self, size, alt=0):
        if self.fake: return
        buffer = ctypes.create_string_buffer(size)
        logger.debug(u'    Now we read the result...')
        #P1 : in 0x81, out 0x01
        #P2 : in 0x82, out 0x02
        bytes = usb.bulk_read(self.handle, 0x81 + alt, buffer, TIMEOUT)
        output = buffer.raw[0:bytes]
        logger.debug(u'    %s bytes read: %s' % (bytes, ByteToHex(output)))
        return output

    def read_firmware(self):
        logger.debug(u'Reading firmware version')
        self.write('\x18\x82\x04\x00')
        version = self.read(32)
        logger.debug(u'  Got firmware version: %s' % version)
        return version

    def stop(self):
        logger.debug(u'Stopping...')
        self.write('\x80\x1B')

    def restart(self):
        logger.debug(u'Restarting...')
        self.write('\x80\x1C')

    def clear_cmd(self):
        logger.debug(u'Clearing cmd...')
        self.write('\x80\x09')

    def read_cmd(self):
        logger.debug(u'Reading cmd...')
        self.write('\x80\x08')
        return self.read(16)

    def open_buffer(self):
        logger.debug(u'Opening buffer...')
        self.write('\x80\x12')

    def close_buffer(self):
        logger.debug(u'Closing buffer...')
        self.write('\x80\x13')

    def clear_buffer_rx(self):
        logger.debug(u'Clearing rx buffer...')
        self.write('\x80\x14')

    def clear_buffer_tx(self):
        logger.debug(u'Clearing tx buffer...')
        self.write('\x80\x15')

    def set_prompt(self, prompt):
        logger.info(u'Setting prompt %s' % prompt)
        command = '\x18\x03\x08\x00'
        hex_state = chr(prompt) + 3*chr(0)
        self.write(command + hex_state)

    def wait(self, pulses):
        """Wait during the specified number of pulses
        """
        logger.debug(u'Waiting %s pulses...' % pulses)
        command = '\x18\x06\x08\x00'
        self.write(command + IntToByte(pulses))

    def get_prompt(self):
        logger.debug(u'Reading prompt')
        self.write('\x18\x83\x04\x00')
        prompt = self.read(8)
        logger.debug(u'  Got prompt: %s' % prompt)
        return prompt

    def get_status(self):
        logger.debug(u'Reading status...')
        self.write('\x18\x89\x04\x00')
        value = ByteToInt(self.read(8)[4:8])
        logger.debug(u'  Got status: %s' % value)
        return value

    def get_x(self):
        logger.debug(u'Reading X')
        self.write('\x10\x81\x04\x00')
        value = ByteToInt(self.read(8)[4:8])
        logger.debug(u'  Got X: %s' % value)
        return value

    def zero_x(self):
        logger.debug(u'Resetting X to zero')
        command = '\x11\x01\x04\x00'
        self.write(command)

    def read_name(self):
        self.write('\x18\x85\x04\x00')
        self.name = self.read(32)
        logger.debug(u'Read name = %s', self.name)
        return self.name

    def get_serial(self):
        self.write('\x18\x84\x04\x00')
        return self.read(10)

    def set_fifo_depth(self, depth):
        logger.debug(u'Setting fifo pulse generator to %s pulses' % depth)
        command = '\x18\x10\x08\x00'
        hex_depth = IntToByte(depth)
        self.write(command + hex_depth)

    def set_pulse_width(self, width):
        logger.debug(u'Setting pulse width to %s ' % width)
        command = '\x13\x08\x08\x00'
        hex_width = IntToByte(width)
        self.write(command + hex_width)

    def get_speed_max(self):
        """set the max speed for the ramp
        """
        logger.debug(u'Reading max speed...')
        self.write('\x12\x85\x04\x00')
        speed = self.read(8)[4:8]
        logger.debug(u'  Got max speed = %s' % ByteToHex(speed))
        return ByteToInt(speed)

    def set_speed_max(self, speed, resolution):
        logger.debug(u'Setting speed max to %s mm/min' % speed)
        command = '\x12\x05\x08\x00'
        speed = speed / 60.0 # convert to mm/s
        speed = speed * resolution * self.tool.numerateur / self.tool.denominateur # FIXME check
        hexspeed = IntToByte(int(speed))
        logger.debug(u'  hex speed max = %s' % ByteToHex(hexspeed))
        self.write(command + hexspeed)

    def get_speed_calc(self):
        logger.debug(u'Reading speed calc...')
        self.write('\x12\x89\x04\x00')
        speed_calc = self.read(8)
        logger.debug(u'  Got speed calc = %s' % ByteToHex(speed_calc))
        return speed_calc

    def set_speed(self, speed, resolution):
        logger.debug(u'Setting speed to %s mm/min' % speed)
        command = '\x12\x06\x08\x00'
        speed = speed / 60.0 # convert to mm/s
        speed = speed * resolution * self.tool.numerateur / self.tool.denominateur # FIXME check
        hexspeed = IntToByte(int(speed))
        logger.debug(u'  hex speed = %s' % ByteToHex(hexspeed))
        self.write(command + hexspeed)

    def get_speed_acca(self):
        logger.debug(u'Reading acca...')
        self.write('\x12\x81\x04\x00')
        value = ByteToInt(self.read(8)[4:8])
        logger.debug(u'  Got acca : %s' % value)
        return value

    def set_speed_acca(self, acc):
        """Set the slope of the acceleration curve (1 to 10)
        """
        logger.debug(u'Setting acca to %s' % acc)
        command = '\x12\x01\x08\x00'
        hexacc = IntToByte(int(acc))
        logger.debug(u'  hex acc = %s' % ByteToHex(hexacc))
        self.write(command + hexacc)

    def set_speed_accb(self, acc):
        """Set the slope of the acceleration curve.
        Must be 1 for a step motor
        """
        logger.debug(u'Setting accb to %s mm/min' % acc)
        command = '\x12\x02\x08\x00'
        hexacc = IntToByte(int(acc))
        logger.debug(u'  hex acc = %s' % ByteToHex(hexacc))
        self.write(command + hexacc)

    def move_ramp_xyz(self, x, y, z):
        raise NotImplementedError

    def move_ramp_x(self, steps):
        """move to x using ramp
        """
        logger.debug(u'move x to step %s' % steps)
        self.write('\x14\x01\x08\x00' + IntToByte(steps))

    def move_var_x(self, steps, start, stop, direction):
        """move to x with variable speed
        steps : the target step
        start : the starting speed
        stop : the target speed
        direction : 'up' or 'down' (accelerate or decelerate)
        """
        if direction == 'up':
            cmd = '\x14\xA1\x10\x00'
        elif direction == 'down':
            cmd = '\x14\x21\x10\x00'
        else:
            raise Exception(u'Wrong direction')
        logger.debug(u'move var x to step %s' % steps)
        self.write(cmd + IntToByte(steps) + IntToByte(start) + IntToByte(stop))

    def move_const_x(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move x to step %s' % steps)
        self.write('\x14\x11\x08\x00' + IntToByte(steps))

    def move_const_y(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move y to step %s' % steps)
        self.write('\x14\x12\x08\x00' + IntToByte(steps))

    def move_const_z(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move z to step %s' % steps)
        self.write('\x14\x13\x08\x00' + IntToByte(steps))

    def move_const_a(self, steps):
        """Move the motor to a fixed position
        """
        logger.debug(u'move a to step %s' % steps)
        self.write('\x14\x14\x08\x00' + IntToByte(steps))

    def get_state(self):
        logger.debug(u'get_state')
        self.write('\x80\x19')
        state = self.read(4, alt=1)
        logger.debug(ByteToHex(state))
        return state

    def get_buffer_state(self):
        logger.debug(u'get_buffer_state')
        self.write('\x80\x18')
        state = self.read(4, alt=1)
        logger.debug(ByteToHex(state))
        return state

    def get_fifo_count(self):
        logger.debug(u'get_fifo_count')
        self.write('\x80\x10', alt=1)
        state = self.read(4, alt=1)
        logger.debug(ByteToHex(state))
        return ByteToInt(state)

