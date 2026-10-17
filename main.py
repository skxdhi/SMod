import math
import os
import sys
import textwrap
from copy import deepcopy
import base64
import json
import zlib

import utils
from utils import compose, lerp, lerp_angle, polar_lerp

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
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
running = True
pygame.font.init()
font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 32)
small_font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 20)
very_big_font = pygame.font.Font(resource_path("Jersey10-Regular.ttf"), 300)
fancy_graphics = True
menu = "Main Menu"

import ui

GameUI = ui.UI([])
MainMenuUI = ui.UI([])
AdjMenuUI = ui.UI([])

adj_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
adj_overlay.fill((80,) * 4)

from loader import images, audio
import cells

player_input = cells.player_input
grid = cells.grid
saved = None
Cell = cells.Cell
pygame.display.set_caption("Cell Machine SMod")
pygame.display.set_icon(pygame.image.load(resource_path("icon.ico")).convert_alpha())
title_logo = pygame.image.load(resource_path("SMod_Logo.png")).convert_alpha()
title_logo = pygame.transform.scale(title_logo, (600, 600 * title_logo.get_height() / title_logo.get_width()))
clock = pygame.time.Clock()

cell_size = 32

selected_cell = {
    "name": "mover",
    "direction": 0,
}
place_type = "place"

adj_menu_name = None
selected_adj_index = 0
adj_text_input = None

