""" hselect
algorithm outline:
translate inputs, get filelist

keep track of keywords/values for final table in dict
loop through files, and request extensions, dict key name will be filename-ext#
check for reg-exp matches (have list of request keywords)
store keyword/values in dictionary (an inner dictionary)
if dictionary is empty at the end, delete the entry

when have all values, make masked numpy arrays, port into astropy table
"""

# STDLIB
from six import iteritems
import operator
import re

# THIRD-PARTY
import numpy as np
from stsci.tools import parseinput
from astropy.io import fits
from astropy.table import Table


class Hselect(object):
    """hselect IRAF replacement.  Will ideally contain full functionality of IRAF version.

    EXAMPLE:
    > myObj = Hselect("jcz*","BUNIT,TIME-OBS",extension="0,1,2,3",expr="BUNIT=ELECTRONS")
    > myObj.table

    """

    def __init__(self, filename_list, keyword_list, extension='all', expr="None"):
        """
        set initial parameters, call class functions for preforming selection
        and formatting to masked astropy table.
        """

        self.filename_list = parseinput.parseinput(filename_list)[0]
        self.final_key_dict = {}
        self.keyword_list = keyword_list.split(",")
        self.final_key_set = set()
        self.extension = extension
        self.expr = expr
        self.table = Table()

        self.select()
        self.__dict_to_table()

    def select(self):
        """
        Perform hselect like query on provided file names, inputs were setup in init, and output is
        stored in self.final_key_dict

        """

        if self.extension != 'all':
            try:
                ext_list = [int(x) for x in self.extension.split(",")]
            except ValueError:
                print("Incorrect syntax for extension list, must all be integers: {}".format(self.extension))

        # loop through all files, find requested keywords
        for filename in self.filename_list:
            try:
                hdulist = fits.open(filename)
            except IOError:
                print("couldn't open file {}".format(filename))

            if self.extension == 'all':
                ext_list = range(len(hdulist))

            for ext in ext_list:
                header = hdulist[ext].header
                outer_key = '{}-{}'.format(filename, ext)

                # check for expressions, will not make dictionary entry if expression false
                # would be nice to use interpreter pattern here for more advanced expressions,
                # but for now I'll stick with just 'AND's. check is expr is valid only once,
                # earlier in code.
                if self.expr != "None" and not self.__eval_keyword_expr(header, self.expr):
                    continue

                self.final_key_dict[outer_key] = {}

                for search_keyword in self.keyword_list:
                    # have to do regular expression matching for keywords
                    if '*' in search_keyword:
                        matches = wildcard_matches(header, search_keyword)
                        for match in matches:
                            self.final_key_dict[outer_key][match], data_type = to_number(header[match])
                            self.final_key_set.add((match, data_type))

                    else:
                        if search_keyword in header:
                            self.final_key_dict[outer_key][search_keyword], data_type = \
                                to_number(header[search_keyword])
                            self.final_key_set.add((search_keyword, data_type))

                if not self.final_key_dict[outer_key]:
                    del self.final_key_dict[outer_key]

            hdulist.close()

    def __dict_to_table(self):
        """Format the final dictionary of keyword matches into a masked astropy table.
        Right now only taking data types of float and str.

        """

        # need to setup all numpy arrays first, then put into table, adding columns is apparently slow
        file_ext_list = self.final_key_dict.keys()
        num_rows = len(file_ext_list)
        final_keyword_list = list(self.final_key_set)

        array_list = [[elem.split('-')[0] for elem in file_ext_list],
                      [int(elem.split('-')[1]) for elem in file_ext_list]]
        col_names = ['Filename', 'ExtNumber']
        data_types = ['S80', int]
        # the bool mask array list will be off by index of 2
        mask_list = []
        dumb_indx_dict = {}

        # make initial empty data and bool arrays
        for indx, key_tuple in enumerate(final_keyword_list):
            # make dumb keyword index dict, probably a better way to do this
            dumb_indx_dict[key_tuple[0]] = indx
            if key_tuple[1] == str:
                data_type = 'S68'
            else:
                data_type = float

            array_list.append(np.zeros(num_rows, dtype=data_type))
            mask_list.append(np.ones(num_rows, dtype=bool))
            col_names.append(key_tuple[0])
            data_types.append(data_type)

        # now fill in arrays and mask arrays
        for indx, efile in enumerate(file_ext_list):
            for (ikeyword, value) in iteritems(self.final_key_dict[efile]):
                ikeyword_indx = dumb_indx_dict[ikeyword]
                array_list[ikeyword_indx+2][indx] = value
                mask_list[ikeyword_indx][indx] = False

        # put arrays and masks together into one masked array
        for indx, mask_arr in enumerate(mask_list):
            array_list[indx+2] = np.ma.array(array_list[indx+2], mask=mask_arr)

        # put everything into an astropy table
        self.table = Table(array_list, names=tuple(col_names), dtype=tuple(data_types))

    @staticmethod
    def __eval_keyword_expr(header, str_expr):
        """Translate the input string expression (only accepting AND's for now)
        into True or False on given header.  Not enforcing spaces right now, but
        could if we want the ability to have ><= character sets in keyword values.

        Parameters
        ----------
        header : fits header

        str_expr : str
            input string that contains given header value expression

        Returns
        -------
        boolean : boolean

        """

        operator_dict = {'=':operator.eq, '<':operator.lt, '<=':operator.le, '>':operator.gt, '>=':operator.ge}
        condition_list = str_expr.split("AND")

        search = re.compile("([><=]?[=])")
        for elem in condition_list:
            split_list = re.split(search,elem)
            check_function = operator_dict[split_list[1]]

            #check for keyword
            if split_list[0].strip() not in header.keys():
                return False
            #now check condition
            if not check_function(header[split_list[0]].strip(), split_list[2].strip()):
                return False

        return True


def wildcard_matches(header, wildcard_key):
    """Take wildcard keyword and return all keyword name matches found in header.
    Throwing out COMMENT and HISTORY cards.

    Parameters
    ----------
    header : header object

    wildcard_key : str

    Returns
    -------
    matches : list
    """

    header_keys = header.keys()
    if 'COMMENT' in header_keys:
        header_keys.remove('COMMENT')
    if 'HISTORY' in header_keys:
        header_keys.remove('HISTORY')
    matches = header[wildcard_key].keys()
    return matches


def to_number(s):
    """Take string, change to float if possible, otherwise return string unchanged.

    Parameters
    ----------
    s : str

    Returns
    -------
    s : str or float
    """

    try:
        s = float(s)
        return s, float
    except ValueError:
        return s, str
