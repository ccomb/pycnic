import time
import unittest, doctest
import techlf, soprolec
import tests

class TestTinyCN(unittest.TestCase):
    def test_release_resources(self):
        """Check USB resources are correctly released.
        We should be able to open the device twice
        """
        tiny = techlf.TinyCN()
        self.assertEqual(tiny.name, 'TinyCN')
        #print tiny.read_firmware()
        del tiny


        tiny = techlf.TinyCN()
        tiny.move_ramp_x(200)
        tiny.move_ramp_x(0)
        while tiny.get_fifo_count() > 0:
            time.sleep(0.5)
        del tiny

def test_suite( ):
    return unittest.TestSuite((
        unittest.TestLoader().loadTestsFromTestCase(TestTinyCN),
        doctest.DocTestSuite(techlf,
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        doctest.DocTestSuite(soprolec,
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        doctest.DocFileSuite('techlf.txt',
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        doctest.DocFileSuite('soprolec.txt',
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
