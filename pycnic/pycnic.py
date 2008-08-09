import sys
import pylibusb as usb
import ctypes

TIMEOUT = 3000 # timeout for usb read or write
VENDOR_ID = 0x9999
PRODUCT_ID = 0x0002
PRODUCT_NAME = u'TinyCN'

SH_CMD_WR = '\x00\x08\x03\x18' # set prompt
SN_CMD_RD = '\x00\x04\x85\x18' # read name

def ByteToHex( byteStr ):
    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()

class TinyCN(object):
    def __init__(self):
        usb.init()
        if not usb.get_busses():
            usb.find_busses()
            usb.find_devices()
        
        busses = usb.get_busses()
        dev = None
    
        for bus in busses:
            for device in bus.devices:
                if device.descriptor.idVendor == VENDOR_ID \
                  and device.descriptor.idProduct == PRODUCT_ID:
                    print u"found %s!" % PRODUCT_NAME
                    dev = device
                    break
    
        if dev is None:
            print u'No device found'
            return None
        self.handle = usb.open(dev)

    def write(self, command):    
        buffer = ctypes.create_string_buffer(len(command))
        buffer.value = command
        print u'we write the command %s...' % ByteToHex(buffer.raw)
        bytes = usb.bulk_write(self.handle, 0x02, buffer, TIMEOUT)
        print u'%s bytes written' % bytes
    
    def read(self, bytes):
        buffer = ctypes.create_string_buffer(bytes)
        print u'Now we read the result...'
        bytes = usb.bulk_read(self.handle, 0x81, buffer, TIMEOUT)
        print u'%s bytes read: %s' % (bytes, ByteToHex(buffer.raw[0:bytes]))

    def set_prompt(self, state):
        if state:
            hexstate = '\x00\x00\x00\x01'
        else:
            hexstate = '\x00\x00\x00\x00'
        self.write('\x00\x08\x03\x18'+hexstate)

    def get_prompt(self):
        self.write('\x00\x04\x83\x18')
        self.read(8)

    def read_name(self):
        #self.write('\x00\x04\x85\x18')
        self.write('\x18\x85\x04\x00')
        self.read(32)

if __name__ =='__main__':
    #interface_nr = 0
    #if hasattr(usb,'get_driver_np'):
    #    # non-portable libusb extension
    #    name = usb.get_driver_np(libusb_handle,interface_nr)
    #    if name != '':
    #        usb.detach_kernel_driver_np(libusb_handle,interface_nr)
    #
    #config = dev.config[0]
    #usb.set_configuration(libusb_handle, config.bConfigurationValue)
    #
    #usb.claim_interface(libusb_handle, interface_nr)
    
    #P1 : in 0x81, out 0x01
    #P2 : in 0x82, out 0x02

    tiny = TinyCN()
    if tiny is None:
        sys.exit()

    tiny.get_prompt()
    #tiny.set_prompt(0)
    #tiny.read_name()



    


