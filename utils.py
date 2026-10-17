import functools, pygame
import math
import functools
from random import choice
allerrors = [item for item in dir(locals()['__builtins__']) if "Error" in item or "Exception" in item]

def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)
  
def raise_random_error():
    global allerrors
    raise choice(allerrors)


def get_darkest_color(surface: pygame.Surface):
    with pygame.PixelArray(surface) as pixel_array:
        unique_mapped_colors = {color for row in pixel_array for color in row}

    unique_colors = [surface.unmap_rgb(color_int) for color_int in unique_mapped_colors]
    unique_colors = [c for c in unique_colors if getattr(c, 'a', 255) > 0]

    def get_brightness(color):
        return 0.299 * color.r + 0.587 * color.g + 0.114 * color.b

    sorted_colors = sorted(unique_colors, key=get_brightness)
    return sorted_colors[0]

def distance(a: tuple, b: tuple):
    ax, ay = a
    bx, by = b
    return math.sqrt((bx-ax)**2 + (by-ay)**2)

def to4(radians):
    return radians/(2*math.pi)*4

def torad(ang4):
    return ang4/4*(2*math.pi)

cos4 = lambda x: to4(math.cos(torad(x)))
sin4 = lambda x: to4(math.sin(torad(x)))

def lerp(a, b, t):
    if a is None: return b
    diff = (b - a)
    return a + diff*t

def lerp_angle(a, b, t):
    if a is None: return b
    diff = (b - a) % 4
    if diff > 2:
        diff -= 4
    return (a + diff * t) % 4

def polar_lerp(a: tuple, b: tuple, center: tuple, t):
    ra, rb = distance(a, center), distance(b, center)
    ang_a = math.atan2(a[1] - center[1], a[0] - center[0])
    ang_b = math.atan2(b[1] - center[1], b[0] - center[0])

    radius = lerp(ra, rb, t)
    angle = torad(lerp_angle(to4(ang_a), to4(ang_b), t))

    return center[0]+math.cos(angle)*radius, center[1]+math.sin(angle)*radius
