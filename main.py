import math
import os
import sys
import textwrap

import pygame


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


pygame.init()
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
running = True
pygame.font.init()
font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 32)
small_font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 20)

fancy_graphics = True

import ui

UI = ui.UI([])

from loader import images, audio
import cells

grid = cells.grid
Cell = cells.Cell
pygame.display.set_caption("Cell Machine SMod")
pygame.display.set_icon(pygame.image.load(resource_path("icon.ico")).convert_alpha())
clock = pygame.time.Clock()

cell_size = 32

selected_cell = {
    "name": "mover",
    "direction": 0,
}

celltypes = {
    "mover": {"desc": "Moves one space per tick in the direction it is pointing, pushing the cells in its way."},
    "push": {"desc": "Does absolutely nothing, but cells can still interact with it."},
    "one directional": {"desc": "Can ony be pushed on the indicated side."},
    "two directional": {"desc": "Can ony be pushed on the indicated sides."},
    "slide": {"desc": "Can only be pushed on the indicated sides."},
    "three directional": {"desc": "Can ony be pushed on the indicated sides."},
    "zero directional": {"desc": "Can ony be pushed on the indicated sides, except there is no indicated sides."},
    "random push": {"desc": "A Push cell that has a 1/2 chance to not be movable."},
    "cw rotator": {"desc": "Rotates neighboring cells 90 degrees clockwise."},
    "ccw rotator": {"desc": "Rotates neighboring cells 90 degrees counterclockwise."},
    "180 rotator": {"desc": "Rotates neighboring cells 180 degrees."},
    "generator": {"desc": "Attempts to copy the cell behind it and put the copy in front of it. If something is blocking it then it will attempt to push the cell blocking it before it generates again"},
    "cw generator": {"desc": "Generator whose output is bent clockwise."},
    "ccw generator": {"desc": "Generator whose output is bent counterclockwise."},
    "wall": {"desc": "Immobile, this cell cannot be moved by other cells."},
    "trash": {"desc": "Deletes cells that move into it."},
    "enemy": {"desc": "A Trash cell that also deletes itself."},
    "curve diverger": {"desc": "Bends the path of cells that go/look through it by 90 degrees."},
    "freezer": {"desc": "Stops adjacent cells from updating for the rest of the tick."},
    "thawer": {"desc": "Prevents adjacent cels from being frozen."},
    "redirector": {"desc": "Turns adjacent cells to face the direction this cell is facing."},
    "cw gear": {"desc": "Rotates neighboring cells 90 degrees clockwise around it."},
    "ccw gear": {"desc": "Rotates neighboring cells 90 degrees counterclockwise around it."},
}

subcategories = {
    "movers": ["mover"],
    "pushables": ["push", "zero directional", "one directional", "two directional", "slide", "three directional",
                  "random push"],
    "rotators": ["cw rotator", "ccw rotator", "180 rotator"],
    "generators": ["generator", "cw generator", "ccw generator"],
    "walls": ["wall"],
    "trashes": ["trash"],
    "enemies": ["enemy"],
    "divergers": ["curve diverger"],
    "redirectors": ["redirector"],
    "effect givers": ["freezer", "thawer"],
    "gears": ["cw gear", "ccw gear"],
}

categories = {
    "Base": [subcategories["pushables"], subcategories["walls"], images["push"]],
    "Movers": [subcategories["movers"], images["mover"]],
    "Recreators": [subcategories["generators"], images["generator"]],
    "Rotators": [subcategories["rotators"], subcategories["redirectors"], subcategories["gears"], images["cw rotator"]],
    "Forcers": [subcategories["gears"], images["cw gear"]],
    "Destroyers": [subcategories["trashes"], subcategories["enemies"], images["trash"]],
    "Divergers": [subcategories["divergers"], images["curve diverger"]],
    "Other": [subcategories["effect givers"], images["freezer"]],
}

lerp = 0
update_delay = 0.2
sim_running = False

camera_x, camera_y = 0, 0

