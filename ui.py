import pygame


class UI:
    def __init__(self, elements=None):
        self.elements = elements if elements is not None else []
        self.enabled = True

    def clear(self, *inputs):
        if len(inputs) == 0:
            self.elements = []
            return
        self.elements = [
            b for b in self.elements
            if not any(i in getattr(b, "tag", "") for i in inputs)
        ]

    def draw(self):
        if not self.enabled: return
        for element in self.elements:
            element.draw()

    def click(self):
        if not self.enabled: return
        for element in self.elements:
            if getattr(element, "hover", None):
                if not element.hover():
                    continue
            else:
                continue
            if getattr(element, "click", None):
                element.click()

    def hover(self):
        if not self.enabled: return
        for element in self.elements:
            if getattr(element, "hover", None):
                if element.hover():
                    return element
        return None

    def update_animation(self, dt):
        if not self.enabled: return
        for element in self.elements:
            element.update_animation(dt)


class ButtonTemplate:
    def __init__(self, x, y, width, height, func, anchor="top-left", enabled=True, anim_start_pos=None, tag=""):
        self.base_x = x
        self.base_y = y
        self.width = width
        self.height = height
        self.func = func
        self.anchor = anchor.lower()
        self.enabled = enabled
        self.tag = tag
        self.anim_progress = 0.0
        self.anim_start_pos = anim_start_pos if anim_start_pos else (0, 0)

    @property
    def target_x(self):
        screen = pygame.display.get_surface()
        screen_width = screen.get_width() if screen else 800
        if "right" in self.anchor:
            return screen_width - self.base_x - self.width
        elif "center" in self.anchor:
            return (screen_width // 2) - (self.width // 2) + self.base_x
        return self.base_x

    @property
    def target_y(self):
        screen = pygame.display.get_surface()
        screen_height = screen.get_height() if screen else 600
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
        if not self.enabled:
            return
        self.func(self)

    def hover(self):
        if not self.enabled:
            return False
        mx, my = pygame.mouse.get_pos()
        return self.x <= mx <= self.x + self.width and self.y <= my <= self.y + self.height


class ImageButton(ButtonTemplate):
    def __init__(self, x, y, width, height, image, func, anchor="top-left", enabled=True, anim_start_pos=None, tag=""):
        super().__init__(x, y, width, height, func, anchor, enabled, anim_start_pos, tag)
        self.image = pygame.transform.scale(image, (int(max(1, width)), int(max(1, height))))
        self.angle = 0

    def draw(self):
        if not self.enabled:
            return

        screen = pygame.display.get_surface()

        surf = pygame.transform.rotate(self.image, self.angle)
        surf.set_alpha(250 if self.hover() else 210)

        rect = surf.get_rect(
            center=(
                int(self.x + self.width / 2),
                int(self.y + self.height / 2)
            )
        )

        screen.blit(surf, rect)


class TextButton(ButtonTemplate):
    def __init__(self, x, y, width, height, text, font, func, anchor="top-left", enabled=True, anim_start_pos=None,
                 text_color=(255, 255, 255), bg_color=(80, 80, 80), hover_bg_color=(100, 100, 100),
                 border_color=(50, 50, 50), tag=""):
        super().__init__(x, y, width, height, func, anchor, enabled, anim_start_pos, tag)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.bg_color = bg_color
        self.hover_bg_color = hover_bg_color
        self.border_color = border_color

    def draw(self):
        if not self.enabled: return
        screen = pygame.display.get_surface()

        current_bg = self.hover_bg_color if self.hover() else self.bg_color

        rect = pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))
        pygame.draw.rect(screen, current_bg, rect)
        pygame.draw.rect(screen, self.border_color, rect, width=2)

        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)