celltypes = {
    "mover": {"desc": "Moves one space per tick in the direction it is pointing, pushing the cells in its way."},
    "push": {"desc": "Does absolutely nothing, but cells can still interact with it."},
    "one directional": {"desc": "Can ony be pushed on the indicated side."},
    "two directional": {"desc": "Can ony be pushed on the indicated sides."},
    "slide": {"desc": "Can only be pushed on the indicated sides."},
    "three directional": {"desc": "Can ony be pushed on the indicated sides."},
    "zero directional": {"desc": "Can ony be pushed on the indicated sides, except there are no indicated sides."},
    "random push": {"desc": "A Push cell that has a 1/2 chance to not be movable."},
    "cw 90 rotator": {"desc": "Rotates neighboring cells 90 degrees clockwise."},
    "ccw 90 rotator": {"desc": "Rotates neighboring cells 90 degrees counterclockwise."},
    "180 rotator": {"desc": "Rotates neighboring cells 180 degrees."},
    "generator": {
        "desc": "Attempts to copy the cell behind it and put the copy in front of it. If something is blocking it then it will attempt to push the cell blocking it before it generates again"},
    "cw generator": {"desc": "Generator whose output is bent clockwise."},
    "ccw generator": {"desc": "Generator whose output is bent counterclockwise."},
    "wall": {"desc": "Immobile, this cell cannot be moved by other cells."},
    "trash": {"desc": "Deletes cells that move into it."},
    "enemy": {"desc": "A Trash cell that also deletes itself."},
    "curve diverger": {"desc": "Bends the path of cells that go/look through it by 90 degrees."},
    "freezer": {"desc": "Stops adjacent cells from updating for the rest of the tick."},
    "thawer": {"desc": "Prevents adjacent cells from being frozen."},
    "redirector": {"desc": "Turns adjacent cells to face the direction this cell is facing."},
    "cw gear": {"desc": "Rotates neighboring cells 90 degrees clockwise around it."},
    "ccw gear": {"desc": "Rotates neighboring cells 90 degrees counterclockwise around it."},
    "weight": {"desc": "When moved by a physical force, subtracts 1 from the force."},
    "anti weight": {"desc": "When moved by a physical force, adds 1 to the force."},
    "bias": {
        "desc": "Acts like a Weight cell on the front and an Anti Weight on the back; It doesnt do anything on the other sides."},
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
    "hydra": {"desc": "A Mover that splits perpendicularly when it hits a wall, if it can."},
    "lichen": {"desc": "Splits like a Hydra when a cell attempts to push it. (VERY BUGGY)"},
    "skidhi 90": {"desc": "ITS ME!!! Rotates the cell in front of it and the cell behind it."},
    "mirror": {"desc": "Swaps the two cells it is pointing to."},
    "ungeneratable": {"desc": "When this cell is being generated it instead makes the generator create air."},
    "obtuse curve diverger": {"desc": "Bends the path of cells that go/look through it by 135 degrees."},
    "acute curve diverger": {"desc": "Bends the path of cells that go/look through it by 45 degrees."},
    "monogeneratable": {
        "desc": "When this cell is being generated it instead makes the generator create an Ungeneratable."},
    "gyro": {"desc": "Acts like a Gear depending on how much its rotated by."},
    "arrow": {"desc": "A Push that cannot be rotated."},
    "helix": {"desc": "An Arrow that moves forward when its rotated."},
    "storage": {
        "desc": "Stores the cell that moves into it, if it already has a cell it will push it out on the opposite side."},
    "repulsor": {"desc": "Pushes neighboring cells away from it."},
    "slow mover": {"desc": "A Mover that moves every other tick."},
    "adj test": {"desc": "test"},
    "jump trash": {"desc": "A Trash that moves away from cells it eats."},
    "self": {"desc": "When a storage like cell hold this cell, it makes it hold a copy of itself instead."},
    "texter": {"desc": "Change the cells Text parameter to display text."},
    "coin": {
        "desc": "When cells collect it, they get 1 coin added to their coin count. Yes, a form of currency in Cell Machine."},
    "void": {"desc": "When a storage like cell hold this cell, it makes it hold air instead."},
    "winter": {"desc": "Freezes the entire grid."},
    "summer": {"desc": "Thaws the entire grid."},
    "puller": {
        "desc": "A Mover that moves the row behind it forwards instead of the row in front of it; Stops if there is a cell in the way."},
    "player": {"desc": "Moves depending on which arrow key you press."},
    "disabler": {"desc": "Makes neighboring cells act like pushables."},
    "enabler": {"desc": "Prevents adjacent cells from being disabled."},
    "ana rotator": {"desc": "When cells are rotated by this cell twice they get rotated 180 degrees clockwise."},
    "kata rotator": {
        "desc": "When cells are rotated by this cell twice they get rotated 180 degrees counterclockwise."},
    "half ana rotator": {
        "desc": "Ana Rotator that rotates half the amount, it needs to rotate a cell 4 times to rotate it 180 degrees by itself."},
    "half kata rotator": {
        "desc": "Kata Rotator that rotates half the amount, it needs to rotate a cell 4 times to rotate it 180 degrees by itself."},
    "impulsor": {"desc": "Pulls neighboring cells towards it."},
    "player mover": {"desc": "A Mover whose direction can be changed using arrow keys."},
    "intaker": {"desc": "Pulls cells in front of it towards it in which it eats them."},
    "anti player": {"desc": "A Player that moves in the opposite direction."},
    "pull player": {"desc": "A Player that uses pull force."},
    "single cell generator": {"desc": "A Generator that can only generate once."},
    "super generator": {"desc": "A Generator that generates the entire row behind it."},
    "cw super generator": {"desc": "Super Generator whose output is bent clockwise."},
    "ccw super generator": {"desc": "Super Generator whose output is bent counterclockwise."},
    "cw 22.5 rotator": {"desc": "When cells are rotated by this cell twice they get rotated 45 degrees clockwise."},
    "ccw 22.5 rotator": {
        "desc": "When cells are rotated by this cell twice they get rotated 45 degrees counterclockwise."},
    "bulk trash": {"desc": "A Trash that stalls the row of cells that move into it."},
    "bulk enemy": {"desc": "An Enemy combined with a Bulk Trash."},
    "light": {"desc": "Lights up a dark area, removes overlapping darkness if the strength value is greater than it."},
    "dark": {"desc": "Darkens a certain area."},
    "night": {"desc": "Like Dark, but it covers the entire grid."},
    "omega trash": {"desc": "Trash but deletes the runtime of the game."},
    "attack trash": {"desc": "A Trash that moves towards cells it eats."},
    "advancer": {"desc": "Puller + Mover."},
    "crusher": {"desc": "A Mover that destroys the cell in front of it if it cannot move; Also acts like a wall on the front side."},
    "purple mover": {"desc": "A Mover that dies when it cannot move."},
    "electrocutor": {"desc": "Allows adjacent cells to update multiple times in one tick."},
    "copper": {"desc": "Prevents adjacent cells from being electrocuted."},
    "bird": {"desc": "Moves up, forward, down, forward. If its not facing horizontally it acts like a Mover. If it cannot move forward at any point it rotates clockwise."},
    "bee": {"desc": "Moves up and forward, then down and forward. If its not facing horizontally it acts like a Mover."},
    "bread": {"desc": "An Enemy that takes an adjustable amount of force to be destroyed."},
    "inertia": {"desc": "When moved, stores momentum until it hits a wall."},
    "adjustable weight": {"desc": "A Weight with an adjustable mass."},
    "random 22.5 rotator": {"desc": "Rotates neighboring cells 22.5 degrees either clockwise or counterclockwise."},
    "adjustable rotator": {"desc": "A Rotator that rotates by an adjustable amount (1 is 90 degrees clockwise)."},
    "nudger": {"desc": "A Mover that cannot move cells in front of it."},
    "slow puller": {"desc": "A Puller that moves every other tick."},
    "leaper puller": {"desc": "A Puller combined with a Leaper."},
    "meta": {"desc": "When a storage like cell hold this cell, it makes it hold a Meta with a decremented index instead. If the index reaches 0 it will have the cell inside of the Meta."},
    "slow cw gear": {"desc": "Rotates neighboring cells 45 degrees clockwise around it."},
    "slow ccw gear": {"desc": "Rotates neighboring cells 45 degrees counterclockwise around it."},
    "180 gear": {"desc": "Rotates neighboring cells 180 degrees around it."},
    "fast cw gear": {"desc": "Rotates neighboring cells 135 degrees clockwise around it."},
    "fast ccw gear": {"desc": "Rotates neighboring cells 135 degrees counterclockwise around it."},
    "jelly": {"desc": "When a Gear tries to move this cell, the Gear will skip it instead."},
    "anti coin": {
        "desc": "When cells collect it, they lose 1 coin from their coin count. Cells can have negative coins (dont ask)."},
    "nano weight": {"desc": "Acts like a wall if its the first cell in the row to be pushed."},
    "anti nano weight": {"desc": "Acts like a wall if its not the first cell in the row to be pushed."},
    #"coin diverger": {"desc": "A Bistraight Diverger that takes away an adjustable amount of coins from cells, doesnt let cells pass through that dont have sufficient currency."},
    "chocolate coin": {
        "desc": "When cells collect it, they.... uhhhmm.... you know what lemme try one. *chomp*. SOGOODANDYUMMYANDDELICIOUSAN- *dies*. Sorry I had to take over for skidhi, it doesnt give you anything."},
}