current_category = None
current_subcategory = None

# =================================================
# AUDIO
# =================================================

def play_sound(sound_name):
    audio[sound_name].play()


# =================================================
# UI
# =================================================

def add_ui(element, tag=None):
    setattr(element, "tag", tag)
    UI.elements.append(element)


def select_cell(b, c):
    global selected_cell
    selected_cell["name"] = c


def select_category(b, c):
    global current_category, current_subcategory
    current_category = c if current_category != c else None
    current_subcategory = None
    update_subcategory_buttons()

def select_subcategory(b, s):
    global current_subcategory
    current_subcategory = s if current_subcategory != s else None
    update_cell_buttons()


cat_positions = {}
subcat_positions = {}

def update_category_buttons():
    global cat_positions
    UI.clear("Category Button", "Subcategory Button", "Cell Button")
    cat_positions = {}
    for i, (cat_name, cat_data) in enumerate(categories.items()):
        cat_icon = cat_data[-1]
        bx, by = i * 70 + 20, 20
        cat_positions[cat_name] = [bx, by]
        add_ui(
            ui.ImageButton(bx, by, 60, 60, cat_icon, lambda b, c=cat_name: select_category(b, c), anchor="bottom-left"),
            ["Category Button", cat_name])

def update_subcategory_buttons():
    global subcat_positions
    UI.clear("Subcategory Button", "Cell Button")
    subcat_positions = {}
    if current_category in categories:
        cat_data = categories[current_category]
        subcat_list = cat_data[:-1]
        for j, subcat in enumerate(subcat_list):
            subcat_icon = images[subcat[0]]
            subcat_name = None
            for s_name, s_val in subcategories.items():
                if s_val == subcat:
                    subcat_name = s_name
                    break
            if subcat_name:
                sbx, sby = j * 70 + 20, 90
                subcat_positions[subcat_name] = [sbx, sby]
                add_ui(ui.ImageButton(sbx, sby, 60, 60, subcat_icon, lambda b, s=subcat_name: select_subcategory(b, s),
                                      anchor="bottom-left", anim_start_pos=(0, 70)),
                       ["Subcategory Button", format_text(subcat_name)])

def update_cell_buttons():
    UI.clear("Cell Button")
    if current_subcategory and current_subcategory in subcategories:
        cell_list = subcategories[current_subcategory]
        for k, cell_name in enumerate(cell_list):
            add_ui(ui.ImageButton(k * 70 + 20, 160, 60, 60, images[cell_name],
                                  lambda b, cn=cell_name: select_cell(b, cn), anchor="bottom-left",
                                  anim_start_pos=(0, 70)), ["Cell Button", format_text(cell_name)])


def format_text(text: str):
    r_text = ""
    for word in text.split():
        if word in ["cw", "ccw"]:
            word = word.upper()
            r_text += word + " "
            continue
        r_text += word.capitalize() + " "
    return r_text.strip()


def wrap_text(text, threshold):
    wrapped_lines = []
    for line in text.splitlines():
        line_segments = textwrap.wrap(line, width=threshold)
        if not line_segments:
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(line_segments)
    return wrapped_lines


def draw_infobox():
    mouse_x, mouse_y = pygame.mouse.get_pos()
    btn_hovering = UI.hover()

    if btn_hovering is not None and btn_hovering.tag[0] == "Cell Button":
        desc = celltypes[(btn_hovering.tag[1]).lower()]["desc"]
        title_text = font.render(btn_hovering.tag[1], True, (255,) * 3)
        wrapped_desc = wrap_text(desc, 50)

        line_spacing = small_font.get_linesize()
        total_desc_height = len(wrapped_desc) * line_spacing

        max_line_width = max([small_font.size(j)[0] for j in wrapped_desc]) if wrapped_desc else 0

        w = max(title_text.get_width() + 20, max_line_width + 20, 150)
        h = max(title_text.get_height() + total_desc_height + 15, 50)

        mouse_y = min(mouse_y, screen.get_height() - h)
        mouse_x = min(mouse_x, screen.get_width() - w)

        box_rect = pygame.Rect(mouse_x, mouse_y, w, h)
        pygame.draw.rect(screen, (80,) * 3, box_rect)
        pygame.draw.rect(screen, (60,) * 3, box_rect, width=5)

        screen.blit(title_text, (mouse_x + 10, mouse_y + 5))

        start_x = mouse_x + 10
        start_y = mouse_y + title_text.get_height() + 5

        for i, line_str in enumerate(wrapped_desc):
            line_surface = small_font.render(line_str, True, (255, 255, 255))
            current_y = start_y + (i * line_spacing)
            screen.blit(line_surface, (start_x, current_y))


