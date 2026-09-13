import math
import sys
from copy import deepcopy

import pygame
grid_width = 50
grid_height = 50

"""
cells without a chunk automatically get a chunk specifically for itself so that's why you might not see
mover cell on the list
"""

chunks = {
    "rotator": ["cw rotator", "ccw rotator"]
}

def to_vec(direction):
    return {
        0: Vector(1, 0),
        1: Vector(0, 1),
        2: Vector(-1, 0),
        3: Vector(0, -1),
    }[direction]

def to_dir(vector):
    if vector.x == 1 and vector.y == 0: return 0
    if vector.x == 0 and vector.y == 1: return 1
    if vector.x == -1 and vector.y == 0: return 2
    if vector.x == 0 and vector.y == -1: return 3
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
                if (cell is not None and cell.name != chunkid) and (cell is not None and cell.name not in chunks.get(chunkid, [])):
                    continue
                if cell is not None and not cell.updated:
                    if cell.effects.frozen: continue
                    func(x, y, cell)
                    cell.updated = True
            return
        if direction % 2 == 0:
            r = range(0, self.width)
            if direction == 0:
                r = reversed(r)
            for x in r:
                for y in range(0, self.height):
                    if (cell := self[x, y]) is not None and not cell.updated:
                        if (cell.name != chunkid) and (cell.name not in chunks.get(chunkid, [])):
                            continue
                        if cell.direction == direction:
                            if cell.effects.frozen: continue
                            func(x, y, cell)
                            cell.updated = True
        elif direction % 2 == 1:
            r = range(0, self.height)
            if direction == 1:
                r = reversed(r)
            for y in r:
                for x in range(0, self.width):
                    if (cell := self[x, y]) is not None and not cell.updated:
                        if (cell.name != chunkid) and (cell.name not in chunks.get(chunkid, [])):
                            continue
                        if cell.direction == direction:
                            if cell.effects.frozen: continue
                            func(x, y, cell)
                            cell.updated = True

    def update_cells(self):
        self.subtick("freezer")
        self.subtick("generator", 0)
        self.subtick("generator", 2)
        self.subtick("generator", 1)
        self.subtick("generator", 3)
        self.subtick("rotator")
        self.subtick("mover", 0)
        self.subtick("mover", 2)
        self.subtick("mover", 1)
        self.subtick("mover", 3)

    def get_neighbors(self, x, y):
        l = []
        for i in range(4):
            v = to_vec(i)
            l.append((x+v.x, y+v.y, self[x+v.x, y+v.y]))
        return l

    def freeze_cell(self, x, y):
        if self[x, y] is not None:
            self[x, y].effects.frozen = True

    def rotate_cell(self, x, y, amt):
        if self[x, y] is not None:
            self[x, y].direction += amt
            self[x, y].direction %= 4

    def eat_cell(self, x, y, tx, ty):
        self.eaten.append((self[x, y], (tx, ty)))

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
                    if side == 0:
                        direction.rotate(-1)
                    elif side == 1:
                        direction.rotate(1)
                    else:
                        break
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

        if not success: return False
        for px, py, pcx, pcy in reversed(to_push):
            if self[px, py] is None: continue
            self[pcx, pcy] = self[px, py]
            self[px, py] = None

        if self[orig_x, orig_y] is None:
            self[orig_x, orig_y] = flags["replacecell"]
        return True

    def handle_push(self, x, y, direction, flags):
        cell = self[x, y]
        old_direction = Vector(direction.x, direction.y)
        nx, ny, direction, _ = self.step_forward(x, y, direction)
        if cell is not None:
            old_dir = to_dir(old_direction)
            new_dir = to_dir(direction)
            cell.direction = (cell.direction + new_dir - old_dir) % 4
        ddir = to_dir(direction)
        front_cell = self[nx, ny]
        lastpos = flags["lastpos"]
        if lastpos == (None, None):
            lastpos = None
        replace_cell = flags.get("replacecell", None)
        success = True

        if cell.name == "slide":
            if ddir % 2 != cell.direction % 2:
                flags["force"] = 0
        if cell.name == "wall":
            flags["force"] = 0

        if cell.name == "trash":
            if lastpos is not None:
                self.eat_cell(*lastpos, x, y)
                self[*lastpos] = None
            else:
                replace_cell = None
            flags["break"] = True
        if cell.name == "enemy":
            if lastpos is not None:
                self[*lastpos] = None
            else:
                replace_cell = None
            self.eat_cell(x, y, x, y)
            self[x, y] = None
            flags["break"] = True

        if front_cell is not None:
            if front_cell.name == "mover" and not front_cell.effects.frozen:
                if front_cell.direction == ddir:
                    flags["force"] += 1
                elif front_cell.direction == (ddir+2)%4:
                    flags["force"] -= 1
        if flags["force"] <= 0: success = False
        flags["replacecell"] = replace_cell
        return nx, ny, direction, flags, success

    def DoMover(self, x, y, cell):
        self.push_cell(x, y, to_vec(cell.direction))

    def DoRotator(self, x, y, cell):
        rotation = {
            "cw rotator": 1,
            "ccw rotator": -1,
        }[cell.name]
        for i, j, c in self.get_neighbors(x, y):
            self.rotate_cell(i, j, rotation)

    def DoGenerator(self, x, y, cell):
        bx, by, j, copy = self.step_backward(x, y, to_vec(cell.direction))
        fx, fy, k, _ = self.step_forward(x, y, to_vec(cell.direction))
        if copy is None: return
        self.push_cell(fx, fy, to_vec(cell.direction), {"replacecell": copy})

    def DoFreezer(self, x, y, cell):
        for vx, vy, vcell in self.get_neighbors(x, y):
            self.freeze_cell(vx, vy)

grid = Grid(grid_width, grid_height)

class EffectList:
    def __init__(self, d=None):
        d = d or {}
        for var in ["frozen"]:
            setattr(self, var, d.get(var, False))

class Cell:
    def __init__(self, direction, name, oldx=None, oldy=None, olddirection=None, eatencells=None, updated=False, effects=None):
        self.direction = direction
        self.name = name
        self.oldx = oldx
        self.oldy = oldy
        self.olddirection = olddirection
        self.eatencells = [] if eatencells is None else eatencells
        self.updated = updated
        self.effects = effects if effects is not None else EffectList([])

    def copy(self):
        copied = Cell(**vars(self))
        copied.updated = False
        copied.effects = deepcopy(copied.effects)
        return copied