import math
import os
import sys
import textwrap
from copy import deepcopy
import base64
import json
import zlib
from utils import compose

import pygame


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


pygame.init()
pygame.mixer.init()
monitor_info = pygame.display.Info()
SCREEN_WIDTH = monitor_info.current_w
SCREEN_HEIGHT = monitor_info.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
running = True
pygame.font.init()
font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 32)
small_font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 20)

fancy_graphics = True
menu = "Main Menu"

import ui

GameUI = ui.UI([])
MainMenuUI = ui.UI([])

from loader import images, audio
import cells

grid = cells.grid
saved = None
Cell = cells.Cell
pygame.display.set_caption("Cell Machine SMod")
pygame.display.set_icon(pygame.image.load(resource_path("icon.ico")).convert_alpha())
title_logo = pygame.image.load(resource_path("SMod_Logo.png")).convert_alpha()
title_logo = pygame.transform.scale(title_logo, (600, 600 * title_logo.get_height()/title_logo.get_width()))
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
    "cw 90 rotator": {"desc": "Rotates neighboring cells 90 degrees clockwise."},
    "ccw 90 rotator": {"desc": "Rotates neighboring cells 90 degrees counterclockwise."},
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
    "weight": {"desc": "When moved by a physical force, subtracts 1 from the force."},
    "anti weight": {"desc": "When moved by a physical force, adds 1 to the force."},
    "bias": {"desc": "Acts like a Weight cell on the front and an Anti Weight on the back; It doesnt do anything on the other sides."},
    "gold": {"desc": "Can only be pushed by orthogonal forces."},
    "lead": {"desc": "Can only be pushed by diagonal forces."},
    "ghost": {"desc": "A Wall that cannot be generated."},
    "jam": {"desc": "When a Gear tries to move this cell, it will jam the gear instead (stop it)."},
    "straight diverger": {"desc": "Like a Curve Diverger thats bent to be straight."},
    "diode diverger": {"desc": "A Straight Diverger that can only diverge on its back side."},
    "bicurve diverger": {"desc": "Two Curve Divergers 180 degrees from each other."},
    "bistraight diverger": {"desc": "Two Straight Divergers perpendicular to each other."},
    "leaper": {"desc": "A Mover that skips the cell in front of it and goes to the one after that. (Rise: 0, Run: 2)"},
    "random 90 rotator": {"desc": "Rotates neighboring cells 90 degrees either clockwise or counterclockwise."},
    "cw 45 rotator": {"desc": "Rotates neighboring cells 45 degrees clockwise."},
    "ccw 45 rotator": {"desc": "Rotates neighboring cells 45 degrees counterclockwise."},
    "random 45 rotator": {"desc": "Rotates neighboring cells 45 degrees either clockwise or counterclockwise."},
    "cw 135 rotator": {"desc": "Rotates neighboring cells 135 degrees clockwise."},
    "ccw 135 rotator": {"desc": "Rotates neighboring cells 135 degrees counterclockwise."},
    "random 135 rotator": {"desc": "Rotates neighboring cells 135 degrees either clockwise or counterclockwise."},
    "squish trash": {"desc": "A Trash that needs to be pushed against a wall to delete cells."},
    "squish enemy": {"desc": "An Enemy that needs to be pushed against a wall to delete cells."},
    "puller": {"desc": "A Mover that moves the line of cells behind it instead of in front of it; Stops if there is a cell in its way."},
    "hydra": {"desc": "A Mover that splits perpendicularly when it hits a wall, if it can."},
    "lichen": {"desc": "Splits like a Hydra when a cell attempts to push it. (VERY BUGGY)"},
    "skidhi 90": {"desc": "ITS ME!!! Rotates the cell in front of it and the cell behind it."},
    "mirror": {"desc": "Swaps the two cells it is pointing to."},
    "ungeneratable": {"desc": "When this cell is being generated it instead makes the generator create air."},
    "obtuse curve diverger": {"desc": "Bends the path of cells that go/look through it by 135 degrees."},
    "acute curve diverger": {"desc": "Bends the path of cells that go/look through it by 45 degrees."},
    "monogeneratable": {"desc": "When this cell is being generated it instead makes the generator create an Ungeneratable."},
}

subcategories = {
    "movers": ["mover", "skidhi 90", "leaper", "hydra"],
    "pushables": ["push", "zero directional", "one directional", "two directional", "slide", "three directional",
                  "random push", "lichen"],
    "weights": ["weight", "anti weight", "bias", "gold", "lead"],
    "rotators": ["cw 90 rotator", "cw 45 rotator", "cw 135 rotator", "ccw 90 rotator", "ccw 45 rotator", "ccw 135 rotator", "random 90 rotator", "random 45 rotator", "random 135 rotator", "180 rotator"],
    "generators": ["generator", "cw generator", "ccw generator"],
    "generatables": ["ungeneratable", "monogeneratable"],
    "walls": ["wall", "ghost"],
    "trashes": ["trash", "squish trash"],
    "enemies": ["enemy", "squish enemy"],
    "divergers": ["curve diverger", "acute curve diverger", "obtuse curve diverger", "bicurve diverger", "straight diverger", "bistraight diverger", "diode diverger"],
    "redirectors": ["redirector"],
    "effect givers": ["freezer", "thawer"],
    "gears": ["cw gear", "ccw gear", "jam"],
    "mirrors": ["mirror"],
}