subcategories = {
    "movers": ["mover", "slow mover", "helix", "skidhi 90", "leaper", "hydra", "player mover", "purple mover", "bird", "bee", "advancer"],
    "players": ["player", "player mover", "anti player", "pull player"],
    "nudgers": ["nudger"],
    "other movers": ["inertia"],
    "crushers": ["crusher"],
    "pullers": ["puller", "slow puller", "leaper puller", "advancer"],
    "pushables": ["push", "zero directional", "one directional", "two directional", "slide", "three directional",
                  "random push", "arrow", "helix", "lichen"],
    "coins": ["coin", "anti coin", "chocolate coin"],
    "weights": ["weight", "anti weight", "bias", "gold", "lead", "nano weight", "anti nano weight", "bread", "adjustable weight"],
    "rotators": ["cw 90 rotator", "cw 45 rotator", "cw 135 rotator", "ccw 90 rotator", "ccw 45 rotator",
                 "ccw 135 rotator", "random 90 rotator", "random 45 rotator", "random 135 rotator", "180 rotator"],
    "slow rotators": ["cw 22.5 rotator", "ccw 22.5 rotator", "random 22.5 rotator", "ana rotator", "half ana rotator", "kata rotator",
                      "half kata rotator", "adjustable rotator"],
    "generators": ["generator", "cw generator", "ccw generator", "single cell generator"],
    "super generators": ["super generator", "cw super generator", "ccw super generator"],
    "generatables": ["ungeneratable", "monogeneratable"],
    "walls": ["wall", "ghost"],
    "trashes": ["trash", "jump trash", "attack trash", "squish trash", "bulk trash", "omega trash"],
    "enemies": ["enemy", "squish enemy", "bulk enemy", "bread"],
    "divergers": ["curve diverger", "acute curve diverger", "obtuse curve diverger", "bicurve diverger",
                  "straight diverger", "bistraight diverger", "diode diverger"],
    "redirectors": ["redirector"],
    "freezers": ["freezer", "winter", "thawer", "summer"],
    "disablers": ["disabler", "enabler"],
    "electrocutors": ["electrocutor", "copper"],
    "gears": ["cw gear", "slow cw gear", "fast cw gear", "ccw gear", "slow ccw gear", "fast ccw gear", "180 gear", "gyro", "jam", "jelly"],
    "mirrors": ["mirror"],
    "storing": ["storage", "self", "meta", "void"],
    "repulsors": ["repulsor"],
    "impulsors": ["impulsor"],
    "other": ["texter"],
    "brightness": ["light", "dark", "night"]
}

categories = {
    "Base": [subcategories["pushables"], subcategories["weights"], subcategories["walls"], images["push"]],
    "Movers": [subcategories["movers"], subcategories["pullers"], subcategories["crushers"], subcategories["nudgers"], subcategories["players"], subcategories["other movers"], images["mover"]],
    "Recreation": [subcategories["generators"], subcategories["super generators"], subcategories["generatables"],
                   images["generator"]],
    "Rotators": [subcategories["rotators"], subcategories["slow rotators"], subcategories["redirectors"],
                 subcategories["gears"],
                 images["cw 90 rotator"]],
    "Forcers": [subcategories["repulsors"], subcategories["impulsors"], subcategories["gears"],
                subcategories["mirrors"], images["repulsor"]],
    "Destroyers": [subcategories["trashes"], subcategories["enemies"], images["trash"]],
    "Divergers": [subcategories["divergers"], images["curve diverger"]],
    "Effect Givers": [subcategories["freezers"], subcategories["disablers"], subcategories["electrocutors"], images["freezer"]],
    "Other": [subcategories["storing"], subcategories["brightness"], subcategories["coins"], subcategories["other"],
              images["void"]],
}


def make_adj_element(type, current_val, name=None):
    return {"name": name or type, "type": type, "current_val": current_val}


adjustables = {
    "adj test": [
        make_adj_element("Float", 0),
        make_adj_element("Integer", 0),
        make_adj_element("Direction", 0),
        make_adj_element("Rotation", "CW"),
        make_adj_element("String", ""),
        make_adj_element("Boolean", True),
        make_adj_element("Color", (255, 255, 255)),
    ],
    "texter": [
        make_adj_element("String", "", "Text"),
        make_adj_element("Color", (255, 255, 255), "Color"),
    ],
    "light": [
        make_adj_element("Integer", 3, "Width"),
        make_adj_element("Integer", 3, "Height"),
        make_adj_element("Float", 10, "Strength"),
    ],
    "dark": [
        make_adj_element("Integer", 3, "Width"),
        make_adj_element("Integer", 3, "Height"),
        make_adj_element("Float", 10, "Strength"),
    ],
    "night": [
        make_adj_element("Float", 10, "Strength"),
    ],
    "electrocutor": [
        make_adj_element("Integer", 2, "Numerator"),
        make_adj_element("Natural", 1, "Denominator"),
    ],
    "random push": [
        make_adj_element("Natural", 1, "Numerator"),
        make_adj_element("Natural", 2, "Denominator"),
    ],
    "bread": [
        make_adj_element("Integer", 3, "Numerator"),
        make_adj_element("Natural", 1, "Denominator"),
    ],
    "adjustable weight": [
        make_adj_element("Integer", 3, "Numerator"),
        make_adj_element("Natural", 1, "Denominator"),
    ],
    "adjustable rotator": [
        make_adj_element("Integer", 3, "Numerator"),
        make_adj_element("Natural", 2, "Denominator"),
    ],
    "meta": [
        make_adj_element("Natural", 3, "Index"),
    ],
    "coin diverger": [
        make_adj_element("Integer", 1, "Cost"),
    ],
}


def draw_rect_alpha(surface, color, rect):
    shape_surf = pygame.Surface(pygame.Rect(rect).size, pygame.SRCALPHA)
    pygame.draw.rect(shape_surf, color, shape_surf.get_rect())
    surface.blit(shape_surf, rect)


lerp_time = 0
update_delay = 0.2
sim_running, stepping = (False,) * 2

camera_x, camera_y = 0, 0

current_category = None
current_subcategory = None


def play_sound(sound_name):
    audio[sound_name].play()


