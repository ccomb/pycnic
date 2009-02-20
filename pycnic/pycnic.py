# coding: utf-8
# 1, 2, 3, 4 : noir, vert, rouge, bleu
import sys
import pylibusb as usb
import ctypes
import time
import subprocess
from optparse import OptionParser

TIMEOUT = 500 # timeout for usb read or write
VENDOR_ID = 0x9999
PRODUCT_ID = 0x0002
PRODUCT_NAME = u'TinyCN'

global DEBUG
DEBUG=False

def debug(message):
    if DEBUG:
        print message

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
    numerateur = None
    denominateur = None
    speed = None


class TinyCN(object):

    motor = None
    tool = None
    
    def __init__(self, fake=False):
        self.fake = fake
        if not self.fake:
            usb.init()
            if not usb.get_busses():
                usb.find_busses()
                usb.find_devices()
            
            busses = usb.get_busses()
            dev = None

            # try to find the device
            for bus in busses:
                for device in bus.devices:
                    if device.descriptor.idVendor == VENDOR_ID \
                      and device.descriptor.idProduct == PRODUCT_ID:
                        debug(u"found %s!" % PRODUCT_NAME)
                        dev = device
                        break
    
            if dev is None:
                raise IOError(u'No device found')
            self.handle = usb.open(dev)
            #usb.reset(self.handle)
        ##
        #interface_nr = 0
        #if hasattr(usb,'get_driver_np'):
        #    # non-portable libusb extension
        #    name = usb.get_driver_np(self.handle,interface_nr)
        #    debug('Got driver name = %s' % name)
        #    if name != '':
        #        debug('Detach %s' % name)
        #        usb.detach_kernel_driver_np(self.handle,interface_nr)
        #
        #config = dev.config[0]
        #usb.set_configuration(self.handle, config.bConfigurationValue)
        #debug('setting configuration %s' % config.bConfigurationValue)
        #usb.claim_interface(self.handle, interface_nr)

        self.motor = Motor()
        self.tool = Tool()

    def __XXXdel__(self):
        usb.release_interface(self.handle, 0) # XXX
        usb.close(self.handle)

    def write(self, command, alt=0):
        buffer = ctypes.create_string_buffer(len(command))
        buffer.value = command
        debug(u'    we write the command %s...' % ByteToHex(buffer.raw))
        if not self.fake:
            bytes = usb.bulk_write(self.handle, 0x01+alt, buffer, TIMEOUT)
            debug(u'    %s bytes written' % bytes)
    
    def read(self, alt=0):
        if self.fake: return
        buffer = ctypes.create_string_buffer(63) #FIXME 64 au lieu de bytes
        debug(u'    Now we read the result...')
        bytes = usb.bulk_read(self.handle, 0x81 + alt, buffer, TIMEOUT)
        output = buffer.raw[0:bytes]
        debug(u'    %s bytes read: %s' % (bytes, ByteToHex(output)))
        return output

    def set_prompt(self, state):
        debug('Setting prompt %s' % state)
        command = '\x18\x03\x08\x00'
        hex_state = chr(state) + 3*chr(0)
        self.write(command + hex_state)

    def get_prompt(self):
        debug('Reading prompt')
        self.write('\x18\x83\x04\x00')
        prompt = self.read()
        debug('  Got prompt: %s' % prompt)
        return prompt

    def read_name(self):
        self.write('\x18\x85\x04\x00')
        self.read()

    def get_serial(self):
        self.write('\x18\x84\x04\x00')
        return self.read()

    def set_fifo_depth(self, depth):
        debug('Setting fifo pulse generator to %s pulses' % depth)
        command = '\x18\x10\x08\x00'
        hex_depth = IntToByte(depth)
        self.write(command + hex_depth)

    def set_pulse_width(self, width):
        debug('Setting pulse width to %s ' % width)
        command = '\x13\x08\x08\x00'
        hex_width = IntToByte(width)
        self.write(command + hex_width)

    def get_speed_calc(self):
        debug('Reading speed calc')
        self.write('\x12\x89\x04\x00')
        speed_calc = self.read()
        debug('  Got speed calc = %s' % ByteToHex(speed_calc))
        return speed_calc

    def set_speed(self, speed, resolution):
        debug('Setting speed to %s mm/min' % speed)
        command = '\x12\x06\x08\x00'
        speed = speed / 60.0 # convert to mm/s
        speed = speed * resolution * self.tool.numerateur / self.tool.denominateur # FIXME check
        hexspeed = IntToByte(int(speed))
        debug('  hex speed = %s' % ByteToHex(hexspeed))
        self.write(command + hexspeed)

    def set_speed_acca(self, acc):
        debug('Setting acca to %s mm/min' % acc)
        command = '\x12\x01\x08\x00'
        hexacc = IntToByte(int(acc))
        debug('  hex acc = %s' % ByteToHex(hexacc))
        self.write(command + hexacc)

    def set_speed_accb(self, acc):
        debug('Setting accb to %s mm/min' % acc)
        command = '\x12\x02\x08\x00'
        hexacc = IntToByte(int(acc))
        debug('  hex acc = %s' % ByteToHex(hexacc))
        self.write(command + hexacc)

    def move_ramp_xyz(self, x, y, z):
        raise NotImplementedError

    def move_ramp_x(self, steps):
        """move to x using ramp
        """
        debug('move x to step %s' % steps)
        tiny.write('\x14\x11\x01\x00' + IntToByte(steps))

    def move_var_x(self, steps, start, stop, direction):
        """move to x using ramp
        """
        if direction == 'up':
            cmd = '\x14\xA1\x10\x00'
        elif direction == 'down':
            cmd = '\x14\x21\x10\x00'
        else:
            raise Exception(u'Wrong direction')
        debug('move var x to step %s' % steps)
        tiny.write(cmd + IntToByte(steps) + IntToByte(start) + IntToByte(stop))

    def move_const_x(self, steps):
        """Move the motor to a fixed position
        """
        debug('move x to step %s' % steps)
        tiny.write('\x14\x11\x08\x00' + IntToByte(steps))

    def move_const_y(self, steps):
        """Move the motor to a fixed position
        """
        debug('move y to step %s' % steps)
        tiny.write('\x14\x12\x08\x00' + IntToByte(steps))

    def move_const_z(self, steps):
        """Move the motor to a fixed position
        """
        debug('move z to step %s' % steps)
        tiny.write('\x14\x13\x08\x00' + IntToByte(steps))

    def move_const_a(self, steps):
        """Move the motor to a fixed position
        """
        debug('move a to step %s' % steps)
        tiny.write('\x14\x14\x08\x00' + IntToByte(steps))

    def get_buffer_state(self):
        debug('get_buffer_state')
        self.write('\x80\x18')
        state = self.read(1)
        debug(ByteToHex(state))
        return state

    def get_fifo_count(self):
        debug('get_fifo_count')
        self.write('\x80\x10')
        state = self.read(1)
        debug(len(state))
        debug(ByteToHex(state))
        return ByteToInt(state)

