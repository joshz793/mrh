import re
from pyscf.dft.libxc import XC_ALIAS, XC_CODES, XC_KEYS
from pyscf.dft.libxc import hybrid_coeff, rsh_coeff

XC_ALIAS_KEYS = set (XC_ALIAS.keys ())
XC_TYPE_HDR = tuple (['LDA_','GGA_','MGGA_'])
INTCODES_TYPES = {}
INTCODES_HYB = []
for key, val in XC_CODES.items ():
    mykey = key
    if key.startswith ('HYB_'):
        INTCODES_HYB.append (val)
        mykey = key[4:]
    if mykey.startswith (XC_TYPE_HDR):
        words = mykey.split ('_')
        INTCODES_TYPES[val] = words[1]
INTCODES_HYB = set (INTCODES_HYB)

class XCSplitError (RuntimeError):
    def __init__(self, xc):
        super().__init__('')
        self.path = '{}->?'.format (xc)
    def __str__(self):
        return self.message + '\npath = ' + self.path
    def extend (self, xc):
        self.path = self.path[:-1] + '{}->?'.format (xc)
    def __call__(self, message):
        self.message = message
        return self

def split_x_c_comma (xc):
    '''Split an xc code string into two separate strings, one for
    exchange and one for correlation, by finding a comma in the string
    or in some alias'''
    xc = xc.upper ()
    myerr = XCSplitError (xc)
    max_recurse = 5
    for i in range (max_recurse):
        if ',' in xc:
            break
        elif xc in XC_ALIAS_KEYS:
            xc = XC_ALIAS[xc]
        elif isinstance (XC_CODES[xc], int):
            xc_int = XC_CODES[xc]
            if xc_int in INTCODES_HYB:
                raise myerr ('LibXC built-in hybrid')
            xc_type = INTCODES_TYPES[xc_int]
            if xc_type == 'X':
                xc = xc + ','
            elif xc_type == 'C':
                xc = ',' + xc
            elif xc_type == 'XC':
                raise myerr ('LibXC built-in X+C functional')
            elif xc_type == 'K':
                raise myerr ('Kinetic energy functional')
            else:
                raise myerr ('Unknown functional type {} for code {}'.format (
                    xc_type, xc_int))
        elif xc in XC_KEYS:
            xc = XC_CODES[xc]
        else:
            raise myerr
        myerr.extend (xc)
    if not ',' in xc:
        raise myerr ('Maximum XC alias recursion depth')
    return xc.split (',')

def is_hybrid_or_rsh (xc_code):
    hyb = hybrid_coeff (xc_code)
    omega, alpha, beta = rsh_coeff (xc_code)
    non0 = [abs (x)>1e-10 for x in (hyb, omega)]
    return any (non0)

def is_hybrid_xc (xc_code):
    hyb = hybrid_coeff (xc_code)
    return abs (hyb)>1e-10

def parse_xc_formula (xc_code):
    if ',' in xc_code:
        x_code, c_code = xc_code.split (',')
        x_facs, x_fnals = _parse_xc_formula (x_code)
        c_facs, c_fnals = _parse_xc_formula (c_code)
        return x_facs+c_facs, x_fnals+c_fnals
    return _parse_xc_formula (xc_code)

def _parse_xc_formula (xc_code):
    facs = []
    fnals = []
    for token in xc_code.replace('-','+-').replace(';+',';').split('+'):
        sign = 1
        if not len (token): continue
        if token[0] == '-':
            sign = -1
            token = token[1:]
        if '*' in token:
            fac, fnal = token.split ('*')
            if fac[0].isalpha ():
                fac, fnal = fnal, fac
            fac = sign * float (fac)
        else:
            fac = sign
            fnal = token
        facs.append (fac)
        fnals.append (fnal)
    return facs, fnals

def assemble_xc_formula (facs, terms):
    code = []
    for fac, term in zip (facs, terms):
        fac = '{:.16f}'.format (round (fac,14))
        fac = fac.rstrip ('0').rstrip ('.')
        code.append ('{:s}*{:s}'.format (fac, term))
    code = '+'.join (code).replace ('+-','-')
    return code