def add_ui(element, tag=None, menu="Game"):
    setattr(element, "tag", tag)
    if menu == "Game":
        GameUI.elements.append(element)
    if menu == "Main Menu":
        MainMenuUI.elements.append(element)
    if menu == "Adj":
        AdjMenuUI.elements.append(element)


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


def close_adj_menu(b):
    global adj_menu_name, selected_adj_index, adj_text_input
    if adj_text_input and adj_text_input.active:
        adj_text_input.deactivate(confirm=False)
    adj_menu_name = None
    selected_adj_index = 0
    adj_text_input = None
    rebuild_adj_menu()


adj_close = ui.ImageButton(100, 100, 50, 50, images["close"], close_adj_menu, anchor="right")
add_ui(adj_close, menu="Adj")


def on_adj_value_confirm(text):
    global selected_adj_index
    if adj_menu_name is None:
        return
    elems = adjustables.get(adj_menu_name)
    if not elems or selected_adj_index >= len(elems):
        return
    elem = elems[selected_adj_index]
    t = elem["type"]
    try:
        if t == "Integer":
            elem["current_val"] = int(float(text)) if text.strip() not in ("", ".") else 0
        if t == "Natural":
            elem["current_val"] = int(float(text)) if text.strip() not in ("", ".") else 0
            elem["current_val"] = max(elem["current_val"], 1)
        elif t == "Float":
            elem["current_val"] = float(text) if text.strip() not in ("", "-", ".") else 0.0
        elif t == "String":
            elem["current_val"] = text
    except ValueError:
        pass
    if adj_text_input is not None:
        if t in ("Integer", "Natural"):
            adj_text_input.text = str(int(elem["current_val"]))
        elif t == "Float":
            adj_text_input.text = str(float(elem["current_val"]))


def select_adj_option(b, idx):
    global selected_adj_index, adj_text_input
    if adj_text_input and adj_text_input.active:
        adj_text_input.deactivate(confirm=True)
    selected_adj_index = idx
    rebuild_adj_menu()


def rebuild_adj_menu():
    global selected_adj_index, adj_text_input
    AdjMenuUI.clear()
    add_ui(adj_close, menu="Adj")
    adj_text_input = None
    if adj_menu_name is None:
        return

    elems = adjustables.get(adj_menu_name, [])
    if not elems:
        return

    if selected_adj_index < 0 or selected_adj_index >= len(elems):
        selected_adj_index = 0

    panel_x = 80
    panel_y = 80
    divider_x = 360
    row_h = 55
    start_y = panel_y + 70
    left_w = divider_x - panel_x - 40

    for i, elem in enumerate(elems):
        row_y = start_y + i * row_h
        is_selected = (i == selected_adj_index)
        bg = (110, 110, 110) if is_selected else (60, 60, 60)
        hover_bg = (120, 120, 120) if is_selected else (80, 80, 80)
        border = (70, 70, 70) if is_selected else (50, 50, 50)
        opt_btn = ui.TextButton(
            panel_x + 15, row_y - 5, left_w, row_h - 8,
            elem["name"],
            font if is_selected else small_font,
            lambda b, idx=i: select_adj_option(b, idx),
            anchor="top-left",
            bg_color=bg,
            hover_bg_color=hover_bg,
            text_color=(255, 255, 255),
            border_color=border,
        )
        add_ui(opt_btn, ["Adj Option", f"opt_{i}"], menu="Adj")

    sel = elems[selected_adj_index]
    t = sel["type"]
    ctrl_y = start_y + 20
    input_w, input_h = 220, 50
    input_x = divider_x + 20
    if t in ("Integer", "Float", "String", "Natural"):
        initial = str(int(sel["current_val"])) if t == "Integer" else (
            str(sel["current_val"]) if t == "String" else (
                str(float(sel["current_val"])) if t == "Float" else str(max(int(sel["current_val"]), 1)))
        )
        adj_text_input = ui.TextInput(
            input_x, ctrl_y, input_w, input_h, font,
            initial=initial,
            on_confirm=on_adj_value_confirm,
            numeric=(t != "String"),
            allow_float=(t == "Float"),
            bg_color=(40, 40, 40),
            active_bg=(50, 50, 70),
            border_color=(100, 100, 100),
            active_border=(120, 160, 220),
        )
        add_ui(adj_text_input, ["Adj Control", "text_input"], menu="Adj")

    if t == "Direction":
        def direction_button_click(b):
            sel["current_val"] = (sel["current_val"] + 0.5) % 4
            b.angle = sel["current_val"] * -90

        dir_button = ui.ImageButton(
            input_x, ctrl_y, 50, 50,
            images["redirector"],
            direction_button_click,
        )

        dir_button.angle = sel["current_val"] * -90

        add_ui(dir_button, ["Adj Control", "button"], menu="Adj")

    if t == "Rotation":
        def get_rotation_image(value):
            if value == "CW":
                return images["cw 90 rotator"]
            if value == "CCW":
                return images["ccw 90 rotator"]
            if value == "180":
                return images["180 rotator"]
            return images["random 90 rotator"]

        def rotation_button_click(b):
            options = ["CW", "CCW", "180", "Random"]
            sel["current_val"] = options[
                (options.index(sel["current_val"]) + 1) % len(options)
                ]
            b.image = pygame.transform.scale(
                get_rotation_image(sel["current_val"]),
                (50, 50)
            )

        rot_button = ui.ImageButton(
            input_x, ctrl_y, 50, 50,
            get_rotation_image(sel["current_val"]),
            rotation_button_click,
        )

        add_ui(rot_button, ["Adj Control", "button"], menu="Adj")

    if t == "Boolean":
        def get_boolean_image(value):
            if value:
                return images["not close"]
            return images["close"]

        def boolean_button_click(b):
            sel["current_val"] = not sel["current_val"]
            b.image = pygame.transform.scale(
                get_boolean_image(sel["current_val"]),
                (50, 50)
            )

        bool_button = ui.ImageButton(
            input_x, ctrl_y, 50, 50,
            get_boolean_image(sel["current_val"]),
            boolean_button_click,
        )

        add_ui(bool_button, ["Adj Control", "button"], menu="Adj")

    if t == "Color":
        slider_w, slider_h, gap = 260, 36, 12
        channels = (("R", (200, 60, 60)), ("G", (60, 180, 60)), ("B", (70, 110, 220)))

        def make_channel_setter(index):
            def setter(v):
                c = list(sel["current_val"])
                c[index] = int(v)
                sel["current_val"] = tuple(c)
            return setter

        for i, (label, fill) in enumerate(channels):
            add_ui(ui.Slider(
                input_x, ctrl_y + i * (slider_h + gap), slider_w, slider_h,
                min_val=0, max_val=255, value=int(sel["current_val"][i]),
                on_change=make_channel_setter(i),
                font=font, label=label, label_width=30, value_width=60,
                fill_color=fill,
            ), ["Adj Control", f"color_slider_{label}"], menu="Adj")

        swatch_size = slider_h * 3 + gap * 2
        add_ui(ui.ColorSwatch(
            input_x + slider_w + 20, ctrl_y, swatch_size, swatch_size,
            lambda: sel["current_val"],
        ), ["Adj Control", "color_swatch"], menu="Adj")


