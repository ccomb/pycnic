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
        del tiny
        tiny = TinyCN()
        self.assertEqual(tiny.name, 'TinyCN')
        del tiny


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