def draw_cate_infobox():
    mouse_x, mouse_y = pygame.mouse.get_pos()
    btn_hovering = UI.hover()

    if btn_hovering is not None and btn_hovering.tag[0] in ["Category Button", "Subcategory Button"]:
        title_text = font.render(btn_hovering.tag[1], True, (255,) * 3)

        w = max(title_text.get_width() + 20, 150)
        h = max(title_text.get_height() + 15, 50)

        mouse_y = min(mouse_y, screen.get_height() - h)
        mouse_x = min(mouse_x, screen.get_width() - w)

        box_rect = pygame.Rect(mouse_x, mouse_y, w, h)
        pygame.draw.rect(screen, (80,) * 3, box_rect)
        pygame.draw.rect(screen, (60,) * 3, box_rect, width=5)

        screen.blit(title_text, (mouse_x + 10, mouse_y + 5))


def update_ui_elements():
    update_category_buttons()
    update_subcategory_buttons()
    update_cell_buttons()


update_ui_elements()


# =================================================
# DRAWING
# =================================================

def lerpp(s, e, t):
    if not fancy_graphics: return e
    if s is None: return e
    return s + t * (e - s)


def draw_cell(x, y, direction, name, flags=None):
    screen_x = int((x * cell_size) - camera_x)
    screen_y = int((y * cell_size) - camera_y)

    if (screen_x < -cell_size or screen_x > SCREEN_WIDTH or
            screen_y < -cell_size or screen_y > SCREEN_HEIGHT):
        return

    flags = flags or {}
    ccell_size = cell_size
    if flags.get("eaten", False):
        ccell_size = round(cell_size * (1 - lerp))
    if ccell_size <= 0: return

    surf = pygame.transform.scale(images[name], (ccell_size, ccell_size))
    angle = direction * -90
    surf = pygame.transform.rotate(surf, angle)

    center_x = screen_x + (cell_size // 2)
    center_y = screen_y + (cell_size // 2)
    rect = surf.get_rect(center=(center_x, center_y))
    screen.blit(surf, rect)


def draw_ghost_cell(x, y, direction, name):
    if (not 0 <= x < grid.width) or (not 0 <= y < grid.height): return
    if cell_size <= 0: return

    center_x = int((x * cell_size) + (cell_size // 2) - camera_x)
    center_y = int((y * cell_size) + (cell_size // 2) - camera_y)

    surf = pygame.transform.scale(images[name], (cell_size, cell_size))
    surf.set_alpha(128)
    angle = direction * -90
    surf = pygame.transform.rotate(surf, angle)
    rect = surf.get_rect(center=(center_x, center_y))
    screen.blit(surf, rect)

    box_size = int(cell_size * 1.8) + int(math.sin(pygame.time.get_ticks() / 300) * (cell_size * 0.2))
    if box_size <= 0: return

    box_rect = pygame.Rect(0, 0, box_size, box_size)
    box_rect.center = (center_x, center_y)
    pygame.draw.rect(screen, (255, 255, 255, 220), box_rect, width=max(1, int(cell_size * 0.15)))


def draw_grid():
    for x, y, cell in grid:
        draw_cell(x, y, 0, "bg")

    for cell, trashpos in grid.eaten:
        if cell is None: continue
        draw_cell(lerpp(cell.oldx, trashpos[0], lerp), lerpp(cell.oldy, trashpos[1], lerp),
                  lerpp(cell.olddirection, cell.direction, lerp), cell.name, flags={"eaten": True})
    for x, y, cell in grid:
        if cell is None: continue
        if cell.olddirection == 3 and cell.direction == 0: cell.olddirection = -1
        if cell.olddirection == 0 and cell.direction == 3: cell.olddirection = 4
        draw_cell(lerpp(cell.oldx, x, lerp), lerpp(cell.oldy, y, lerp), lerpp(cell.olddirection, cell.direction, lerp),
                  cell.name)
        for effect in vars(cell.effects):
            if not getattr(cell.effects, effect): continue
            draw_cell(lerpp(cell.oldx, x, lerp), lerpp(cell.oldy, y, lerp),
                      lerpp(0, 0, lerp),
                      f"effects/{effect}")


# =================================================
# RUNTIME
# =================================================

def place_cell(x, y, direction, name):
    if 0 <= x < grid.width and 0 <= y < grid.height:
        grid[x, y] = Cell(direction, name)


def delete_cell(x, y):
    if 0 <= x < grid.width and 0 <= y < grid.height:
        grid[x, y] = None


def reset_cells():
    grid.eaten = []
    perm_effects = []
    for x, y, cell in grid:
        if cell is not None:
            cell.oldx, cell.oldy, cell.olddirection, cell.updated = x, y, cell.direction, False
            for effect in vars(cell.effects):
                if effect not in perm_effects:
                    setattr(cell.effects, effect, False)


dt = 0
while running:
    mouse_pos = pygame.mouse.get_pos()
    mx, my = int((mouse_pos[0] + camera_x) // cell_size), int((mouse_pos[1] + camera_y) // cell_size)
    lerp += dt * (1 / update_delay)
    if lerp >= 1:
        lerp = 0
        reset_cells()
        if sim_running:
            grid.update_cells()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break
        if event.type == pygame.VIDEORESIZE:
            SCREEN_WIDTH, SCREEN_HEIGHT = event.size
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                selected_cell["direction"] += 1
                selected_cell["direction"] %= 4
            if event.key == pygame.K_q:
                selected_cell["direction"] += -1
                selected_cell["direction"] %= 4
            if event.key == pygame.K_SPACE:
                sim_running = not sim_running
            if event.key == pygame.K_f:
                sim_running = False
                grid.update_cells()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5):
                old_cell_size = cell_size
                if event.button == 4:
                    cell_size = min(128, cell_size + 4)
                elif event.button == 5:
                    cell_size = max(8, cell_size - 4)

                world_m_x = mouse_pos[0] + camera_x
                world_m_y = mouse_pos[1] + camera_y
                camera_x = (world_m_x * cell_size // old_cell_size) - mouse_pos[0]
                camera_y = (world_m_y * cell_size // old_cell_size) - mouse_pos[1]
        if event.type == pygame.MOUSEBUTTONUP:
            UI.click()
    mouse_buttons = pygame.mouse.get_pressed()
    if mouse_buttons[0] and not UI.hover():
        place_cell(mx, my, selected_cell["direction"], selected_cell["name"])
    if mouse_buttons[2] and not UI.hover():
        delete_cell(mx, my)
    key_buttons = pygame.key.get_pressed()
    cam_speed = 60 * dt * 5
    if key_buttons[pygame.K_w]:
        camera_y -= cam_speed
    if key_buttons[pygame.K_s]:
        camera_y += cam_speed
    if key_buttons[pygame.K_d]:
        camera_x += cam_speed
    if key_buttons[pygame.K_a]:
        camera_x -= cam_speed
    screen.fill((20,) * 3)
    draw_grid()
    draw_ghost_cell(mx, my, selected_cell["direction"], selected_cell["name"])
    UI.draw()
    draw_infobox()
    draw_cate_infobox()
    UI.update_animation(dt)
    pygame.display.flip()
    dt = clock.tick(60) / 1000
pygame.quit()