def draw_adjustable_menu():
    global adj_menu_name, AdjMenuUI, selected_adj_index
    if adj_menu_name is None:
        AdjMenuUI.enabled = False
        return
    AdjMenuUI.enabled = True
    x = 80
    y = 80
    w = SCREEN_WIDTH - x * 2
    h = SCREEN_HEIGHT - y * 2
    screen.blit(adj_overlay, (0, 0))
    pygame.draw.rect(screen, (80,) * 3, pygame.Rect(x, y, w, h))
    pygame.draw.rect(screen, (70,) * 3, pygame.Rect(x, y, w, h), width=10)
    pygame.draw.rect(screen, (150,) * 3, pygame.Rect(360, 100, 5, h - 40))

    title = font.render(format_text(adj_menu_name), True, (255, 255, 255))
    screen.blit(title, (x + 20, y + 15))

    elems = adjustables.get(adj_menu_name, [])
    if not elems:
        return

    if 0 <= selected_adj_index < len(elems):
        sel = elems[selected_adj_index]
        t = sel["type"]

        type_surf = small_font.render(f"Type: {t}", True, (180, 180, 180))
        screen.blit(type_surf, (380, 120))


rebuild_adj_menu()


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
        b.image = pygame.transform.scale(pause_surf.copy(), (70, 70))
    else:
        b.image = pygame.transform.scale(start_surf.copy(), (70, 70))


def step_sim(b):
    global stepping, sim_running, sim_button, lerp_time
    if stepping: return
    if sim_running:
        toggle_sim(sim_button)
        return
    stepping = True
    lerp_time = 0
    if sim_running:
        toggle_sim(sim_button)
    tick()


def save_state(b):
    global saved, load_state_button
    saved = deepcopy(grid.grid)
    b.enabled = False
    load_state_button.enabled = False


def load_state(b):
    global saved, grid, save_state_button, sim_running, sim_button, lerp_time
    if sim_running:
        toggle_sim(sim_button)
    lerp_time = 1
    grid.grid = deepcopy(saved)
    b.enabled = False
    save_state_button.enabled = False


def to_adj_menu(b):
    global adj_menu_name
    adj_menu_name = selected_cell["name"].lower()
    rebuild_adj_menu()


def quit_game(b):
    global menu
    menu = "Main Menu"


sim_button = ui.ImageButton(20, 20, 70, 70, images["mover"], toggle_sim)
add_ui(sim_button, ["Simulation Button"])
step_button = ui.ImageButton(95, 20, 70, 70, images["nudger"], step_sim)
add_ui(step_button, ["Simulation Button"])
quit_button = ui.ImageButton(20, 20, 70, 70, images["close"], compose(lambda x: play_sound("click"), quit_game),
                             anchor="right")
add_ui(quit_button, ["Simulation Button"])
save_state_button = ui.ImageButton(20, 95, 70, 70, images["generator"], save_state, enabled=False)
add_ui(save_state_button, ["Simulation Button"])
load_state_button = ui.ImageButton(95, 95, 70, 70, images["180 rotator"],
                                   compose(lambda x: play_sound("click"), load_state), enabled=False)
add_ui(load_state_button, ["Simulation Button"])
adj_button = ui.ImageButton(170, 20, 70, 70, images["edit"], compose(lambda x: play_sound("click"), to_adj_menu),
                            enabled=False)
add_ui(adj_button, ["Simulation Button"])

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


play_button = ui.ImageButton(500, 240, 150, 150, images["mover"], compose(lambda x: play_sound("click"), go_to_game),
                             anchor="left-bottom")
add_ui(play_button, ["Main Menu", "Play"], menu="Main Menu")
quit_button = ui.ImageButton(500, 40, 150, 150, images["trash"], quit_app, anchor="right-bottom")
add_ui(quit_button, ["Main Menu", "Quit"], menu="Main Menu")
credits_button = ui.ImageButton(500, 40, 150, 150, images["push"],
                                compose(lambda x: play_sound("click"), go_to_credits), anchor="left-bottom")
add_ui(credits_button, ["Main Menu", "Credits"], menu="Main Menu")

