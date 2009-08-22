# coding: utf-8
"""Module supporting Soprolec controllers
See soprolec.txt
"""
import serial
import time
import logging

TIMEOUT = 1 # in seconds, for serial port reads or writes
logger = logging.getLogger('PyCNiC')
logging.basicConfig(level=logging.DEBUG)


class InterpCNC(object):
    """This class represents the InterpCNC controller
    """
    serial_speed = 19200
    prompt = '>'
    port = None
    _speed = None

    def __init__(self, speed=500):
        self.connect()
        self.speed = speed
        self.reset_all_axis()

    def __del__(self):
        self.disconnect

    #
    # Lowlevel methods
    #
    def connect(self, serial_port=0):
        if self.port is None or self.port.fd is None:
            self.port = serial.Serial(serial_port,
                                      self.serial_speed,
                                      timeout=TIMEOUT)

    def disconnect(self):
        if self.port is None or self.port.fd is None:
            return
        self.port.flush()
        self.port.close()

    def _read(self):
        """Read from the controller until we get the prompt or we timeout.
        """
        response = ''
        while not response.endswith(self.prompt):
            time1 = time.time()
            response += self.port.read()
            if time.time() - time1 > TIMEOUT: break
        return response

    def _write(self, command):
        """Write a command to the controller.
        """
        self.port.write(command)

    def execute(self, command):
        """execute a command by sending it to the controller,
        and returning its response.
        The result should be interpreted by the caller.
        """
        self._write(command + ';')
        response = self._read()
        if response.startswith('=') and response.endswith(self.prompt):
            return response[1:-1]
        else:
            return ''

    def _eeprom_read(self, param):
        """Read a parameter in the EEPROM
        """
        return self.execute('RP'+ param)

    def _eeprom_write(self, param, value):
        """write a parameter into the EEPROM
        This should probably not be abused to save the EEPROM.
        """
        return self.execute('WP' + param + 'V' + value)

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
    def move_x(self, step, ramp=True):
        """Move X axis to specified step using a ramp or not

        >>> cnc = InterpCNC(speed=440)
        >>> cnc.move_x(10)
        >>> cnc.x
        10
        >>> cnc.move_x(0, ramp=False)
        >>> cnc.x
        0
        """
        if ramp: command = 'LX'
        if not ramp: command = 'LLX'
        self.execute(command + str(step))

    def _get_x(self):
        """Get the position of the X axis

        >>> cnc = InterpCNC(speed=440)
        >>> cnc.move_x(10)
        >>> cnc._get_x()
        10
        >>> cnc.move_x(0)
        >>> cnc._get_x()
        0
        """
        return int(self.execute('RX'))

    def _set_x(self, x):
        """Reset the X axis to the specified value without moving

        >>> cnc = InterpCNC(speed=440)
        >>> cnc.x
        0
        >>> cnc._set_x(10)
        >>> cnc.x
        10
        >>> cnc._set_x(0)
        >>> cnc.x
        0
        """
        self.execute('WX' + str(x))

    x = property(_get_x, _set_x)

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
        >>> cnc.move_x(5)
        >>> cnc.reset_all_axis()
        >>> cnc.x
        0
        """
        self.execute('E')




