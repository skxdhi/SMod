import pygame

screen = pygame.display.get_surface()

class UI:
    def __init__(self, elements):
        self.elements = elements

    def draw(self):
        for element in self.elements:
            element.draw()

    def click(self):
        for element in self.elements:
            if getattr(element, "hover", None):
                if not element.hover():
                    continue
            else:
                continue
            if getattr(element, "click", None):
                element.click()

    def hover(self):
        for element in self.elements:
            if getattr(element, "hover", None):
                if element.hover():
                    return element
        return None

class ButtonTemplate:
    def __init__(self, x, y, width, height, func, anchor="top-left"):
        self.base_x = x
        self.base_y = y
        self.width = width
        self.height = height
        self.func = func
        self.anchor = anchor.lower()

    @property
    def x(self):
        screen_width = screen.get_width()
        if "right" in self.anchor:
            return screen_width - self.base_x - self.width
        elif "center" in self.anchor:
            return (screen_width // 2) - (self.width // 2) + self.base_x
        return self.base_x

    @property
    def y(self):
        screen_height = screen.get_height()
        if "bottom" in self.anchor:
            return screen_height - self.base_y - self.height
        elif "center" in self.anchor:
            return (screen_height // 2) - (self.height // 2) + self.base_y
        return self.base_y

    def click(self):
        self.func(self)

    def hover(self):
        mx, my = pygame.mouse.get_pos()
        return self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height

class ImageButton(ButtonTemplate):
    def __init__(self, x, y, width, height, image, func, anchor="top-left"):
        super().__init__(x, y, width, height, func, anchor)
        self.image = image

    def draw(self):
        surf = self.image.copy()
        surf = pygame.transform.scale(surf, (int(self.width), int(self.height)))
        screen.blit(surf, (self.x, self.y))