if __name__ =='__main__':
    parser = OptionParser()
    parser.add_option('-d', '--debug', nargs=0, help='set debug mode')
    (options, args) = parser.parse_args()
    if options.debug is not None:
        DEBUG=True
        usb.set_debug(True)

    
    #P1 : in 0x81, out 0x01
    #P2 : in 0x82, out 0x02

    tiny = TinyCN()
    if tiny is None:
        sys.exit()

    tiny.motor.res_x = 30
    tiny.motor.res_y = 200
    tiny.motor.res_z = 200

    tiny.set_prompt(0)
    tiny.read_name()
    tiny.set_fifo_depth(255) # 255 pulses
    tiny.set_pulse_width(64) # 5µs (?)
    res = tiny.get_speed_calc()
    debug(ByteToHex(res))

    tiny.tool.numerateur = ByteToInt(res[4:8])
    tiny.tool.denominateur = ByteToInt(res[0:4])
    debug('numerateur = %s' % tiny.tool.numerateur)
    debug('denominateur = %s' % tiny.tool.denominateur)


    tiny.tool.speed = 700
    x=0

    tiny.set_speed(tiny.tool.speed, tiny.motor.res_x)


    tiny.set_speed_acca(4)
    #tiny.set_speed_accb(2)

    # launch the burst shoot
    # D200 took 1.515sec for 8 images

    tiny.move_var_x(2400, 0, 30, 'up')
    tiny.move_var_x(3000, 30, 0, 'down')

    tiny.move_var_x(600, 0, 300, 'up')
    tiny.move_var_x(0, 300, 0, 'down')

    import time
    time.sleep(1)

    command = ('gphoto2',
               '--auto-detect',
               '--set-config',
               '/main/settings/capturetarget=1',
               '--set-config',
               '/main/capturesettings/capturemode=1',
               '--set-config',
               '/main/capturesettings/burstnumber=8',
               '--capture-image')

    p = subprocess.Popen(command)

    #ramp tiny.write('\x14\x08\x10\x00' + 3*'\x00\x00\x01\x10')
    #tiny.get_buffer_state()
    #while tiny.get_buffer_state() != '\x00\x80':
    #    pass
    #while tiny.get_fifo_count() > 0:
    #    time.sleep(0.1)

#    usb.release_interface(tiny.handle, 0)
#    usb.detach_kernel_driver_np(tiny.handle,0)
#    usb.reset(tiny.handle)
#    usb.close(tiny.handle)
    #del tiny




    