categories = {
    "Base": [subcategories["pushables"], subcategories["weights"], subcategories["walls"], images["push"]],
    "Movers": [subcategories["movers"], images["mover"]],
    "Recreators": [subcategories["generators"], subcategories["generatables"], images["generator"]],
    "Rotators": [subcategories["rotators"], subcategories["redirectors"], subcategories["gears"], images["cw 90 rotator"]],
    "Forcers": [subcategories["gears"], subcategories["mirrors"], images["mirror"]],
    "Destroyers": [subcategories["trashes"], subcategories["enemies"], images["trash"]],
    "Divergers": [subcategories["divergers"], images["curve diverger"]],
    "Other": [subcategories["effect givers"], images["freezer"]],
}

lerp = 0
update_delay = 0.2
sim_running, stepping = (False,)*2

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

def add_ui(element, tag=None, menu="Game"):
    setattr(element, "tag", tag)
    if menu == "Game":
        GameUI.elements.append(element)
    if menu == "Main Menu":
        MainMenuUI.elements.append(element)


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
    GameUI.clear("Category Button", "Subcategory Button", "Cell Button")
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
    GameUI.clear("Subcategory Button", "Cell Button")
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
    GameUI.clear("Cell Button")
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
    btn_hovering = GameUI.hover()

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
    btn_hovering = GameUI.hover()

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

def draw_main_infobox():
    mouse_x, mouse_y = pygame.mouse.get_pos()
    btn_hovering = MainMenuUI.hover()

    if btn_hovering is not None and btn_hovering.tag[0] in ["Main Menu"]:
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

def toggle_sim(b):
    global sim_running
    start_surf = images["mover"]
    pause_surf = pygame.transform.rotate(images["slide"].copy(), 90)
    sim_running = not sim_running
    if sim_running:
        b.image = pause_surf.copy()
    else:
        b.image = start_surf.copy()

def step_sim(b):
    global stepping, sim_running, sim_button, lerp
    if stepping: return
    if sim_running:
        toggle_sim(sim_button)
        return
    stepping = True
    lerp = 0
    if sim_running:
        toggle_sim(sim_button)
    tick()

def save_state(b):
    global saved, load_state_button
    saved = deepcopy(grid.grid)
    b.enabled = False
    load_state_button.enabled = False

def load_state(b):
    global saved, grid, save_state_button, sim_running, sim_button, lerp
    if sim_running:
        toggle_sim(sim_button)
    lerp = 1
    grid.grid = deepcopy(saved)
    b.enabled = False
    save_state_button.enabled = False

sim_button = ui.ImageButton(20, 20, 70, 70, images["mover"], toggle_sim)
add_ui(sim_button, ["Simulation Button"])
step_button = ui.ImageButton(95, 20, 70, 70, images["nudger"], step_sim)
add_ui(step_button, ["Simulation Button"])
save_state_button = ui.ImageButton(20, 95, 70, 70, images["generator"], save_state, enabled=False)
add_ui(save_state_button, ["Simulation Button"])
load_state_button = ui.ImageButton(95, 95, 70, 70, images["180 rotator"], compose(lambda x: play_sound("click"), load_state), enabled=False)
add_ui(load_state_button, ["Simulation Button"])

update_ui_elements()

def go_to_game(b):
    global menu, grid
    menu = "Game"
    for x in range(grid.width):
        for y in range(grid.height):
            if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                grid[x, y] = Cell(0, "ghost")

def quit_app(b):
    global running
    running = False

def go_to_credits(b):
    pass

play_button = ui.ImageButton(500, 240, 150, 150, images["mover"], compose(lambda x: play_sound("click"), go_to_game), anchor="left-bottom")
add_ui(play_button, ["Main Menu", "Play"], menu="Main Menu")
quit_button = ui.ImageButton(500, 40, 150, 150, images["trash"], quit_app, anchor="right-bottom")
add_ui(quit_button, ["Main Menu", "Quit"], menu="Main Menu")
credits_button = ui.ImageButton(500, 40, 150, 150, images["push"], compose(lambda x: play_sound("click"), go_to_credits), anchor="left-bottom")
add_ui(credits_button, ["Main Menu", "Credits"], menu="Main Menu")

# =================================================
# DRAWING
# =================================================

def lerpp(s, e, t):
    if not fancy_graphics: return e
    if s is None: return e
    return s + t * (e - s)


def lerp_angle(s, e, t):
    if not fancy_graphics: return e
    if s is None: return e
    diff = e - s
    diff = (diff + 2) % 4 - 2
    return s + diff * t


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
                  lerp_angle(cell.olddirection, cell._direction, lerp), cell.name, flags={"eaten": True})
    for x, y, cell in grid:
        if cell is None: continue
        for eaten in cell.eaten:
            draw_cell(lerpp(eaten.oldx, x, lerp), lerpp(eaten.oldy, y, lerp),
                      lerp_angle(eaten.olddirection, eaten._direction, lerp), eaten.name, flags={"eaten": True})
        draw_cell(lerpp(cell.oldx, x, lerp), lerpp(cell.oldy, y, lerp), lerp_angle(cell.olddirection, cell._direction, lerp),
                  cell.name)
        for effect in vars(cell.effects):
            if not getattr(cell.effects, effect): continue
            draw_cell(lerpp(cell.oldx, x, lerp), lerpp(cell.oldy, y, lerp),
                      0,
                      f"effects/{effect}")


