# linear_equation_solver.py (safer version)

import re

def try_solve_linear(text: str):
    """
    Conservative single-variable linear solver for forms like:
      2x + 5 = 15
      x - 3 = 2
      -x + 4 = 1

    Returns 'x = <value>' or None when it cannot confidently solve.
    This version refuses to handle expressions that look non-linear
    (x^2, x2, powers, etc).
    """
    if not isinstance(text, str):
        return None

    t = text.strip().replace(" ", "")
    # quick rejects: must contain '=' and 'x'
    if '=' not in t or 'x' not in t.lower():
        return None

    # Reject if there are obvious non-linear patterns
    if re.search(r'(\^|[²³]|x\s*\d)', t, flags=re.IGNORECASE):
        return None

    # Normalize uppercase X
    left, right = t.split('=', 1)
    left = left.replace('X', 'x')

    # Replace standalone 'x' or '+x' or '-x' with '1x' and '-1x' safely
    def repl_standalone(match):
        prefix = match.group(1) or ""
        return prefix + "1x"
    left = re.sub(r'(^|[+\-])x', repl_standalone, left)

    # find coefficient a of ax
    ax_match = re.search(r'([+\-]?\d+(?:\.\d+)?)x', left)
    if not ax_match:
        return None
    try:
        a = float(ax_match.group(1))
    except Exception:
        return None

    # remove ax term and sum remaining constants on left
    left_without_ax = left[:ax_match.start()] + left[ax_match.end():]
    consts = re.findall(r'([+\-]?\d+(?:\.\d+)?)', left_without_ax)
    b = sum(float(c) for c in consts) if consts else 0.0

    # right side must be numeric and not contain 'x'
    if 'x' in right.lower():
        return None
    try:
        c = float(right)
    except Exception:
        return None

    if a == 0:
        return None
    x = (c - b) / a
    if float(x).is_integer():
        return f"x = {int(x)}"
    return f"x = {x}"
