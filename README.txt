Python library to generate control code as:

Requirements:
 - python 2.5
 - python-crypto

Usage:

>>> from utils.controlcode import ControlCode
>>> cc = ControlCode(auth, secret)

# Direct generation passing date & nit

>>> print cc.generate(bill, amount, date=date, nit=nit)

# Batch generation with persistent date & nit

>>> cc.set_date(date).set_nit(nit)
>>> for (bill, amount) in data:
        print cc.generate(bill, amount)

Note:
 auth   - Número de Autorización
 secret - LLave de dosificación
 date   - Fecha de la factura e.g 20081010 or 2008/10/10
 nit    - NIT o CI
 bill   - Número de Factura
 amount - Monto facturado

