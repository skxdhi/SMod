import pygame

screen = pygame.display.get_surface()


class UI:
    def __init__(self, elements):
        self.elements = elements

    def clear(self, *inputs):
        if len(inputs) == 0:
            self.elements = []
            return
        self.elements = [
            b for b in self.elements
            if not any(i in b.tag for i in inputs)
        ]

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

    def update_animation(self, dt):
        for element in self.elements:
            element.update_animation(dt)


class ButtonTemplate:
    def __init__(self, x, y, width, height, func, anchor="top-left", enabled=True, anim_start_pos=None):
        self.base_x = x
        self.base_y = y
        self.width = width
        self.height = height
        self.func = func
        self.anchor = anchor.lower()
        self.enabled = enabled
        self.anim_progress = 0.0
        # Treated as a relative offset from the anchor target position
        self.anim_start_pos = anim_start_pos if anim_start_pos else (0, 0)

    @property
    def target_x(self):
        screen_width = screen.get_width()
        if "right" in self.anchor:
            return screen_width - self.base_x - self.width
        elif "center" in self.anchor:
            return (screen_width // 2) - (self.width // 2) + self.base_x
        return self.base_x

    @property
    def target_y(self):
        screen_height = screen.get_height()
        if "bottom" in self.anchor:
            return screen_height - self.base_y - self.height
        elif "center" in self.anchor:
            return (screen_height // 2) - (self.height // 2) + self.base_y
        return self.base_y

    @property
    def start_x(self):
        return self.target_x + self.anim_start_pos[0]

    @property
    def start_y(self):
        return self.target_y + self.anim_start_pos[1]

    @property
    def x(self):
        sx = self.start_x
        tx = self.target_x
        return sx + (tx - sx) * self.anim_progress

    @property
    def y(self):
        sy = self.start_y
        ty = self.target_y
        return sy + (ty - sy) * self.anim_progress

    def update_animation(self, dt):
        if self.anim_progress < 1.0:
            self.anim_progress = min(1.0, self.anim_progress + dt * 8.0)

    def click(self):
        self.func(self)

    def hover(self):
        mx, my = pygame.mouse.get_pos()
        if not self.enabled:
            return False
        tx, ty = self.target_x, self.target_y
        return tx <= mx <= tx + self.width and ty <= my <= ty + self.height


class ImageButton(ButtonTemplate):
    def __init__(self, x, y, width, height, image, func, anchor="top-left", enabled=True, anim_start_pos=None):
        super().__init__(x, y, width, height, func, anchor, enabled, anim_start_pos)
        self.image = image

    def draw(self):
        current_w = int(self.width)
        current_h = int(self.height)

        surf = self.image.copy()
        surf = pygame.transform.scale(surf, (max(1, current_w), max(1, current_h)))

        draw_x = self.x + (self.width - current_w) // 2
        draw_y = self.y + (self.height - current_h) // 2
        screen.blit(surf, (draw_x, draw_y))