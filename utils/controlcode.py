# -*- encoding: utf-8 -*-
# see http://www.impuestos.gov.bo/Facturacion/CodigoControlV7.pdf

__author__ = "Rolando Espinoza La fuente <darkrho@gmail.com>"
__version__ = "0.2"
__date__ = "Date: 2008/10/15"
__copyright__ = "Copyright (c) 2008 Rolando Espinoza La fuente"
__license__ = "BSD"

import re

# local modules
import base64, rc4, verhoeff

DEBUG = False
## Helper functions
def debug(s, level=0):
    if DEBUG:
        indent = '>>'
        print indent * (level+1), s

# only matchs valid characters for secret key
REGEX_SECRET = re.compile(r'^[A-NP-Za-kmnp-z2-9=#\(\)\*\+\-_\\@\[\]\{\}%\$]+$')

# date format. ex. 1900-2999 01-12 01-31
REGEX_DATE = re.compile(r'^(19|20)[0-9]{2}(0[1-9]|1[0-2])(0[0-9]|[1-2][0-9]|3[0-1])$')
REGEX_DATE_FORMAT = re.compile(r'^(19|20)[0-9]{2}/(0[1-9]|1[0-2])/(0[1-9]|[1-2][0-9]|3[0-1])$')


class CCException(Exception):
    pass

class InvalidParam(CCException):
    pass

