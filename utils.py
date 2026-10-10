import functools, random
def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

def raise_random_error():
    # the game was crashing because you didnt include this function
    pass