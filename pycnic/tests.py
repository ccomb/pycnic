import unittest, doctest
import pycnic

def test_suite( ):
    return unittest.TestSuite((
        doctest.DocTestSuite(pycnic, 
                             optionflags=doctest.NORMALIZE_WHITESPACE+
                                         doctest.ELLIPSIS
                             ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