class ControlCode(object):
    """ControlCode generator"""


    def __init__(self, auth, secret):
        # auth number
        # secret key
        self.set_auth(auth) \
            .set_secret(secret)

        # initialize params
        self._bill = 0
        self._nit = 0
        self._date = 0
        self._amount = 0

    #
    # generation
    #

    def generate(self, bill, amount, **kwargs):
        """Changing values are bill & amount
           the others can be persisten through
           the instance (date, nit).
           Persistence values can be overrided by
           keyword argument"""
        # round amount upper if >= .5
        amount = int(round(amount))

        # nit
        if kwargs.has_key('nit'):
            nit = self.set_nit(kwargs['nit']).get_nit();
        else:
            nit = self.get_nit()

        # date
        if kwargs.has_key('date'):
            date = self.set_date(kwargs['date']).get_date();
        else:
            date = self.get_date()

        # validate parameters
        if not self.validate_bill(bill):
            raise InvalidParam('Invalid bill %s' % bill)

        if not self.validate_amount(amount):
            raise InvalidParam('Invalid amount %s' % amount)

        if not self.validate_nit(nit):
            raise InvalidParam('Invalid nit %s' % nit)

        if not self.validate_date(date):
            raise InvalidParam('Invalid date %s' % date)

        ##
        ## Start process
        ##

        ## get persistent parameters
        auth = self.get_auth()
        secret = self.get_secret()

        debug('Begining process')

        ##
        ## step 1
        ##
        verhoeff5 = self._step1_verhoeff_5digits(bill, nit, date, amount)
        debug('Verhoeff 5 Digits: ' + repr(verhoeff5), 1)

        ##
        ## step2
        ##
        strings = self._step2_slice_secret_by_verhoeff(verhoeff5)
        debug('String Slices: ' + repr(strings), 1)

        ## concatenate
        long_string = ''

        for s1,s2 in zip((auth, bill, nit, date, amount), strings):
            ## add two verhoeff digits to each param
            ## but auth
            if s1 != auth:
                s1 = str(s1) + verhoeff.encode(s1, 2)
            ## concatenate string
            long_string += str(s1) + str(s2)

        debug('Long String: ' + repr(long_string), 2)

        ##
        ## step3
        ##
        long_string_rc4 = self._step3_encode_allegedrc4(verhoeff5, long_string)
        debug('ARC4 Long String: ' + repr(long_string_rc4), 1)

        ##
        ## step4
        ##
        partial_sums = self._step4_partial_sums(long_string_rc4)
        debug('Partial Sums: ' + repr(partial_sums), 2)
        debug('Total Sum: ' + str(sum(partial_sums)), 2)

        ##
        ## step5
        ##
        base64_string = self._step5_base64_sum(verhoeff5, partial_sums)
        debug('Base64 String: ' + base64_string, 1)

        ##
        ## step6
        ##
        code = self._step6_get_code(verhoeff5, base64_string)
        debug('Raw Code: ' + code, 1)

        ##
        ## Return print-ready code
        ##
        return self._format_code(code)


    #
    # Gen code algorithm step by step methods
    #
    def _step1_verhoeff_5digits(self, bill, nit, date, amount):
        # dummy verhoeff numbers
        data = (bill, nit, date, amount)
        # append two verhoeff numbers to each param
        sum1 = sum([int(str(d) + verhoeff.encode(d, 2)) for d in data])
        # generate 5 verhoeff digits
        return verhoeff.encode(sum1, 5)

    def _step2_slice_secret_by_verhoeff(self, verhoeff):
        # add 1 to each verhoeff digit
        slices = [int(n)+1 for n in verhoeff]

        strings = []
        index = 0
        for length in slices:
            # slice secret
            strings.append(self.get_secret()[index:index+length])
            # move index
            index += length

        return strings

    def _step3_encode_allegedrc4(self, verhoeff, long_string):
        seed = self.get_secret() + verhoeff
        return rc4.encrypt(long_string, seed)

    def _step4_partial_sums(self, long_string_rc4):
        sums = [0] * 5; i = 0
        for c in long_string_rc4:
            sums[i % 5] += ord(c)
            i += 1
        return sums

    def _step5_base64_sum(self, verhoeff, partial_sums):
        divs = [int(d) + 1 for d in verhoeff]
        total = sum(partial_sums)
        result = 0
        for partial,div in zip(partial_sums, divs):
            result += (total * partial) / div
        return base64.encode_integer(result)

    def _step6_get_code(self, verhoeff, base64_string):
        seed = self.get_secret() + verhoeff
        return rc4.encrypt(base64_string, seed)


    def _format_code(self, code):
        formatted = ''
        sep = '-'; length = len(code)
        for i in range(length):
            formatted += code[i]
            if (i+1) % 2 == 0 and (i+1) < length:
                formatted += sep
        return formatted

    #
    # Getters & Setters
    #
    def get_auth(self):
        return self._auth

    def set_auth(self, auth):
        if self.validate_auth(auth):
            self._auth = auth
        else:
            raise InvalidParam('Invalid auth %s' % auth)
        return self

    def get_secret(self):
        return self._secret

    def set_secret(self, secret):
        if self.validate_secret(secret):
            self._secret = secret
        else:
            raise InvalidParam('Invalid secret %s' % secret)
        return self

    def get_bill(self):
        return self._bill

    def set_bill(self, bill):
        if self.validate_bill(bill):
            self._bill = bill
        else:
            raise InvalidParam('Invalid bill %s' % bill)
        return self

    def get_nit(self):
        return self._nit

    def set_nit(self, nit):
        if self.validate_nit(nit):
            self._nit = nit
        else:
            raise InvalidParam('Invalid nit %s' % nit)
        return self

    def get_date(self):
        return self._date

    def set_date(self, date):
        if isinstance(date, str) and REGEX_DATE_FORMAT.match(date):
            date = int(date.replace('/', ''))

        if self.validate_date(date):
            self._date = date
        else:
            raise InvalidParam('Invalid date %s' % date)
        return self

    def get_amount(self):
        return self._amount

    def set_amount(self, amount):
        if self.validate_amount(amount):
            self._amount = amount
        else:
            raise InvalidParam('Invalid amount %s' % amount)
        return self


    #
    # Validators
    #

    def validate_auth(self, auth):
        """check for integer and 15 digits len"""
        return isinstance(auth, (int,long)) and 1 <= len(str(auth)) <= 15

    def validate_secret(self, secret):
        return isinstance(secret, str) and 1 <= len(secret) <= 256 and REGEX_SECRET.match(secret)

    def validate_bill(self, bill):
        return isinstance(bill, (int,long)) and 1 <= len(str(bill)) <= 12

    def validate_nit(self, nit):
        return isinstance(nit, (int,long)) and 1 <= len(str((nit))) <= 12

    def validate_date(self, date):
        return isinstance(date, int) and REGEX_DATE.match(str(date))

    def validate_amount(self, amount):
        return isinstance(amount, (int,float,long)) and amount > 0


if __name__ == '__main__':
    """Test again example"""

    #TODO: use pyunit for testing

    data = {
            'auth': 29040011007,
            'bill': 1503,
            'nit': 4189179011,
            #'date': 20070702,
            'date': '2007/07/02',
            'amount': 2500,
            'secret': '9rCB7Sv4X29d)5k7N%3ab89p-3(5[A'
            }

    results = {
            'step1': 71621, # 5 verhoeff digits
            'step2': ('9rCB7Sv4', 'X2', '9d)5k7N', '%3a', 'b8'), # 5 string slices
            'step3': '69DD0A42536C9900C4AE6484726C122ABDBF95D80A4BA403FB7834B3EC2A88595E2149A3D965923BA4547B42B9528AAE7B8CFB9996BA2B58516913057C9D791B6B748A', # rc4 encoded string
            'step4': (7720, 1548, 1537, 1540, 1565, 1530), # total & partial sums
            'step5': '18isw', # base64 string
            'step6': '6ADC530514' # rc4 encoded string
            }

    DEBUG = True

    print repr(data)

    cc = ControlCode(data['auth'], data['secret'])

    cc.set_date(data['date']) \
      .set_nit(data['nit'])

    control_code = cc.generate(data['bill'], data['amount'])

    print 'Generated Code:', control_code


