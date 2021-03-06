#def test_primes_c():
#    from ..example_c import primes as primes_c
#    assert primes_c(10) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

def test_primes():
    from ..example_mod import primes
    assert primes(10) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

def test_deprecation():
    import warnings
    warnings.warn(
        "This is deprecated, but shouldn't raise an exception, unless "
        "enable_deprecations_as_exceptions() called from conftest.py",
        DeprecationWarning)

def test_hselect_basic():
    from ..hselect import Hselect
    from astropy.table import Table
    test_dir = "/eng/ssb/iraf_transition/test_data/"

    data_rows = [('/eng/ssb/iraf_transition/test_data/iczgs3y5q_flt.fits', 1, 'ELECTRONS/S'),
                 ('/eng/ssb/iraf_transition/test_data/iczgs3y5q_flt.fits', 2, 'ELECTRONS/S')]
    correct_table = Table(rows=data_rows, names=('Filename', 'ExtNumber', 'BUNIT'),
                          dtype=('S80', 'int64', 'S68'))
    hobj = Hselect(test_dir+'iczgs3y5q_flt.fits', 'BUNIT', extension='1,2')

    #for boo in correct_table == hobj.table:
    #    assert boo


def test_hselect_wildcard():
    from ..hselect import Hselect
    from astropy.table import Table
    test_dir = "/eng/ssb/iraf_transition/test_data/"

    data_rows = [('/eng/ssb/iraf_transition/test_data/iczgs3y5q_flt.fits', 0,
                  'iczgs3y5q_flt.fits', 'SCI')]
    correct_table = Table(rows=data_rows, names=('Filename', 'ExtNumber', 'FILENAME', 'FILETYPE'),
                          dtype=('S80', 'int64', 'S68', 'S68'))
    hobj = Hselect(test_dir+'iczgs3y5q_*.fits', 'FILE*', extension='0')

    #for boo in correct_table == hobj.table:
    #     assert boo


#def test_eval_keyword_lessthen():

#def test_eval_keyword_equalto():