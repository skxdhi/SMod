import functools, pygame
def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

def raise_random_error():
    # the game was crashing because you didnt include this function
    pass


def get_darkest_color(surface: pygame.Surface):
    with pygame.PixelArray(surface) as pixel_array:
        unique_mapped_colors = {color for row in pixel_array for color in row}

    unique_colors = [surface.unmap_rgb(color_int) for color_int in unique_mapped_colors]
    unique_colors = [c for c in unique_colors if getattr(c, 'a', 255) > 0]

    def get_brightness(color):
        return 0.299 * color.r + 0.587 * color.g + 0.114 * color.b

    sorted_colors = sorted(unique_colors, key=get_brightness)
    return sorted_colors[0]
