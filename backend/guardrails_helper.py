import re

def is_math_question(text):
    """
    Returns True if text looks like a math-related question.
    Covers: arithmetic, algebra, geometry, trigonometry, calculus, and related theory.
    """
    t = text.lower()

    math_keywords = [
        "solve", "equation", "value of", "simplify", "add", "subtract", "multiply", "divide",
        "integrate", "differentiate", "derivative", "limit", "function", "geometry", "theorem",
        "triangle", "circle", "area", "perimeter", "algebra", "calculus", "trigonometry",
        "sin", "cos", "tan", "log", "root", "square", "cube", "mean", "median", "mode",
        "probability", "statistics", "vector", "matrix", "formula", "radius", "diameter",
        "volume", "height", "base", "hypotenuse", "pythagoras", "slope"
    ]

    math_pattern = re.compile(r"[+\-*/=^]|x\d|x\^|\d+\s*x|\d+\s*[+\-*/]\s*\d+")

    if any(word in t for word in math_keywords):
        return True
    if math_pattern.search(t):
        return True
    return False


def contains_prompt_injection(text):
    """
    Detects if user input tries to override the system, inject harmful instructions,
    or request unrelated non-math tasks.
    """
    t = text.lower()

    suspicious_phrases = [
        "ignore previous", "system prompt", "change rules", "bypass", "act as", "jailbreak",
        "reveal", "show hidden", "write code", "malware", "sql injection", "prompt injection",
        "delete all", "sudo", "hack", "disable filter"
    ]

    for phrase in suspicious_phrases:
        if phrase in t:
            return True
    return False
