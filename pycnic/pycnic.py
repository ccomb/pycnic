import sys
import pylibusb as usb
import ctypes

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
    return ''.join(["%02X " % ord(x) for x in byteStr] ).strip() + pretty


def ByteToInt(byteStr):
    """Converts a byte string to the corresponding integer
    
        >>> from pycnic import ByteToInt
        >>> ByteToInt('\xFF\xFF')
        65535
    """
    return int(''.join(["%02X" % ord(x) for x in byteStr]),16)


def IntToByte(integer):
    """Converts an integer to its corresponding reversed byte string

    >>> from pycnic import IntToByte, ByteToHex
    >>> print IntToByte(0x00)
    \x00\x00\x00\x00
    >>> print IntToByte(0xFF)
    \xff\x00\x00\x00
    >>> print IntToByte(0x746F)
    \x6F\x74\x00\x00
    >>> print IntToByte(0x746F746F)
    \x6F\x74\x6F\x74
    """
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
                        print u"found %s!" % PRODUCT_NAME
                        dev = device
                        break
    
            if dev is None:
                raise IOError(u'No device found')
            self.handle = usb.open(dev)
        ###
        #interface_nr = 0
        #if hasattr(usb,'get_driver_np'):
        #    # non-portable libusb extension
        #    name = usb.get_driver_np(self.handle,interface_nr)
        #    if name != '':
        #        print 'detach %s' % name
        #        usb.detach_kernel_driver_np(self.handle,interface_nr)
        #
        #config = dev.config[0]
        #usb.set_configuration(self.handle, config.bConfigurationValue)
        #
        #usb.claim_interface(self.handle, interface_nr)

        self.motor = Motor()
        self.tool = Tool()

    def write(self, command):
        buffer = ctypes.create_string_buffer(len(command))
        buffer.value = command
        print u'we write the command %s...' % ByteToHex(buffer.raw)
        if not self.fake:
            bytes = usb.bulk_write(self.handle, 0x01, buffer, TIMEOUT)
            print u'%s bytes written' % bytes
    
    def read(self):
        if self.fake: return
        buffer = ctypes.create_string_buffer(63) #FIXME 64 au lieu de bytes
        print u'Now we read the result...'
        bytes = usb.bulk_read(self.handle, 0x81, buffer, TIMEOUT)
        output = buffer.raw[0:bytes]
        print u'%s bytes read: %s' % (bytes, ByteToHex(output))
        return output

    def set_prompt(self, state):
        command = '\x18\x03\x08\x00'
        hex_state = chr(state) + 3*chr(0)
        self.write(command + hex_state)

    def get_prompt(self):
        self.write('\x18\x83\x04\x00')
        self.read()

    def read_name(self):
        self.write('\x18\x85\x04\x00')
        self.read()

    def get_serial(self):
        self.write('\x18\x84\x04\x00')
        self.read()

    def set_fifo_depth(self, depth):
        print 'set_fifo_depth %s' % depth
        command = '\x18\x10\x08\x00'
        hex_depth = IntToByte(depth)
        self.write(command + hex_depth)

    def set_pulse_width(self, width):
        print 'set_pulse_width %s' % width
        command = '\x13\x08\x08\x00'
        hex_width = IntToByte(width)
        self.write(command + hex_width)

    def get_speed_calc(self):
        self.write('\x12\x89\x04\x00')
        return self.read()

    def set_speed(self, speed):
        print 'set speed %s' % speed
        command = '\x12\x06\x08\x00'

        speed = speed / 60 # FIXME not exact!
        if self.tool.denominateur:
            speed = speed * self.motor.res_x \
                * self.tool.numerateur / self.tool.denominateur
            print 'set calculated speed %s' % speed
            hex_speed = IntToByte(speed)
            #return speed
        else:
            hex_speed = IntToByte(1)
        #FIXME check that hex_speed is on 4 bytes
        self.write(command + hex_speed)

    def move_ramp_xyz(self, x, y, z):
        raise NotImplementedError

if __name__ =='__main__':
    
    #P1 : in 0x81, out 0x01
    #P2 : in 0x82, out 0x02

    tiny = TinyCN()
    if tiny is None:
        sys.exit()

    #tiny.set_prompt(0)
    #tiny.get_prompt()
    #tiny.get_serial()
    tiny.read_name()

    tiny.motor.res_x = 200
    tiny.motor.res_y = 200
    tiny.motor.res_z = 200


    tiny.set_fifo_depth(15) # 255 pulses
    tiny.set_pulse_width(64)
    res = tiny.get_speed_calc()

    tiny.tool.numerateur = ByteToInt(res[0:4])
    tiny.tool.denominateur = ByteToInt(res[4:8])
    print 'numerateur = %s' % tiny.tool.numerateur
    print 'denominateur = %s' % tiny.tool.denominateur
    tiny.tool.speed = 1200

    print 'set the speed'
    #tiny.set_speed(tiny.tool.speed)
    tiny.write('\x12\x06\x08\x00' + '\x00\x02\x00\x00')
    tiny.write('\x14\x11\x08\x00' + '\x00\x01\x00\x00') # 100 step!!

    tiny.read_name()

    #tiny.write('\x14\x08\x10\x00' + 3*'\x00\x00\x01\x10')





    


