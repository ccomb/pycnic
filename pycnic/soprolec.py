# coding: utf-8
"""Module supporting Soprolec controllers
See soprolec.txt
"""
from UserDict import UserDict
import logging
import os
import pycnic
import serial
import usb
import time

logger = logging.getLogger('PyCNiC')
logging.basicConfig(level=logging.INFO)

TIMEOUT = 2 # in seconds, for serial port reads or writes
MAXTIMEOUT = 30 # in seconds, for any move command
VENDOR_ID = 0x067b
PRODUCT_ID = 0x2303
PRODUCT_NAME = u'serial to usb converter'

def tuple2hex(tup):
    """Converts a data tuple of integers to its hex representation

    >>> from pycnic.soprolec import tuple2hex
    >>> tuple2hex( (1,2,3) )
    '01 02 03'
    >>> tuple2hex( (30,40,110) )
    '1E 28 6E'
    """
    return ' '.join(["%02X" % i for i in tup])


class InterpCNC(object):
    """This class represents the InterpCNC controller
    """
    serial_speed = 19200
    name = None
    prompt = '>'
    _paramlist = None
    params = None
    port = None # serial
    handle = None # usb
    device = None # usb
    _speed = None
    configfile = 'soprolec.csv'

    def __init__(self, speed=1000):
        self._speed = speed
        try:
            self.connect()
        except IOError:
            logger.warning(u'Did you plug and turn on the device?')
        self.params = UserDict()
        self.params.__getitem__ = self._eeprom_read
        self.params.__setitem__ = self._eeprom_write

    @property
    def paramlist(self):
        """Load the parameter descriptions from a csv file

        >>> InterpCNC().paramlist[0]['name']
        'EE_DEFAULT_SPEED'
        >>> InterpCNC().paramlist[0]['num']
        '3'

        """
        if self._paramlist is not None:
            return self._paramlist
        # read the file
        paramfile = open(os.path.join(os.path.dirname(pycnic.__file__),
                                         self.configfile))
        paramlist = paramfile.readlines()
        paramfile.close()
        # get only our own config based on the card identifier
        found = False
        titles = None
        for line in paramlist:
            line = line.strip()
            # try to find our name
            if not found and line == self.name:
                found = True
                self._paramlist = []
                continue
            if not found: continue
            # next line is the title line
            if not titles:
                titles = line.split(';')
                continue
            if line.strip() == '':
                break
            # turn following lines into a dict with titles
            param = dict(zip(titles, line.split(';')))
            self._paramlist.append(param)

        if not found:
            raise NotImplementedError(
                u'No config yet for this card. Please contact the author.')

        return self._paramlist

    def __repr__(self):
        return '<%s.%s object at %s name="%s">' % (
                self.__module__,
                self.__class__.__name__,
                hex(id(self)),
                self.name)

    #
    # Lowlevel methods
    #
    def connect(self, serial_port=0):
        # first try the serial port
        if (self.port is None
            or self.port.fd is None
            or not self.name):
            self.port = serial.Serial(serial_port,
                                      self.serial_speed,
                                      timeout=TIMEOUT)
        if self.port.fd is not None:
            self.name = self.execute('RI')
            self.speed = self._speed
            #self.reset_all_axis()
            return
        else:
            self.port = None
        # otherwise try the usb port
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

            logger.debug(u'Opening device...')
            self.handle = self.device.open()

            logger.debug(u'Detach kernel driver...')
            interface = self.device.configurations[0].interfaces[0][0]
            self.handle.detachKernelDriver(interface)

            logger.debug(u'Setting configuration 1')
            self.handle.setConfiguration(1)

            logger.debug(u'Claiming interface 0')
            self.handle.claimInterface(0)





    def disconnect(self):
        # serial
        if self.port is not None and self.port.fd is not None:
            self.port.flush()
            self.port.close()

        # usb
        if self.handle is not None:
            logger.debug(u'Releasing interface...')
            self.handle.releaseInterface()
            self.handle = None
            #self.device.close()

    def _read(self, timeout=None):
        """Read from the controller until we get the prompt or we timeout.
        """
        logger.debug(u'    Now we read the result...')
        if timeout is None:
            timeout = TIMEOUT

        response = ''
        while not response.endswith(self.prompt):
            time1 = time.time()
            if self.port is not None: # serial
                response += self.port.read()
            elif self.handle is not None: # usb
                size = 1
                buffer = self.handle.bulkRead(0x83, size, TIMEOUT)
                response += buffer
            if time.time() - time1 > 0.9 * timeout:
                raise IOError(u'Could not read from the device')
                break

        return response

    def _write(self, command):
        """Write a command to the controller.
        """
        logger.debug(u'    we write the command %s...' % command)
        time1 = time.time()

        if self.port is not None: # serial
            self.port.write(command)
            self.port.flush()
        elif self.handle is not None: # usb
            bytes = self.handle.bulkWrite(0x02, command, TIMEOUT)
            logger.debug(u'    %s bytes written' % bytes)

        if time.time() - time1 > TIMEOUT:
            raise IOError(u'Could not write to the device')

    def execute(self, command, timeout=None):
        """execute a command by sending it to the controller,
        and returning its response.
        The result should be interpreted by the caller.
        """
        if not self.name and command != 'RI':
            raise IOError(u'The device is not connected')
        if command.startswith('H'):
            timeout = 10 # the card does not respond while calibrating
        command += ';'
        logger.debug(u'Executing command: %s' % command)
        self._write(command)
        response = self._read(timeout=timeout)
        if response.startswith('=') and response.endswith(self.prompt):
            return response[1:-1]
        else:
            return ''

    def _eeprom_read(self, param):
        """Read a parameter in the EEPROM

        >>> cnc = InterpCNC()
        >>> 0 < int(cnc.params['EE_DEFAULT_SPEED']) < 10000
        True
        """
        try:
            param = [p for p in self.paramlist if p['name']==param][0]
        except:
            raise ValueError(u'This config does not exist')
        return self.execute('RP'+ param['num'])

    def _eeprom_write(self, param, value):
        """write a parameter into the EEPROM
        This should probably not be abused to save the EEPROM.
        """
        try:
            param = [p for p in self.paramlist if p['name']==param][0]
        except:
            raise ValueError(u'This config does not exist')
        return self.execute('WP' + param['num'] + 'V' + str(value))


    #
    # Informative commands
    #

    @property
    def firmware_major(self):
        """Get the major firmware version number

        >>> InterpCNC().firmware_major
        3
        """
        return int(self.execute('RVH'))

    @property
    def firmware_minor(self):
        """Get the minor firmware version number

        >>> InterpCNC().firmware_minor > 0
        True
        """
        return int(self.execute('RVL'))

    @property
    def bootloader_major(self):
        """Get the major bootloader version number

        >>> InterpCNC().bootloader_major
        1
        """
        return int(self.execute('RVBH'))

    @property
    def bootloader_minor(self):
        """Get the minor bootloader version number

        >>> InterpCNC().bootloader_minor >= 0
        True
        """
        return int(self.execute('RVBL'))

    @property
    def max_linear_speed(self):
        """Get the maximum speed in linear move (Hz)

        >>> 10000 < InterpCNC().max_linear_speed < 90000
        True
        """
        return int(self.execute('RVML'))

    @property
    def max_circular_speed(self):
        """Get the maximum speed in circular move (Hz)

        >>> 10000 < InterpCNC().max_circular_speed < 90000
        True
        """
        return int(self.execute('RVMC'))

    #
    # linear moves
    #
    def move(self, x=None, y=None, z=None, speed=None, ramp=True):
        """Move specified axis to specified step using a ramp or not

        >>> cnc = InterpCNC(speed=2000)
        >>> cnc.reset_all_axis()

        We must specify one axis

        >>> cnc.move()
        Traceback (most recent call last):
        ...
        ValueError: Please specify at least one axis to move

        We can move any axis:

        >>> cnc.move(x=10)
        >>> cnc.x, cnc.y, cnc.z
        (10, 0, 0)
        >>> cnc.move(x=0, ramp=False)
        >>> cnc.x, cnc.y, cnc.z
        (0, 0, 0)

        int are converted to floats

        >>> cnc.move(x=10.2)
        >>> cnc.x, cnc.y, cnc.z
        (10, 0, 0)


        We can specify the speed of the move

        >>> cnc.move(x=200, speed=500)
        >>> cnc.move(x=0, speed=2000)

        >>> cnc.move(y=10)
        >>> cnc.move(z=10)
        >>> cnc.x, cnc.y, cnc.z
        (0, 10, 10)
        >>> cnc.move(y=0)
        >>> cnc.move(z=0)
        >>> cnc.x, cnc.y, cnc.z
        (0, 0, 0)

        We can also move along all axis at once:

        >>> cnc.x, cnc.y, cnc.z
        (0, 0, 0)
        >>> cnc.move(x=10, y=20, z=30)
        >>> cnc.x, cnc.y, cnc.z
        (10, 20, 30)
        >>> cnc.move(x=30, y=10, z=20)
        >>> cnc.x, cnc.y, cnc.z
        (30, 10, 20)


        """
        if ramp: command = 'L'
        if not ramp: command = 'LL'

        if (x, y, z) == (None, None, None):
            raise ValueError(u'Please specify at least one axis to move')

        values = [('X',x), ('Y',y), ('Z',z)]
        # the card wants the biggest move to be at the left.
        values.sort(key=lambda x:x[1], reverse=True)
        command += ''.join([val[0] + str(int(val[1])) for val in values if val[1] is not None])

        # add the speed
        if speed is not None:
            command += 'V' + str(speed)

        self.execute(command)

    def wait(self, time=None):
        """tell the controller to wait during <time> seconds. If time is not provided, wait until the
        controller is available.
        """
        if time is None:
            self.execute('RX', timeout=MAXTIMEOUT)
        if time > 0:
            self.execute('WD' + str(10*time), timeout=MAXTIMEOUT)


    def _get_axis(self, axis):
        """Get the position of the X axis

        >>> cnc = InterpCNC(speed=2000)
        >>> cnc.reset_all_axis()
        >>> cnc.move(x=10)
        >>> cnc._get_axis('x')
        10
        >>> cnc.move(x=0)
        >>> cnc._get_axis('x')
        0
        """
        if axis not in ('x', 'y', 'z'):
            raise ValueError(u'Bad axis')
        return int(self.execute('R' + axis.upper()))

    def _set_axis(self, axis, value):
        """Reset the specified axis to the specified value without moving

        >>> cnc = InterpCNC(speed=2000)
        >>> cnc.reset_all_axis()
        >>> cnc.x
        0
        >>> cnc._set_axis('x', 10)
        >>> cnc.x
        10
        >>> cnc._set_axis('x', 0)
        >>> cnc.x
        0
        >>> cnc.y = 1
        >>> cnc.z = 2
        >>> cnc.x, cnc.y, cnc.z
        (0, 1, 2)

        If value is None, perform a calibration on the specified axis
        #>>> cnc.x = None

        """
        if axis not in ('x', 'y', 'z'):
            raise ValueError(u'Bad axis')
        if value is None:
            # calibration with home sensor
            if 0 < int(self.params['EE_FDC_ORIGINEX']) <= 8:
                self.execute('HX')
            else:
                raise Warning(u'The input port is not configured')
            return
        self.execute('W' + axis.upper() + str(value))

    x = property(lambda self: self._get_axis('x'), lambda self, val: self._set_axis('x', val))
    y = property(lambda self: self._get_axis('y'), lambda self, val: self._set_axis('y', val))
    z = property(lambda self: self._get_axis('z'), lambda self, val: self._set_axis('z', val))

    def _get_speed(self):
        """Get the current speed used for next move

        >>> cnc = InterpCNC(speed=440)
        >>> cnc._get_speed()
        440
        >>> cnc.speed = 880
        >>> cnc._get_speed()
        880
        >>> cnc.speed
        880
        """
        return self._speed

    def _set_speed(self, speed):
        """Set the speed

        >>> cnc = InterpCNC(speed=440)
        >>> cnc.speed
        440
        >>> cnc._set_speed(880)
        >>> cnc.speed
        880
        >>> cnc.speed = 440
        >>> cnc.speed
        440
        """
        self.execute('VV' + str(speed))
        self._speed = speed

    speed = property(_get_speed, _set_speed)

    def reset_all_axis(self):
        """Reset all axis to zero

        >>> cnc = InterpCNC(speed=440)
        >>> cnc.x = 10
        >>> cnc.reset_all_axis()
        >>> cnc.x
        0
        >>> cnc.move(x=5)
        >>> cnc.reset_all_axis()
        >>> cnc.x
        0
        """
        self.execute('E')