class TextInput(ButtonTemplate):
    """Simple single-line text input. Click to focus, type to edit, Enter to confirm, Escape to cancel."""
    def __init__(self, x, y, width, height, font, initial="", on_confirm=None, on_cancel=None,
                 anchor="top-left", enabled=True, numeric=False, allow_float=False,
                 text_color=(255, 255, 255), bg_color=(40, 40, 40),
                 active_bg=(50, 50, 70), border_color=(100, 100, 100),
                 active_border=(120, 160, 220), tag=""):
        super().__init__(x, y, width, height, lambda b: None, anchor, enabled, None, tag)
        self.font = font
        self.text = str(initial)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.numeric = numeric
        self.allow_float = allow_float
        self.text_color = text_color
        self.bg_color = bg_color
        self.active_bg = active_bg
        self.border_color = border_color
        self.active_border = active_border
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0.0
        self._original = self.text

    def activate(self):
        self.active = True
        self._original = self.text
        self.cursor_visible = True
        self.cursor_timer = 0.0

    def deactivate(self, confirm=True):
        if not self.active:
            return
        self.active = False
        if confirm:
            if self.on_confirm:
                self.on_confirm(self.text)
        else:
            self.text = self._original
            if self.on_cancel:
                self.on_cancel()

    def click(self):
        if not self.enabled:
            return
        self.activate()

    def handle_key(self, event):
        """Call this from the main KEYDOWN loop when this input might be active.
        Returns True if the event was consumed."""
        if not self.active or not self.enabled:
            return False

        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self.deactivate(confirm=True)
            return True
        if event.key == pygame.K_ESCAPE:
            self.deactivate(confirm=False)
            return True
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return True

        char = event.unicode
        if not char:
            return False

        if self.numeric:
            allowed = "0123456789-"
            if self.allow_float:
                allowed += "."
            if char not in allowed:
                return True  # consume but ignore invalid
            # basic validation: only one dot, minus only at start
            if char == '.' and '.' in self.text:
                return True
            if char == '-' and (self.text or self.text.startswith('-')):
                return True

        self.text += char
        return True

    def update_animation(self, dt):
        super().update_animation(dt)
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 0.5:
                self.cursor_timer = 0.0
                self.cursor_visible = not self.cursor_visible

    def draw(self):
        if not self.enabled:
            return
        screen = pygame.display.get_surface()
        rect = pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

        bg = self.active_bg if self.active else self.bg_color
        border = self.active_border if self.active else self.border_color

        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, width=2, border_radius=4)

        display = self.text
        if self.active and self.cursor_visible:
            display += "|"

        text_surf = self.font.render(display if display else " ", True, self.text_color)
        # left-align with a little padding
        text_x = rect.x + 10
        text_y = rect.y + (rect.height - text_surf.get_height()) // 2
        # clip if too long
        max_w = rect.width - 20
        if text_surf.get_width() > max_w:
            # show the end of the string
            while text_surf.get_width() > max_w and len(display) > 1:
                display = display[1:]
                text_surf = self.font.render(display, True, self.text_color)
        screen.blit(text_surf, (text_x, text_y))