# =================================================
# RUNTIME
# =================================================

def save_code():
    code = []
    code_type = "S1"
    cell_type_list = list(celltypes.keys())

    for x, y, cell in grid:
        if cell is None:
            continue

        pos = x + (y * grid.width)
        cell_id = cell_type_list.index(cell.name)

        state = vars(cell).copy()
        state["name"] = cell_id
        state["effects"] = vars(cell.effects)

        code.append([pos, state])

    json_str = json.dumps(code, separators=(',', ':'))
    compressed = zlib.compress(json_str.encode('utf-8'))
    b64_str = base64.b64encode(compressed).decode('utf-8')

    return f"{code_type};{b64_str}"


def load_code(save_string):
    parts = save_string.split(";")
    b64_str = parts[1]
    cell_type_list = list(celltypes.keys())

    compressed = base64.b64decode(b64_str.encode('utf-8'))
    json_str = zlib.decompress(compressed).decode('utf-8')
    code_data = json.loads(json_str)

    for pos, state in code_data:
        x = pos % grid.width
        y = pos // grid.width

        state["name"] = cell_type_list[state["name"]]
        effects_data = state.pop("effects")

        loaded_cell = Cell(direction=state["direction"], name=state["name"])

        for key, value in state.items():
            setattr(loaded_cell, key, value)

        loaded_cell.effects = cells.EffectList(effects_data)
        grid[x, y] = loaded_cell


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
            cell.oldx, cell.oldy = x, y
            cell.olddirection = cell._direction % 4
            cell._direction = cell._direction % 4
            cell.updated = False
            for effect in vars(cell.effects):
                if effect not in perm_effects:
                    setattr(cell.effects, effect, False)

def tick():
    global saved
    if saved is None:
        saved = deepcopy(grid.grid)
    grid.update_cells()
    save_state_button.enabled = True
    load_state_button.enabled = True

dt = 0
while running:
    mouse_pos = pygame.mouse.get_pos()
    mx, my = int((mouse_pos[0] + camera_x) // cell_size), int((mouse_pos[1] + camera_y) // cell_size)
    lerp += dt * (1 / update_delay)
    if lerp >= 1:
        lerp = 0
        stepping = False
        reset_cells()
        if sim_running:
            tick()
    if menu == "Main Menu":
        lerp = 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break
        if event.type == pygame.VIDEORESIZE:
            SCREEN_WIDTH, SCREEN_HEIGHT = event.size
        if event.type == pygame.KEYDOWN:
            if menu == "Game":
                if event.key == pygame.K_e:
                    selected_cell["direction"] += 1
                    selected_cell["direction"] %= 4
                if event.key == pygame.K_q:
                    selected_cell["direction"] += -1
                    selected_cell["direction"] %= 4
                if event.key == pygame.K_r:
                    selected_cell["direction"] -= 0.5
                    selected_cell["direction"] %= 4
                if event.key == pygame.K_t:
                    selected_cell["direction"] += 0.5
                    selected_cell["direction"] %= 4
                if event.key == pygame.K_SPACE:
                    toggle_sim(sim_button)
                if event.key == pygame.K_f:
                    step_sim(step_button)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5):
                if menu == "Game":
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
            if event.button not in (4, 5):
                if menu == "Game":
                    GameUI.click()
                elif menu == "Main Menu":
                    MainMenuUI.click()
    mouse_buttons = pygame.mouse.get_pressed()
    if menu == "Game":
        if mouse_buttons[0] and not GameUI.hover():
            place_cell(mx, my, selected_cell["direction"], selected_cell["name"])
            for x in range(grid.width):
                for y in range(grid.height):
                    if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                        grid[x, y] = Cell(0, "ghost")
        if mouse_buttons[2] and not GameUI.hover():
            delete_cell(mx, my)
            for x in range(grid.width):
                for y in range(grid.height):
                    if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                        grid[x, y] = Cell(0, "ghost")
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
    screen.fill((0,) * 3)
    if menu == "Game":
        screen.fill((20,) * 3)
        draw_grid()
        draw_ghost_cell(mx, my, selected_cell["direction"], selected_cell["name"])
        GameUI.draw()
        draw_infobox()
        draw_cate_infobox()
        GameUI.update_animation(dt)
    if menu == "Main Menu":
        screen.fill((30,) * 3)
        MainMenuUI.draw()
        screen.blit(title_logo, ((SCREEN_WIDTH-title_logo.get_width())//2+20, 40+math.sin(pygame.time.get_ticks()/500)*10))
        draw_main_infobox()
    pygame.display.flip()
    dt = clock.tick(60) / 1000
pygame.quit()