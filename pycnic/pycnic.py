import sys
import pylibusb as usb
import ctypes

TIMEOUT = 500 # timeout for usb read or write
VENDOR_ID = 0x9999
PRODUCT_ID = 0x0002
PRODUCT_NAME = u'TinyCN'

def ByteToHex(byteStr):
    try:
        pretty = u' (%s)' % unicode(byteStr)
    except UnicodeDecodeError:
        pretty = ''
    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip() + pretty

class TinyCN(object):
    def __init__(self):
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
            print u'No device found'
            return None
        self.handle = usb.open(dev)
        ###
        interface_nr = 0
        if hasattr(usb,'get_driver_np'):
            # non-portable libusb extension
            name = usb.get_driver_np(self.handle,interface_nr)
            if name != '':
                print 'detach %s' % name
                usb.detach_kernel_driver_np(self.handle,interface_nr)
        
        config = dev.config[0]
        usb.set_configuration(self.handle, config.bConfigurationValue)
        
        usb.claim_interface(self.handle, interface_nr)

    def write(self, command):    
        buffer = ctypes.create_string_buffer(len(command))
        buffer.value = command
        print u'we write the command %s...' % ByteToHex(buffer.raw)
        bytes = usb.bulk_write(self.handle, 0x01, buffer, TIMEOUT)
        print u'%s bytes written' % bytes
    
    def read(self):
        buffer = ctypes.create_string_buffer(64) #FIXME 64 au lieu de bytes
        print u'Now we read the result...'
        bytes = usb.bulk_read(self.handle, 0x81, buffer, TIMEOUT)
        print u'%s bytes read: %s' % (bytes, ByteToHex(buffer.raw[0:bytes]))

    def set_prompt(self, state):
        command = '\x18\x03\x08\x00'
        if state:
            hexstate = '\x00\x00\x00\x01'
        else:
            hexstate = '\x00\x00\x00\x00'
        self.write(command + hexstate)

    def get_prompt(self):
        self.write('\x18\x83\x04\x00')
        self.read()

    def read_name(self):
        #self.write('\x00\x04\x85\x18')
        self.write('\x18\x85\x04\x00')
        self.read()

    def get_serial(self):
        self.write('\x18\x84\x04\x00')
        self.read()
if __name__ =='__main__':
    
    #P1 : in 0x81, out 0x01
    #P2 : in 0x82, out 0x02

    tiny = TinyCN()
    if tiny is None:
        sys.exit()

    tiny.set_prompt(0)
    tiny.get_prompt()
    tiny.get_serial()
    tiny.read_name()



    