def draw_text(x, y, direction, name, flags, text, outline=False, color=(255, 255, 255)):
    if flags.get("shadow"):
        return
    text = str(text)
    f = dict(flags)
    f["raw"] = True
    f["nearest"] = True
    if outline:
        f["source"] = small_font.render(text, False, outline)
        f["source"] = pygame.transform.scale_by(f["source"], (f.get("size", 1), f.get("size", 1)))
        px = max(1, round(cell_size / 32))
        step = px / cell_size
        for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            draw_cell(x + dx * step, y + dy * step, direction, name, f)
    f["source"] = small_font.render(text, False, color)
    f["source"] = pygame.transform.scale_by(f["source"], (f.get("size", 1), f.get("size", 1)))
    draw_cell(x, y, direction, name, f)

def draw_storage(x, y, direction, name, flags):
    f = dict(flags)
    f["raw"] = True
    draw_cell(x, y, direction, name, f)
    f_s = dict(flags)
    if flags.get("size"):
        f_s["size"] *= 0.5
    else:
        f_s["size"] = 0.5
    if (stored := f_s["cell"].storing_raw) is not None:
        f_s["cell"] = stored
        draw_cell(x, y, stored.direction, stored.name, f_s)

def draw_texter(x, y, direction, name, flags):
    txt = str(flags["cell"].properties["Text"])
    f = dict(flags)
    f["raw"] = True
    if txt == "":
        draw_cell(x, y, direction, name, flags=f)
        return
    draw_text(x, y, direction, name, f, txt, color=flags["cell"].properties["Color"])

def draw_disable_storage(x, y, direction, name, flags):
    store = flags["cell"].storing_raw
    if store is not None:
        draw_cell(x, y, direction, store.name, flags)
    draw_cell(x, y, direction, "effects/disabled", flags)

def draw_single_cell_generator(x, y, direction, name, flags):
    f = dict(flags)
    f["raw"] = True
    draw_cell(x, y, direction, name + " full" if flags["cell"].vars.get("full", False) else name, f)

def draw_fraction(numerator_name, denominator_name):
    def wrapper(x, y, direction, name, flags):
        txt = str(flags["cell"].properties[numerator_name])+"/"+str(flags["cell"].properties[denominator_name])
        if flags["cell"].properties[denominator_name] == 1:
            txt = str(flags["cell"].properties[numerator_name])
        draw_text(x, y, direction, name, flags, txt, outline=utils.get_darkest_color(images[name]))
    return wrapper

def draw_number(number_name, offset_y=0, offset_x=0, offset_size=1):
    def wrapper(x, y, direction, name, flags):
        txt = str(flags["cell"].properties[number_name])
        size = flags.get("size", 1)*offset_size
        draw_text(x+(offset_x*size), y+(offset_y*size), direction, name, flags, txt, outline=utils.get_darkest_color(images[name]))
    return wrapper

draw_funcs = {
    "storage": draw_storage,
    "texter": draw_texter,
    "disablestorage": draw_disable_storage,
    "single cell generator": draw_single_cell_generator,
    "meta": draw_storage,
}

after_draw_funcs = {
    "electrocutor": draw_fraction("Numerator", "Denominator"),
    "bread": draw_fraction("Numerator", "Denominator"),
    "adjustable weight": draw_fraction("Numerator", "Denominator"),
    "adjustable rotator": draw_fraction("Numerator", "Denominator"),
    "random push": draw_fraction("Numerator", "Denominator"),
    "meta": draw_number("Index", offset_x=0.25, offset_y=0.25),
    "coin diverger": draw_number("Cost", offset_x=0.25, offset_y=0.25),
}

