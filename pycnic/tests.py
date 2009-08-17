import time
import unittest, doctest
import pycnic
from pycnic import TinyCN
import tests

class TestTinyCN(unittest.TestCase):
    def test_release_resources(self):
        """Check USB resources are correctly released.
        We should be able to open the device twice
        """
        tiny = TinyCN()
        self.assertEqual(tiny.name, 'TinyCN')
        #print tiny.read_firmware()
        del tiny


        tiny = TinyCN()
        tiny.move_ramp_x(200)
        tiny.move_ramp_x(0)
        while tiny.get_fifo_count() > 0:
            time.sleep(0.5)
        del tiny

        #tiny = TinyCN()
        #tiny.move_ramp_x(200)
        #tiny.move_ramp_x(0)
        #while tiny.get_fifo_count() > 0:
        #    time.sleep(0.5)
        #del tiny

def test_suite( ):
    return unittest.TestSuite((
        unittest.TestLoader().loadTestsFromTestCase(TestTinyCN),
        doctest.DocTestSuite(pycnic,
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        doctest.DocFileSuite('pycnic.txt',
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
