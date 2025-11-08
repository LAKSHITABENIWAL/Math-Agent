# arithmetic_helper.py
import re
from math import isfinite

# Accept + - * / ^ and common unicode multiply signs
_ARITH_RE = re.compile(
    r'^\s*([-+]?\d+(?:\.\d+)?|\.\d+)\s*([+\-×x\*\/\^])\s*([-+]?\d+(?:\.\d+)?|\.\d+)\s*$',
    flags=re.IGNORECASE
)

def try_compute_arithmetic(text: str):
    """
    If text is a simple two-operand arithmetic expression (like "3+10" or " 12 / 4 "),
    return the result as a string. Otherwise return None.
    """
    if not isinstance(text, str):
        return None
    t = text.strip()
    # normalize common unicode multiply sign
    t = t.replace('×', '*').replace('X', '*').replace('x', '*')
    m = _ARITH_RE.match(t)
    if not m:
        return None
    a_s, op, b_s = m.group(1), m.group(2), m.group(3)
    try:
        a = float(a_s)
        b = float(b_s)
    except Exception:
        return None

    try:
        if op in ('+',):
            res = a + b
        elif op in ('-',):
            res = a - b
        elif op in ('*', '×', 'x'):
            res = a * b
        elif op == '/' or op == '÷':
            if b == 0:
                return "Division by zero error"
            res = a / b
        elif op == '^':
            res = a ** b
        else:
            return None

        # format: integer-like without decimal
        if isinstance(res, float) and res.is_integer():
            return str(int(res))
        # prevent weird floats like inf/nan
        if not isfinite(res):
            return None
        # limit length
        s = repr(res)
        return s
    except Exception:
        return None
