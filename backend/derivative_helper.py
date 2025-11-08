# derivative_helper.py
def try_derivative_lookup(text: str):
    """
    Very small lookup for common simple derivative queries.
    Returns a brief answer string or None.
    Examples: "d/dx x^2", "derivative of x^2", "derivative sin(x)"
    """
    if not isinstance(text, str):
        return None
    t = text.lower().replace(' ', '')
    # basic patterns
    if 'd/dx' in t or t.startswith('derivative') or t.startswith('deriv'):
        # x^n
        if 'x^2' in t or 'x**2' in t:
            return 'Derivative of x^2 is 2x'
        if 'x^3' in t or 'x**3' in t:
            return 'Derivative of x^3 is 3x^2'
        if 'sin(x)' in t or 'sinx' in t:
            return 'Derivative of sin(x) is cos(x)'
        if 'cos(x)' in t or 'cosx' in t:
            return 'Derivative of cos(x) is -sin(x)'
        if 'ln(x)' in t or 'log(x)' in t:
            return 'Derivative of ln(x) is 1/x'
    return None
