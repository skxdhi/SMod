import functools
from random import choice
allerrors = [item for item in dir(locals()['__builtins__']) if "Error" in item or "Exception" in item]
def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)
def raise_random_error():
    global allerrors
    raise choice(allerrors)
    
    