def draw_cell(x, y, direction, name, flags=None):
    flags = flags or {}
    if (f := draw_funcs.get(name)) and not flags.get("raw"):
        f(x, y, direction, name, flags)
        if (f := after_draw_funcs.get(name)) and not flags.get("raw"):
            f(x, y, direction, name, flags)
        return
    screen_x = int((x * cell_size) - camera_x)
    screen_y = int((y * cell_size) - camera_y)

    if (screen_x < -cell_size or screen_x > SCREEN_WIDTH or
            screen_y < -cell_size or screen_y > SCREEN_HEIGHT):
        return
    flags["size"] = flags.get("size", 1)
    ccell_size = cell_size
    if flags.get("eaten", False):
        flags["size"] *= (1 - lerp_time)
    if flags.get("size") is not None:
        ccell_size = round(cell_size * flags.get("size"))
    if ccell_size <= 0: return

    if flags.get("source"):
        surf = flags["source"].copy()
        scale = pygame.transform.scale_by if flags.get("nearest") else pygame.transform.smoothscale_by
        surf = scale(surf, (cell_size / 32, cell_size / 32))
        center_x = screen_x + (cell_size // 2)
        center_y = screen_y + (cell_size // 2)
        rect = surf.get_rect(center=(center_x, center_y))
        if flags.get("shadow"):
            surf = shadow(surf)
        screen.blit(surf, rect)
        return
    surf = pygame.transform.scale(images[name], (ccell_size, ccell_size))
    angle = direction * -90
    surf = pygame.transform.rotate(surf, angle)

    center_x = screen_x + (cell_size // 2)
    center_y = screen_y + (cell_size // 2)
    rect = surf.get_rect(center=(center_x, center_y))
    if flags.get("shadow"):
        surf = shadow(surf)
    screen.blit(surf, rect)
    if (f := after_draw_funcs.get(name)) and not flags.get("raw"):
        f(x, y, direction, name, flags)


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


def shadow(surf, opacity=30):
    copy = surf.copy()
    copy.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
    copy.fill((opacity, opacity, opacity, opacity), special_flags=pygame.BLEND_RGBA_MULT)
    return copy


def draw_grid():
    for x, y, cell in grid:
        draw_cell(x, y, 0, "bg")

    for (cell, trashpos) in grid.eaten:
        if cell is None: continue
        draw_cell(lerp(cell.oldx, trashpos[0], lerp_time), lerp(cell.oldy, trashpos[1], lerp_time),
                  lerp_angle(cell.olddirection, cell._direction, lerp_time), cell.name,
                  flags={"eaten": True, "x": None, "y": None, "cell": cell,})
    for x, y, cell in grid:
        if cell is None: continue

        draw_x, draw_y = lerp(cell.oldx, x, lerp_time), lerp(cell.oldy, y, lerp_time)
        if cell.anim_center is not None:
            draw_x, draw_y = polar_lerp((cell.oldx, cell.oldy), (x, y), cell.anim_center, lerp_time)

        draw_cell(draw_x + 0.25, draw_y + 0.25,
                  lerp_angle(cell.olddirection, cell._direction, lerp_time),
                  cell.name,
                  flags={"x": x, "y": y, "cell": cell, "shadow": True}
        )
        for eaten in cell.eaten:
            draw_cell(lerp(eaten.oldx, x, lerp_time), lerp(eaten.oldy, y, lerp_time),
                      lerp_angle(eaten.olddirection, eaten._direction, lerp_time), eaten.name,
                      flags={"eaten": True, "x": None, "y": None, "cell": eaten, })
        draw_cell(draw_x, draw_y,
                  lerp_angle(cell.olddirection, cell._direction, lerp_time),
                  cell.name, flags={"x": x, "y": y, "cell": cell, })
        if cell.vars["wrot"] != 0:
            draw_cell(draw_x, draw_y,
                      0,
                      "ana rotated" if cell.vars["wrot"] > 0 else "kata rotated", flags={"x": x, "y": y})
        if cell.vars["srot"] != 0:
            draw_cell(draw_x, draw_y,
                      0,
                      "cw 22.5 rotated" if cell.vars["srot"] > 0 else "ccw 22.5 rotated", flags={"x": x, "y": y})
            srot = round(cell.vars["srot"], 3)
            if srot > 0:
                srot = "+"+str(srot)
            elif srot < 0:
                srot = "-"+str(-srot)
            else:
                srot = ""
            draw_text(draw_x, draw_y-0.1,
                      0,
                      "cw 22.5 rotated" if cell.vars["srot"] > 0 else "ccw 22.5 rotated", {"x": x, "y": y, "size": 0.6},
                      srot, outline=(225, 78, 46) if cell.vars["srot"] > 0 else (46, 168, 219))
        if cell.vars["coins"] != 0:
            draw_cell(draw_x, draw_y,
                      0,
                      "coins", flags={"x": x, "y": y})
            draw_text(draw_x, draw_y-0.325,
                      0,
                      "coins", {"x": x, "y": y},
                      str(cell.vars["coins"]))
        for effect in vars(cell.effects):
            if not getattr(cell.effects, effect): continue
            if isinstance(effect, list): effect = effect[0]
            draw_cell(draw_x, draw_y,
                      0,
                      f"effects/{effect}", flags={"x": x, "y": y})


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


def place_cell(x, y, direction, name, properties=None):
    if 0 <= x < grid.width and 0 <= y < grid.height:
        grid[x, y] = Cell(direction, name, properties=properties)


def delete_cell(x, y):
    if 0 <= x < grid.width and 0 <= y < grid.height:
        grid[x, y] = None


def reset_cells():
    grid.eaten = []
    perm_effects = []
    for x, y, cell in grid:
        if cell is not None:
            if cell.name == "disablestorage":
                cell = cell.storing_raw
                grid[x, y] = cell
                if cell is None: continue
            cell.oldx, cell.oldy = x, y
            cell.olddirection = cell._direction % 4
            cell._direction = cell._direction % 4
            cell.updated = False
            cell.eaten = []
            cell.anim_center = None
            for effect in vars(cell.effects):
                if effect not in perm_effects:
                    setattr(cell.effects, effect, False)


def do_camera():
    global camera_x, camera_y

    def calc_player_cam():
        player_pos = []
        for x, y, cell in grid:
            if cell is not None:
                if cell.name in ["player", "player mover", "anti player", "pull player"]:
                    player_pos.append((lerp(cell.oldx, x, lerp_time) * cell_size + cell_size / 2,
                                       lerp(cell.oldy, y, lerp_time) * cell_size + cell_size / 2))
        if len(player_pos) == 0:
            return None
        return (sum([i[0] for i in player_pos]) / len(player_pos) - SCREEN_WIDTH / 2,
                sum([i[1] for i in player_pos]) / len(player_pos) - SCREEN_HEIGHT / 2)

    plrcalc = calc_player_cam()
    if plrcalc is not None and sim_running:
        camera_x, camera_y = plrcalc


def tick():
    global saved
    if saved is None:
        saved = deepcopy(grid.grid)
    grid.update_cells()
    for x in range(grid.width):
        for y in range(grid.height):
            if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                grid[x, y] = Cell(0, "ghost")
    save_state_button.enabled = True
    load_state_button.enabled = True
    grid.ticks += 1


_light_mask = None


def draw_bright_areas():
    global _light_mask
    screen_rect = screen.get_rect()

    sources = []
    has_dark = False
    for x, col in enumerate(grid.grid):
        for y, cell in enumerate(col):
            if cell is None: continue
            name = cell.name
            if name == "night":
                rect = screen_rect.copy()
                is_light = False
            elif name == "light" or name == "dark":
                p = cell.properties
                rect = pygame.Rect(0, 0, p.get("Width", 3) * cell_size, p.get("Height", 3) * cell_size)
                rect.center = ((x + 0.5) * cell_size - camera_x, (y + 0.5) * cell_size - camera_y)
                if not rect.colliderect(screen_rect): continue
                is_light = name == "light"
            else:
                continue
            has_dark |= not is_light
            sources.append((cell.properties.get("Strength", 10), is_light, rect))

    if not has_dark:
        return

    size = screen.get_size()
    if _light_mask is None or _light_mask.get_size() != size:
        _light_mask = pygame.Surface(size, pygame.SRCALPHA)
    else:
        _light_mask.fill((0, 0, 0, 0))

    sources.sort(key=lambda s: (s[0], s[1]))
    for strength, is_light, rect in sources:
        if is_light:
            _light_mask.fill((0, 0, 0, 0), rect)
        else:
            pygame.draw.rect(_light_mask, (0, 0, 0, 80), rect)

    screen.blit(_light_mask, (0, 0))


ui_dir_from = 0
ui_dir_to = 0
ui_dir_t = 1
ui_dir_shown = 0

def update_ui_rotation(dt):
    global ui_dir_from, ui_dir_to, ui_dir_t, ui_dir_shown
    target = selected_cell["direction"]
    if target != ui_dir_to:
        ui_dir_from = ui_dir_shown % 4
        ui_dir_to = target
        ui_dir_t = 0
    ui_dir_t = min(1, ui_dir_t + dt / 0.1)
    ui_dir_shown = lerp_angle(ui_dir_from, ui_dir_to, ui_dir_t)
    angle = ui_dir_shown * -90
    for element in GameUI.elements:
        tag = getattr(element, "tag", None)
        if tag and tag[0] in ("Category Button", "Subcategory Button", "Cell Button"):
            element.angle = angle


dt = 0
amb = pygame.mixer.Sound("SMod Soundtrack.wav")
amb.play(loops=-1)
while running:
    key_buttons = pygame.key.get_pressed()
    if key_buttons[pygame.K_LEFT]:
        player_input.append("left")
    if key_buttons[pygame.K_DOWN]:
        player_input.append("down")
    if key_buttons[pygame.K_UP]:
        player_input.append("up")
    if key_buttons[pygame.K_RIGHT]:
        player_input.append("right")
    mouse_pos = pygame.mouse.get_pos()
    mx, my = int((mouse_pos[0] + camera_x) // cell_size), int((mouse_pos[1] + camera_y) // cell_size)
    lerp_time += dt * (1 / update_delay)
    if lerp_time >= 1 and menu == "Game":
        lerp_time = 0
        stepping = False
        reset_cells()
        if sim_running:
            tick()
        player_input.clear()
    if menu == "Main Menu":
        lerp_time = 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break
        if event.type == pygame.VIDEORESIZE:
            SCREEN_WIDTH, SCREEN_HEIGHT = event.size
        if event.type == pygame.KEYDOWN:
            if adj_menu_name is not None and adj_text_input is not None:
                if adj_text_input.handle_key(event):
                    continue
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
            else:
                if menu == "Game" and 0 <= mx < grid.width and 0 <= my < grid.height:
                    if grid[mx, my] is not None and cells.get_tag(grid[mx, my].name, "can_store"):
                        place_type = "store"
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button not in (4, 5):
                if menu == "Game":
                    GameUI.click()
                    AdjMenuUI.click()
                elif menu == "Main Menu":
                    MainMenuUI.click()
    mouse_buttons = pygame.mouse.get_pressed()
    if menu == "Game" and adj_menu_name is None:
        if mouse_buttons == (False,) * 3:
            place_type = "place"
        if mouse_buttons[0] and not GameUI.hover():
            if 0 <= mx < grid.width and 0 <= my < grid.height:
                if grid[mx, my] is not None and cells.get_tag(grid[mx, my].name, "can_store") and place_type == "store":
                    grid[mx, my].storing = Cell(selected_cell["direction"], selected_cell["name"], properties=adjustables.get(selected_cell["name"], {}))
                elif place_type == "place":
                    place_cell(mx, my, selected_cell["direction"], selected_cell["name"],
                               properties=adjustables.get(selected_cell["name"], {}))
                    for x in range(grid.width):
                        for y in range(grid.height):
                            if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                                grid[x, y] = Cell(0, "ghost")
        if mouse_buttons[2] and not GameUI.hover():
            if 0 <= mx < grid.width and 0 <= my < grid.height:
                if grid[mx, my] is not None and cells.get_tag(grid[mx, my].name,
                                                              "can_store") and place_type == "store" and grid[
                    mx, my].storing is not None:
                    grid[mx, my].storing = None
                elif place_type == "place":
                    delete_cell(mx, my)
                    for x in range(grid.width):
                        for y in range(grid.height):
                            if x == 0 or y == 0 or x == grid.width - 1 or y == grid.height - 1:
                                grid[x, y] = Cell(0, "ghost")
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
        do_camera()
        draw_grid()
        draw_bright_areas()
        draw_ghost_cell(mx, my, selected_cell["direction"], selected_cell["name"])
        if adjustables.get(selected_cell["name"]) is not None:
            adj_button.enabled = True
        else:
            adj_button.enabled = False
        update_ui_rotation(dt)
        GameUI.draw()
        draw_infobox()
        draw_cate_infobox()
        draw_adjustable_menu()
        fps_txt = small_font.render("FPS: " + str(fps), True, (255,) * 3)
        screen.blit(fps_txt, (20, 0))
        AdjMenuUI.draw()
        if adj_text_input:
            adj_text_input.update_animation(dt)
        GameUI.update_animation(dt)
    if menu == "Main Menu":
        screen.fill((30,) * 3)
        MainMenuUI.draw()
        screen.blit(title_logo, ((SCREEN_WIDTH - title_logo.get_width()) // 2 + 20,
                                 40 + math.sin(pygame.time.get_ticks() / 500) * 10))
        draw_main_infobox()
    pygame.display.flip()
    dt = clock.tick(120) / 1000
    fps = 1 / dt
pygame.quit()