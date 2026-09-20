import math
import random
import sys
from copy import deepcopy
from utils import list_all

import pygame
grid_width = 50
grid_height = 50

"""
cells without a chunk automatically get a chunk specifically for itself so that's why you might not see
mover cell on the list
"""

chunks = {
    "rotator": ["cw 90 rotator", "ccw 90 rotator", "180 rotator", "random 90 rotator", "cw 45 rotator", "ccw 45 rotator", "random 45 rotator", "cw 135 rotator", "ccw 135 rotator", "random 135 rotator",
                "skidhi 90"],
    "gear": ["cw gear", "ccw gear"],
    "generator": ["cw generator", "ccw generator"],
    "mover": ["leaper", "hydra", "skidhi 90"]
}

tags = {}
def add_tag(tag, pairs):
    for pair in pairs.items():
        tags[pair[0]] = pair[1]

def get_tag(name, tag, *args):
    f = tags.get(name, None)
    if callable(f):
        return f(*args)
    return f

def is_unbreakable(cell, force_type, side):
    return get_tag(cell.name, "is_unbreakable", force_type, side, cell)

def unbreakable_to(*force_types):
    return lambda f_t, s, c: f_t in force_types

add_tag("unbreakable", {
    "wall": True,
    "ghost": True,
    "redirector": unbreakable_to("redirect"),
    "freezer": unbreakable_to("freeze"),
    "mirror": lambda f_t, s, c: f_t == "swap" and s%2 == 0,
})

def to_vec(direction):
    return {
        0: Vector(1, 0),
        1: Vector(0, 1),
        2: Vector(-1, 0),
        3: Vector(0, -1),
        0.5: Vector(1, 1),
        1.5: Vector(-1, 1),
        2.5: Vector(-1, -1),
        3.5: Vector(1, -1),
    }[direction]

def to_dir(vector):
    mag = vector.magnitude
    if mag == 0:
        return 0

    ux = round(vector.x / mag)
    uy = round(vector.y / mag)

    if ux == 1 and uy == 0: return 0
    if ux == 1 and uy == 1: return 0.5
    if ux == 0 and uy == 1: return 1
    if ux == -1 and uy == 1: return 1.5
    if ux == -1 and uy == 0: return 2
    if ux == -1 and uy == -1: return 2.5
    if ux == 0 and uy == -1: return 3
    if ux == 1 and uy == -1: return 3.5

    return math.atan2(vector.y, vector.x)

def to_side(cell_dir, f_dir):
    return (f_dir-cell_dir+2)%4

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)
    def __mul__(self, other):
        return Vector(self.x * other, self.y * other)
    def __truediv__(self, other):
        return Vector(self.x / other, self.y / other)
    def __neg__(self):
        return Vector(-self.x, -self.y)
    @property
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)

    def rotate(self, degrees):
        degrees *= 90
        radians = math.radians(degrees)
        cos_theta = math.cos(radians)
        sin_theta = math.sin(radians)
        new_x = self.x * cos_theta - self.y * sin_theta
        new_y = self.x * sin_theta + self.y * cos_theta
        self.x = round(new_x)
        self.y = round(new_y)

class EffectList:
    def __init__(self, d=None):
        d = d or {}
        for var in ["frozen", "thawed"]:
            setattr(self, var, d.get(var, False))

class Cell:
    def __init__(self, direction, name, oldx=None, oldy=None, olddirection=None, eatencells=None, updated=False, effects=None, noupdate=False):
        self.direction = direction
        self.name = name
        self.oldx = oldx
        self.oldy = oldy
        self.olddirection = olddirection
        self.eatencells = [] if eatencells is None else eatencells
        self.updated = updated
        self.noupdate = False
        self.effects = effects if effects is not None else EffectList([])

    def copy(self):
        copied = Cell(**vars(self))
        copied.effects = deepcopy(copied.effects)
        return copied