class Slider(ButtonTemplate):
    """Horizontal slider. Click the track (or the handle) and drag to change the value.
    Layout, left to right: label | track | value text.
    on_change(value) is called every time the value changes."""
    def __init__(self, x, y, width, height, min_val=0, max_val=100, value=None, on_change=None,
                 font=None, label="", step=1, anchor="top-left", enabled=True, anim_start_pos=None,
                 label_width=0, value_width=0,
                 track_color=(40, 40, 40), fill_color=(120, 160, 220), handle_color=(230, 230, 230),
                 handle_hover_color=(255, 255, 255), border_color=(100, 100, 100),
                 text_color=(255, 255, 255), tag=""):
        super().__init__(x, y, width, height, lambda b: None, anchor, enabled, anim_start_pos, tag)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.on_change = on_change
        self.font = font
        self.label = label
        self.label_width = label_width
        self.value_width = value_width
        self.track_color = track_color
        self.fill_color = fill_color
        self.handle_color = handle_color
        self.handle_hover_color = handle_hover_color
        self.border_color = border_color
        self.text_color = text_color
        self.dragging = False
        self._was_pressed = False
        self._value = self._clean(min_val if value is None else value)

    def _clean(self, v):
        v = max(self.min_val, min(self.max_val, v))
        if self.step:
            v = self.min_val + round((v - self.min_val) / self.step) * self.step
            v = max(self.min_val, min(self.max_val, v))
        if isinstance(self.step, int) and isinstance(self.min_val, int):
            v = int(round(v))
        return v

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self.set_value(v)

    def set_value(self, v, notify=False):
        v = self._clean(v)
        changed = v != self._value
        self._value = v
        if changed and notify and self.on_change:
            self.on_change(v)

    @property
    def fraction(self):
        span = self.max_val - self.min_val
        return 0.0 if span == 0 else (self._value - self.min_val) / span

    def track_rect(self):
        left = self.x + self.label_width
        right = self.x + self.width - self.value_width
        return pygame.Rect(int(left), int(self.y), int(max(1, right - left)), int(self.height))

    def _value_from_mouse(self, mx):
        track = self.track_rect()
        t = (mx - track.left) / track.width
        t = max(0.0, min(1.0, t))
        return self.min_val + t * (self.max_val - self.min_val)

    def click(self):
        pass

    def _update_input(self):
        pressed = pygame.mouse.get_pressed()[0]
        mx, my = pygame.mouse.get_pos()
        if not pressed:
            self.dragging = False
        elif not self._was_pressed and self.hover():
            self.dragging = True
        self._was_pressed = pressed
        if self.dragging:
            self.set_value(self._value_from_mouse(mx), notify=True)

    def draw(self):
        if not self.enabled:
            return
        self._update_input()
        screen = pygame.display.get_surface()
        track = self.track_rect()
        mid_y = track.centery

        bar = pygame.Rect(track.left, mid_y - 4, track.width, 8)
        pygame.draw.rect(screen, self.track_color, bar, border_radius=4)
        fill_w = int(track.width * self.fraction)
        if fill_w > 0:
            pygame.draw.rect(screen, self.fill_color, pygame.Rect(bar.left, bar.top, fill_w, bar.height), border_radius=4)
        pygame.draw.rect(screen, self.border_color, bar, width=1, border_radius=4)

        handle_w = max(8, int(self.height * 0.4))
        handle = pygame.Rect(0, 0, handle_w, int(self.height))
        handle.center = (track.left + fill_w, mid_y)
        handle.clamp_ip(pygame.Rect(track.left - handle_w // 2, track.top, track.width + handle_w, track.height))
        active = self.dragging or self.hover()
        pygame.draw.rect(screen, self.handle_hover_color if active else self.handle_color, handle, border_radius=3)
        pygame.draw.rect(screen, self.border_color, handle, width=2, border_radius=3)

        if self.font is not None:
            if self.label and self.label_width:
                surf = self.font.render(self.label, True, self.text_color)
                screen.blit(surf, (int(self.x), mid_y - surf.get_height() // 2))
            if self.value_width:
                surf = self.font.render(str(self._value), True, self.text_color)
                screen.blit(surf, (int(self.x + self.width - self.value_width + 10), mid_y - surf.get_height() // 2))


class ColorSwatch(ButtonTemplate):
    """A square that shows a colour. get_color is a function returning an (r, g, b) tuple."""
    def __init__(self, x, y, width, height, get_color, anchor="top-left", enabled=True, anim_start_pos=None,
                 border_color=(50, 50, 50), tag=""):
        super().__init__(x, y, width, height, lambda b: None, anchor, enabled, anim_start_pos, tag)
        self.get_color = get_color
        self.border_color = border_color

    def click(self):
        pass

    def draw(self):
        if not self.enabled:
            return
        screen = pygame.display.get_surface()
        rect = pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))
        r, g, b = (max(0, min(255, int(c))) for c in self.get_color()[:3])
        pygame.draw.rect(screen, (r, g, b), rect)
        pygame.draw.rect(screen, self.border_color, rect, width=3)