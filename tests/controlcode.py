# test

from __future__ import with_statement

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

FILENAME = os.path.join(os.path.dirname(__file__), '5000CasosPruebaCCVer7.txt')

if __name__ == '__main__':
    from utils.controlcode import ControlCode

    with open(FILENAME) as file:
        firstline = True

        valid_count = 0
        invalid_count = 0

        fails = []

        for line in file:
            if firstline:
                firstline = False
                continue

            data = line.strip().strip('|').split('|')
            (auth, bill, nit, date, amount, secret) = data[:6]
            valid_code = data[-1]

            # cast valid values
            auth = int(auth)
            bill = int(bill)
            amount = float(amount.replace(',', '.'))
            nit = int(nit)

            cc = ControlCode(int(auth), secret)
            generated_code = cc.generate(bill, amount, date=date, nit=nit)

            if generated_code == valid_code:
                result = 'OK'
                valid_count += 1

                sys.stdout.write('\r ')
                if valid_count % 3 == 0:
                    sys.stdout.write('|')
                elif valid_count % 3 == 1:
                    sys.stdout.write('/')
                elif valid_count % 3 == 2:
                    sys.stdout.write('\\')
            else:
                invalid_count += 1
                result = 'Wrong, valid code: ' + valid_code
                print 'Generated Code:', generated_code, result
                fails.append(line)

        print ''
        print 'Total valid:', valid_count
        print 'Total invalid:', invalid_count