class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[None] * height for _ in range(width)]
        self.eaten = []
    def __getitem__(self, key):
        x, y = key
        if x is None or y is None: return None
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[x][y]
        return None
    def __setitem__(self, key, value):
        x, y = key
        if x is None or y is None: return None
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x][y] = value
    def __iter__(self):
        for x in range(self.width):
            for y in range(self.height):
                yield x, y, self[x, y]

    def subtick(self, chunkid, direction=None):
        func = getattr(self, "Do" + chunkid[0].upper() + chunkid[1:])

        if direction is None:
            for x, y, cell in self:
                if (cell is not None and cell.name != chunkid) and (
                        cell is not None and cell.name not in chunks.get(chunkid, [])):
                    continue
                if cell is not None and not cell.updated:
                    if cell.effects.frozen:
                        continue
                    func(x, y, cell)
                    if not cell.noupdate:
                        cell.updated = True
                    else:
                        cell.noupdate = False
            return

        if direction == 0:
            xs = range(self.width - 1, -1, -1)
            ys = range(self.height)

        elif direction == 1:
            xs = range(self.width)
            ys = range(self.height - 1, -1, -1)

        elif direction == 2:
            xs = range(self.width)
            ys = range(self.height)

        elif direction == 3:
            xs = range(self.width)
            ys = range(self.height)

        elif direction == 0.5:
            xs = range(self.width - 1, -1, -1)
            ys = range(self.height - 1, -1, -1)

        elif direction == 1.5:
            xs = range(self.width)
            ys = range(self.height - 1, -1, -1)

        elif direction == 2.5:
            xs = range(self.width)
            ys = range(self.height)

        elif direction == 3.5:
            xs = range(self.width - 1, -1, -1)
            ys = range(self.height)

        for x in xs:
            for y in ys:
                cell = self[x, y]

                if cell is None or cell.updated:
                    continue

                if cell.name != chunkid and cell.name not in chunks.get(chunkid, []):
                    continue

                if cell.direction == direction:
                    if cell.effects.frozen:
                        continue

                    func(x, y, cell)
                    if not cell.noupdate:
                        cell.updated = True
                    else:
                        cell.noupdate = False

    def direction_subtick(self, chunkid):
        for i in [0, 0.5, 2, 2.5, 1, 1.5, 3, 3.5]:
            self.subtick(chunkid, i)

    def update_cells(self):
        self.subtick("thawer")
        self.subtick("freezer")
        self.direction_subtick("mirror")
        self.direction_subtick("generator")
        self.subtick("gear")
        self.subtick("rotator")
        self.subtick("redirector")
        self.direction_subtick("puller")
        self.direction_subtick("mover")

    def get_neighbors(self, x, y):
        l = []
        for i in range(4):
            v = to_vec(i)
            l.append((x+v.x, y+v.y, self[x+v.x, y+v.y]))
        return l

    def get_surrounding(self, x, y):
        l = {}
        for i in range(8):
            i /= 2
            v = to_vec(i)
            l[i] = (x+v.x, y+v.y, self[x+v.x, y+v.y])
        return l

    def freeze_cell(self, x, y, side):
        if self[x, y] is not None:
            if is_unbreakable(self[x, y], "freeze", side): return
            if self[x, y].effects.thawed: return
            self[x, y].effects.frozen = True

    def thaw_cell(self, x, y, side):
        if self[x, y] is not None:
            if is_unbreakable(self[x, y], "thaw", side): return
            self[x, y].effects.thawed = True
            self[x, y].effects.frozen = False

    def rotate_cell(self, x, y, amt, side):
        if self[x, y] is not None:
            if is_unbreakable(self[x, y], "rotate", side): return
            self[x, y].direction += amt
            self[x, y].direction %= 4

    def redirect_cell(self, x, y, direction, side):
        if self[x, y] is not None:
            if is_unbreakable(self[x, y], "redirect", side): return
            self[x, y].direction = direction

    def eat_cell(self, x, y, tx, ty):
        self.eaten.append((self[x, y], (tx, ty)))

    def direct_step_forward(self, x, y, direction=None):
        if direction is None:
            direction = to_vec(self[x, y].direction)

        f = deepcopy(direction)
        nx, ny = x + f.x, y + f.y
        return nx, ny, f, self[nx, ny]

    def step_forward(self, x, y, direction):
        end_x, end_y = x, y
        start_x, start_y = x, y
        loops = 0
        while True:
            cdir = to_dir(direction)
            end_x += direction.x
            end_y += direction.y
            cell = self[end_x, end_y]
            if (end_x, end_y) == (start_x, start_y):
                loops += 1
            if loops > 5:
                break
            if cell is None:
                break
            else:
                side = to_side(cell.direction, cdir)
                if cell.name == "curve diverger":
                    if side == 0: direction.rotate(-1)
                    elif side == 1: direction.rotate(1)
                    else: break
                elif cell.name == "straight diverger":
                    if side % 2 == 0: pass
                    else: break
                elif cell.name == "bicurve diverger":
                    if side % 2 == 0: direction.rotate(-1)
                    elif side % 2 == 1: direction.rotate(1)
                    else: break
                elif cell.name == "bistraight diverger":
                    if side % 1 == 0: pass
                    else: break
                elif cell.name == "diode diverger":
                    if side == 2: pass
                    else: break
                else:
                    break
        if cell is not None:
            to_copy = cell.copy()
            to_copy.direction += to_dir(direction) - cell.direction
            return end_x, end_y, direction, to_copy
        return end_x, end_y, direction, None

    def step_backward(self, x, y, direction):
        result = self.step_forward(x, y, -direction)
        result = [i for i in result]
        result[2] = -result[2]
        result[3] = None

        if self[*result[0:2]] is not None:
            cell = self[*result[0:2]]
            to_copy = cell.copy()

            old_dir = to_dir(-result[2])
            new_dir = to_dir(direction)

            to_copy.direction = (to_copy.direction - new_dir + old_dir + 2) % 4
            result[3] = to_copy

        return result

    def push_cell(self, x, y, direction, flags=None):
        orig_x, orig_y = x, y
        cx, cy = x, y
        flags = flags if flags is not None else {}
        flags["force"] = flags.get("force", 1)
        flags["replacecell"] = flags.get("replacecell", None)

        to_push = []
        success = True
        lastx, lasty = (None,) * 2
        flags["loops"] = -1

        if flags.get("ignore_first", False):
            cx += direction.x
            cy += direction.y
            to_push.append((orig_x, orig_y, cx, cy))
            lastx, lasty = orig_x, orig_y

        sim_cx, sim_cy = cx, cy
        sim_dir = Vector(direction.x, direction.y)
        sim_loops = flags["loops"]
        path_coords = set()

        while True:
            if (sim_cx, sim_cy) == (orig_x, orig_y):
                sim_loops += 1
            if sim_loops >= 5:
                break
            cell = self[sim_cx, sim_cy]
            if cell is not None:
                path_coords.add((sim_cx, sim_cy))
                nx, ny, sim_dir, _ = self.step_forward(sim_cx, sim_cy, sim_dir)
                sim_cx, sim_cy = nx, ny
            else:
                break

        grid_snapshot = {}
        if flags.get("test", False):
            for px, py in path_coords:
                c = self[px, py]
                if c is not None:
                    grid_snapshot[(px, py)] = (c, c.direction, c.updated, deepcopy(c.effects))

        while True:
            if (cx, cy) == (orig_x, orig_y):
                flags["loops"] += 1
            if flags["loops"] >= 5:
                break
            cell = self[cx, cy]
            if cell is not None:
                flags["lastpos"] = (lastx, lasty)
                oldx, oldy = cx, cy
                cx, cy, direction, flags, success = self.handle_push(cx, cy, direction, flags)
                if not success or flags.get("break", False):
                    break
            else:
                break
            to_push.append((oldx, oldy, cx, cy))
            lastx, lasty = oldx, oldy

        def restore_snapshot():
            if flags.get("test", False):
                for px, py in path_coords:
                    self[px, py] = None
                for (px, py), (cell, direction, updated, effects) in grid_snapshot.items():
                    cell.direction = direction
                    cell.updated = updated
                    cell.effects = effects
                    self[px, py] = cell

        if not success:
            restore_snapshot()
            return False

        if not flags.get("test", False):
            for px, py, pcx, pcy in reversed(to_push):
                if self[px, py] is None: continue
                self[pcx, pcy] = self[px, py]
                self[px, py] = None

            if self[orig_x, orig_y] is None:
                self[orig_x, orig_y] = flags["replacecell"]
        else:
            restore_snapshot()

        return True

    def handle_push(self, x, y, direction, flags):
        cell = self[x, y]
        old_direction = Vector(direction.x, direction.y)
        nx, ny, direction, _ = self.step_forward(x, y, direction)
        ddir = to_dir(direction)
        side = to_side(cell.direction, ddir)
        front_cell = self[nx, ny]
        lastpos = flags["lastpos"]
        if lastpos == (None, None):
            lastpos = None
        replace_cell = flags.get("replacecell", None)
        success = True

        if is_unbreakable(cell, "push", side):
            flags["force"] = 0

        if cell.name == "slide":
            if side % 2 != 0:
                flags["force"] = 0
        if cell.name == "two directional":
            if side not in [0, 1]:
                flags["force"] = 0
        if cell.name == "three directional":
            if side == 2:
                flags["force"] = 0
        if cell.name == "random push":
            if random.random() < 0.5:
                flags["force"] = 0
        if cell.name == "one directional":
            if side != 0:
                flags["force"] = 0

        if cell.name == "weight":
            flags["force"] -= 1
        if cell.name == "anti weight":
            flags["force"] += 1
        if cell.name == "bias":
            if side == 2:
                flags["force"] += 1
            elif side == 0:
                flags["force"] -= 1
        if cell.name == "gold":
            if side % 1 != 0:
                flags["force"] = 0
        if cell.name == "lead":
            if side % 1 == 0:
                flags["force"] = 0

        if cell.name == "trash":
            if lastpos is not None:
                self.eat_cell(*lastpos, x, y)
                self[*lastpos] = None
            else:
                replace_cell = None
            flags["break"] = True
        if cell.name == "squish trash":
            v = deepcopy(flags)
            v["test"] = True
            v["ignore_first"] = True
            if not self.push_cell(x, y, direction, v):
                if lastpos is not None:
                    self.eat_cell(*lastpos, x, y)
                    self[*lastpos] = None
                else:
                    replace_cell = None
                flags["break"] = True

        if cell.name == "lichen":
            self.eat_cell(x, y, x, y)
            self[x, y] = None
            flags["break"] = True

            up_dir = (cell.direction + 1) % 4
            down_dir = (cell.direction - 1) % 4

            upcopy = deepcopy(cell)
            downcopy = deepcopy(cell)
            upcopy.updated = True
            downcopy.updated = True
            upcopy.direction = up_dir
            downcopy.direction = down_dir

            self[x, y] = upcopy
            up_ok = self.push_cell(x, y, to_vec(up_dir), {"test": True, "ignore_first": True})

            self[x, y] = downcopy
            down_ok = self.push_cell(x, y, to_vec(down_dir), {"test": True, "ignore_first": True})

            self[x, y] = None

            if up_ok and down_ok:
                self[x, y] = upcopy
                self.push_cell(x, y, to_vec(up_dir), {"replacecell": None, "ignore_first": True})
                self[x, y] = downcopy
                self.push_cell(x, y, to_vec(down_dir), {"replacecell": None, "ignore_first": True})
            elif up_ok:
                self[x, y] = upcopy
                self.push_cell(x, y, to_vec(up_dir), {"replacecell": None, "ignore_first": True})
            elif down_ok:
                self[x, y] = downcopy
                self.push_cell(x, y, to_vec(down_dir), {"replacecell": None, "ignore_first": True})

        if cell.name == "enemy":
            if lastpos is not None:
                self[*lastpos] = None
            else:
                replace_cell = None
            self.eat_cell(x, y, x, y)
            self[x, y] = None
            flags["break"] = True
        if cell.name == "squish enemy":
            v = deepcopy(flags)
            v["test"] = True
            v["ignore_first"] = True
            if not self.push_cell(x, y, direction, v):
                if lastpos is not None:
                    self[*lastpos] = None
                else:
                    replace_cell = None
                self.eat_cell(x, y, x, y)
                self[x, y] = None
                flags["break"] = True

        if front_cell is not None:
            if front_cell.name in ["mover", "leaper", "hydra", "skidhi 90"] and not front_cell.effects.frozen:
                if front_cell.direction == ddir:
                    flags["force"] += 1
                elif front_cell.direction == (ddir+2)%4:
                    flags["force"] -= 1
        if flags["force"] <= 0: success = False
        if cell is not None:
            old_dir = to_dir(old_direction)
            new_dir = to_dir(direction)
            cell.direction = (cell.direction + new_dir - old_dir) % 4
        flags["replacecell"] = replace_cell
        return nx, ny, direction, flags, success

    def swap_cells(self, x1, y1, x2, y2, side1, side2):
        a, b = self[x1, y1], self[x2, y2]

        a_copy = a.copy() if a is not None else None
        b_copy = b.copy() if b is not None else None

        if a_copy and is_unbreakable(a_copy, "swap", side1) or False: return False
        if b_copy and is_unbreakable(b_copy, "swap", side2) or False: return False

        self[x1, y1] = b_copy
        self[x2, y2] = a_copy
        return True

    def DoMirror(self, x, y, cell):
        if cell.name == "mirror":
            fx, fy, _, _ = self.direct_step_forward(x, y, to_vec(cell.direction))
            bx, by, _, _ = self.direct_step_forward(x, y, to_vec((cell.direction + 2) % 4))
            side1 = self[fx, fy] and to_side(self[fx, fy].direction, cell.direction) or 0
            side2 = self[bx, by] and to_side(self[bx, by].direction, (cell.direction + 2) % 4) or 0
            self.swap_cells(fx, fy, bx, by, side1, side2)

    def DoMover(self, x, y, cell):
        if cell.name in ["mover", "skidhi 90"]:
            self.push_cell(x, y, to_vec(cell.direction))
        elif cell.name == "leaper":
            self.push_cell(x, y, to_vec(cell.direction) * 2)
        elif cell.name == "hydra":
            if not self.push_cell(x, y, to_vec(cell.direction)):
                up_dir = (cell.direction + 1) % 4
                down_dir = (cell.direction - 1) % 4

                upcopy = deepcopy(cell)
                downcopy = deepcopy(cell)
                upcopy.updated = True
                downcopy.updated = True
                upcopy.direction = up_dir
                downcopy.direction = down_dir

                self[x, y] = upcopy
                up_ok = self.push_cell(x, y, to_vec(up_dir), {"test": True})

                self[x, y] = downcopy
                down_ok = self.push_cell(x, y, to_vec(down_dir), {"test": True})

                self[x, y] = cell

                if up_ok and down_ok:
                    self[x, y] = upcopy
                    self.push_cell(x, y, to_vec(up_dir), {"replacecell": None})
                    self[x, y] = downcopy
                    self.push_cell(x, y, to_vec(down_dir), {"replacecell": None})
                elif up_ok:
                    self[x, y] = upcopy
                    self.push_cell(x, y, to_vec(up_dir), {"replacecell": None})
                elif down_ok:
                    self[x, y] = downcopy
                    self.push_cell(x, y, to_vec(down_dir), {"replacecell": None})


    def DoPuller(self, x, y, cell):
        if cell.name == "puller":
            self.pull_cell(x, y, to_vec(cell.direction))

    def DoRotator(self, x, y, cell):
        if "skidhi" in cell.name:
            rotation = next((val for key, val in {"45": 45, "90": 90, "135": 135, "180": 180, "360": 360}.items() if
                             key in cell.name), 0) / 90
            fx, fy, _, f = self.direct_step_forward(x, y, to_vec(cell.direction))
            bx, by, _, b = self.direct_step_forward(x, y, to_vec((cell.direction+2)%4))
            if f is not None: self.rotate_cell(fx, fy, rotation, to_side(f.direction, cell.direction))
            if b is not None: self.rotate_cell(bx, by, -rotation, to_side(b.direction, cell.direction))
            cell.noupdate = True
            return
        rotation = next((val for key, val in {"45": 45, "90": 90, "135": 135, "180": 180, "360": 360}.items() if key in cell.name), 0)/90
        if "ccw" in cell.name:
            rotation = -rotation
        if "random" in cell.name:
            rotation = str(rotation)
        for k, (i, j, c) in enumerate(self.get_neighbors(x, y)):
            if not c: continue
            if isinstance(rotation, str): self.rotate_cell(i, j, random.choice([float(rotation), -float(rotation)]), to_side(c.direction, k)); continue
            self.rotate_cell(i, j, rotation, to_side(c.direction, k))

    def DoGenerator(self, x, y, cell):
        front_outputs = {
            "generator": 0,
            "cw generator": 1,
            "ccw generator": -1,
        }
        front_output = front_outputs.get(cell.name, 0)
        bx, by, j, copy = self.step_backward(x, y, to_vec(cell.direction))
        fx, fy, k, _ = self.step_forward(x, y, to_vec((cell.direction + front_output)%4))
        if copy is None: return
        if copy.name == "ghost": return
        copy.direction += front_output
        self.push_cell(fx, fy, to_vec((cell.direction + front_output)%4), {"replacecell": copy})

    def DoRedirector(self, x, y, cell):
        for k, (i, j, c) in enumerate(self.get_neighbors(x, y)):
            if not c: continue
            self.redirect_cell(i, j, cell.direction, to_side(c.direction, k))

    def DoThawer(self, x, y, cell):
        for k, (i, j, c) in enumerate(self.get_neighbors(x, y)):
            if not c: continue
            self.thaw_cell(i, j, to_side(c.direction, k))

    def DoFreezer(self, x, y, cell):
        for k, (i, j, c) in enumerate(self.get_neighbors(x, y)):
            if not c: continue
            self.freeze_cell(i, j, to_side(c.direction, k))

    def do_basic_gear(self, gear_x, gear_y, rotation):
        neighbors = self.get_surrounding(gear_x, gear_y)
        old_states = neighbors.copy()
        gears = ["cw gear", "ccw gear", "jam"]

        for i, (nx, ny, c) in enumerate(old_states.values()):
            if self[nx, ny] is not None:
                if self[nx, ny].name in gears:
                    return
                if is_unbreakable(c, "gear", to_side(c.direction, i)):
                    return

        self.rotate_cell(gear_x, gear_y, rotation, 0)

        for nx, ny, _ in old_states.values():
            self[nx, ny] = None

        for i in range(8):
            i /= 2
            nx, ny, cell = old_states[i]
            if cell is None:
                continue

            target_idx = (i + rotation) % 4
            target_nx, target_ny, _ = old_states[target_idx]

            to_copy = cell.copy()
            to_copy.direction = (to_copy.direction + rotation) % 4
            self[target_nx, target_ny] = to_copy

    def DoGear(self, x, y, cell):
        rotation = {
            "cw gear": 1,
            "ccw gear": -1,
        }
        self.do_basic_gear(x, y, rotation[cell.name])

grid = Grid(grid_width, grid_height)