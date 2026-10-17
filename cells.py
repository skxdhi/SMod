import math
import random
import sys
import weakref
from copy import deepcopy
from utils import raise_random_error
from loader import audio, images
import pygame

player_input = []
def play_sound(sound_name):
    audio[sound_name].play()

grid_width = 50
grid_height = 50

queue = {}

def add_channel(c):
    if c not in queue:
        queue[c] = []

def queue_task(c, task):
    queue[c].append(task)

def queue_last(c, task):
    queue[c].insert(0, task)

def run_queue(c):
    if (q:=queue.get(c)) is None: return
    while q:
        task = q.pop(0)
        task()

add_channel("postrotate")
add_channel("postpush")
add_channel("postpull")

"""
cells without a chunk automatically get a chunk specifically for itself so that's why you might not see
mover cell on the list
"""

chunks = {
    "rotator": ["cw 90 rotator", "ccw 90 rotator", "180 rotator", "random 90 rotator", "cw 45 rotator", "ccw 45 rotator", "random 45 rotator", "cw 135 rotator", "ccw 135 rotator", "random 135 rotator",
                "skidhi 90", "random 22.5 rotator","ana rotator", "kata rotator", "half ana rotator", "half kata rotator", "cw 22.5 rotator", "ccw 22.5 rotator", "adjustable rotator"],
    "gear": ["cw gear", "ccw gear", "slow cw gear", "slow ccw gear", "fast cw gear", "fast ccw gear", "180 gear"],
    "generator": ["cw generator", "ccw generator", "single cell generator"],
    "super generator": ["cw super generator", "ccw super generator"],
    "mover": ["leaper", "hydra", "skidhi 90", "slow mover", "player mover", "crusher", "purple mover", "bird", "bee"],
    "freezer": ["winter"],
    "thawer": ["summer"],
    "steer": ["player mover"],
    "player": ["anti player", "pull player"],
    "puller": ["advancer", "leaper puller", "slow puller"],
}

tags = {}
def add_tag(tag, pairs):
    if tag not in tags:
        tags[tag] = {}
    for name, value in pairs.items():
        tags[tag][name] = value

def get_tag(name, tag, *args, default=None):
    f = tags.get(tag, {}).get(name, default)
    if callable(f):
        return f(*args)
    return f

def is_unbreakable(cell, force_type, side):
    return get_tag(cell.name, "unbreakable", force_type, side, cell, default=False)

def collide(cell, force_type, side):
    return get_tag(cell.name, "collide", force_type, side, cell, default=False)

def gen_as(cell, side):
    return get_tag(cell.name, "gen_as", side, cell, default=cell.name)

def nudge_into(cell, side):
    return get_tag(cell.name, "nudge_into", side, cell, default=False)

def coin_cost(cell):
    return cell.properties.get("Cost", 1)

def total_toll(crossed):
    return sum(coin_cost(c) for c in crossed)

def unbreakable_to(*force_types):
    return lambda f_t, s, c: f_t in force_types

def unbreakable_sides(sides, func=False):
    if not func: return lambda f_t, s, c: (s in sides)
    return lambda f_t, s, c: (s in sides) or func(f_t, s, c)

add_tag("unbreakable", {
    "wall": True,
    "ghost": True,
    "redirector": unbreakable_to("redirect"),
    "freezer": unbreakable_to("freeze"),
    "winter": unbreakable_to("freeze"),
    "repulsor": unbreakable_to("repulse"),
    "impulsor": unbreakable_to("impulse"),
    "mirror": lambda f_t, s, c: f_t == "swap" and s%2 == 0,
    "arrow": unbreakable_to("rotate"),
    "crusher": unbreakable_sides([0]),
    "copper": unbreakable_to("electrocute"),
    "electrocutor": unbreakable_to("electrocute"),
})

add_tag("gen_as", {
    "ungeneratable": None,
    "monogeneratable": "ungeneratable",
})

add_tag("can_store", {
    "storage": True,
    "meta": True,
})

add_tag("cannot_disable", {
    "disabler": True,
    "enabler": True,
})

add_tag("collide", {
    "enemy": True,
    "bulk enemy": True,
})

add_tag("nudge_into", {
    "trash": True,
    "jump trash": True,
    "attack trash": True,
    "bulk trash": True,
    "omega trash": True,
    "enemy": True,
    "bulk enemy": True,
    "bread": True,
    "coin": True,
    "anti coin": True,
    "chocolate coin": True,
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
    }[direction%4]

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
    return (f_dir % 4 - cell_dir % 4 + 2) % 4

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
        for var in ["frozen", "thawed", "enabled", "electrocuted", "coppered"]:
            v = d.get(var, False)
            setattr(self, var, list(v) if isinstance(v, (list, tuple)) else v)

    def copy(self):
        return EffectList(vars(self))

class Cell:
    def __init__(self, direction, name, oldx=None, oldy=None, olddirection=None, eatencells=None, updated=False, effects=None, noupdate=False, eaten=None, v=None, anim_center=None, properties=None):
        self._direction = direction
        self.name = name
        self.oldx = oldx
        self.oldy = oldy
        self.olddirection = olddirection
        self.eatencells = [] if eatencells is None else eatencells
        self.updated = updated
        self.noupdate = noupdate
        self.effects = effects if effects is not None else EffectList()
        self.eaten = eaten if eaten is not None else []
        self.vars = v if v is not None else {}
        self.vars.setdefault("coins", 0)
        self.vars.setdefault("wrot", 0)
        self.vars.setdefault("srot", 0)
        self.anim_center = anim_center
        if isinstance(properties, dict):
            self.properties = properties
        else:
            self.properties = dict([(i["name"], i["current_val"]) for i in properties]) if properties is not None else {}

    @property
    def direction(self):
        return self._direction % 4

    @direction.setter
    def direction(self, value):
        self._direction = value

    @property
    def storing(self):
        if self.storing_raw is None or self.storing_raw.name == "void":
            return None
        if self.storing_raw.name == "self":
            return self.copy()
        if self.storing_raw.name == "meta":
            c = self.storing_raw.copy()
            if c.properties["Index"] > 1:
                c.properties["Index"] -= 1
                return c
            return self.storing_raw.storing
        return self.storing_raw

    @property
    def storing_raw(self):
        return self.vars.get("storing")

    @storing.setter
    def storing(self, value):
        self.vars["storing"] = value

    def copy(self):
        return Cell(
            direction=self._direction,
            name=self.name,
            oldx=self.oldx,
            oldy=self.oldy,
            olddirection=self.olddirection,
            eatencells=list(self.eatencells),
            updated=self.updated,
            effects=self.effects.copy(),
            noupdate=self.noupdate,
            eaten=list(self.eaten),
            v=dict(self.vars),
            properties=dict(self.properties)
        )


class Grid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[None] * height for _ in range(width)]
        self.eaten = []
        self.ticks = 0
        self.positions = weakref.WeakKeyDictionary()
    def __getitem__(self, key):
        x, y = key
        if x is None or y is None: return None
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[x][y]
        return None
    def __setitem__(self, key, value):
        x, y = key
        if x is None or y is None: return None
        if not (0 <= x < self.width and 0 <= y < self.height): return
        self.grid[x][y] = value
        if value is not None:
            self.positions[value] = (x, y)

    def locate(self, cell, x, y):
        if self[x, y] is cell:
            return x, y
        pos = self.positions.get(cell)
        if pos is not None and self[pos] is cell:
            return pos
        for gx, col in enumerate(self.grid):
            for gy, c in enumerate(col):
                if c is cell:
                    return gx, gy
        return None
    def __iter__(self):
        for x in range(self.width):
            for y in range(self.height):
                yield x, y, self[x, y]

    def update_cells(self):
        active_cells = []
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell is not None:
                    active_cells.append((x, y))

        self.subtick("thawer", active_cells)
        self.subtick("freezer", active_cells)
        self.subtick("enabler", active_cells)
        self.subtick("disabler", active_cells)
        self.subtick("electrocutor", active_cells)
        self.subtick("copper", active_cells)
        self.subtick("inertia", active_cells)
        self.directional_subtick("mirror", active_cells)
        self.directional_subtick("intaker", active_cells)
        self.directional_subtick("super generator", active_cells)
        self.directional_subtick("generator", active_cells)
        self.subtick("gear", active_cells)
        run_queue("postrotate")
        self.subtick("rotator", active_cells)
        run_queue("postrotate")
        self.subtick("redirector", active_cells)
        self.subtick("impulsor", active_cells)
        self.subtick("repulsor", active_cells)
        self.directional_subtick("puller", active_cells)
        self.subtick("steer", active_cells)
        self.directional_subtick("mover", active_cells)
        self.directional_subtick("nudger", active_cells)
        self.directional_subtick("player", active_cells)

    def directional_subtick(self, chunkid, active_cells):
        for i in [0, 0.5, 2, 2.5, 1, 1.5, 3, 3.5]:
            self.subtick(chunkid, active_cells, i)

    def subtick(self, chunkid, active_cells, direction=None):
        func = getattr(self, "Do" + chunkid.title().replace(" ", ""))
        valid_names = {chunkid}.union(chunks.get(chunkid, []))

        if direction is None:
            for x in range(self.width):
                col = self.grid[x]
                for y in range(self.height):
                    cell = col[y]
                    if cell is None or cell.name not in valid_names or cell.updated or cell.effects.frozen:
                        continue
                    self.run_cell(func, x, y, cell)
            return

        if direction in [0, 0.5, 3.5]:
            xs = range(self.width - 1, -1, -1)
        else:
            xs = range(self.width)

        if direction in [1, 0.5, 1.5]:
            ys = range(self.height - 1, -1, -1)
        else:
            ys = range(self.height)

        for x in xs:
            for y in ys:
                cell = self.grid[x][y]
                if cell is None or cell.name not in valid_names or cell.direction != direction or cell.updated or cell.effects.frozen:
                    continue
                self.run_cell(func, x, y, cell)

    def get_tick_count(self, cell):
        if not (e:=cell.effects.electrocuted): e = 1
        else: e = e[1]
        return math.floor((self.ticks+1)*e - math.floor(self.ticks*e))

    def run_cell(self, func, x, y, cell):
        for i in range(self.get_tick_count(cell)):
            if i > 0:
                pos = self.locate(cell, x, y)
                if pos is None:
                    break
                x, y = pos
            func(x, y, cell)
        if not cell.noupdate:
            cell.updated = True
        else:
            cell.noupdate = False

    def get_neighbors(self, x, y, dist=1, flags=None):
        flags = flags or {}
        l = {}
        for i in range(4):
            v = to_vec(i)*dist
            l[i] = (x+v.x, y+v.y, self[x+v.x, y+v.y])
        return l

    def get_diagonals(self, x, y, dist=1, flags=None):
        flags = flags or {}
        l = {}
        for i in range(4):
            i += 0.5
            v = to_vec(i)*dist
            l[i] = (x+v.x, y+v.y, self[x+v.x, y+v.y])
        return l

    def get_surrounding(self, x, y, dist=1):
        l = {}
        for i in range(8):
            i /= 2
            v = to_vec(i)*dist
            l[i] = (x+v.x, y+v.y, self[x+v.x, y+v.y])
        return l

    def electrocute_cell(self, x, y, amount, side=None):
        if self[x, y] is not None:
            if side is not None and is_unbreakable(self[x, y], "electrocute", side): return
            if self[x, y].effects.coppered: return
            self[x, y].effects.electrocuted = [True, amount]

    def copper_cell(self, x, y, side=None):
        if self[x, y] is not None:
            if side is not None and is_unbreakable(self[x, y], "copper", side): return
            self[x, y].effects.coppered = True
            self[x, y].effects.electrocuted = False

    def freeze_cell(self, x, y, side=None):
        if self[x, y] is not None:
            if side is not None and is_unbreakable(self[x, y], "freeze", side): return
            if self[x, y].effects.thawed: return
            self[x, y].effects.frozen = True

    def thaw_cell(self, x, y, side=None):
        if self[x, y] is not None:
            if side is not None and is_unbreakable(self[x, y], "thaw", side): return
            self[x, y].effects.thawed = True
            self[x, y].effects.frozen = False

    def rotate_cell(self, x, y, amt, side=None):
        if amt == 0: return
        if self[x, y] is not None:
            if side is not None and is_unbreakable(self[x, y], "rotate", side): return
            if self[x, y].name == "gyro":
                applied = self.take_srot(self[x, y], amt)
                if applied != 0:
                    queue_task("postrotate", lambda: self.DoGyro(x, y, applied))
                return
            if self[x, y].name == "helix":
                queue_task("postrotate", lambda: self.DoHelix(x, y, amt))
                return
            self.rotate_cell_raw(x, y, amt, side)

    def w_rotate_cell(self, x, y, amt, side=None):
        cell = self[x, y]
        if cell is None: return
        if side is not None and is_unbreakable(cell, "rotate", side): return

        total = cell.vars.get("wrot", 0) + amt
        applied = int(total / 2) * 2
        cell.vars["wrot"] = total - applied

        if applied != 0:
            self.rotate_cell(x, y, applied, side)

    def take_srot(self, cell, amt):
        total = cell.vars.get("srot", 0) + amt
        applied = int(total / 0.5) * 0.5
        cell.vars["srot"] = total - applied
        return applied

    def rotate_cell_raw(self, x, y, amt, side):
        cell = self[x, y]
        if cell is None: return
        if side is not None and is_unbreakable(cell, "rotate", side): return

        applied = self.take_srot(cell, amt)
        if applied != 0:
            self[x, y].direction += applied

    def redirect_cell(self, x, y, direction, side):
        if self[x, y] is not None:
            if is_unbreakable(self[x, y], "redirect", side): return
            self[x, y].direction = direction

    def disable_cell(self, x, y):
        cell = self[x, y]
        if cell is None: return
        if cell.name == "disablestorage": return
        if cell.effects.enabled: return
        if get_tag(cell.name, "cannot_disable"): return
        oldx = cell.oldx if cell.oldx is not None else x
        oldy = cell.oldy if cell.oldy is not None else y
        new_cell = Cell(
            cell.direction,
            "disablestorage",
            oldx=oldx,
            oldy=oldy,
            olddirection=cell.olddirection,
            effects=cell.effects.copy(),
            eaten=list(cell.eaten),
        )
        new_cell.storing = cell.copy()
        self[x, y] = new_cell

    def enable_cell(self, x, y):
        cell = self[x, y]
        if cell is None: return
        if cell.name == "disablestorage":
            self[x, y] = cell.storing_raw
        self[x, y].effects.enabled = True

    def eat_cell(self, x, y, tx, ty, force_animation=False):
        if (x, y) == (tx, ty):
            self.eaten.append((self[x, y].copy(), (tx, ty)))
            return
        if self[tx, ty] is not None:
            self[tx, ty].eaten.append(self[x, y].copy())
            return
        self.eaten.append((self[x, y].copy(), (tx, ty)))

    def direct_step_forward(self, x, y, direction=None):
        if direction is None:
            direction = to_vec(self[x, y].direction)

        f = deepcopy(direction)
        nx, ny = x + f.x, y + f.y
        return nx, ny, f, self[nx, ny]

    def step_forward(self, x, y, direction, traveler=None, passed=None):
        end_x, end_y = x, y
        start_x, start_y = x, y
        loops = 0
        crossed = []
        toll = 0
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
                elif cell.name == "acute curve diverger":
                    if side == 0: direction.rotate(-1.5)
                    elif side == 0.5: direction.rotate(1.5)
                    else: break
                elif cell.name == "obtuse curve diverger":
                    if side == 0: direction.rotate(-0.5)
                    elif side == 1.5: direction.rotate(0.5)
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
                elif cell.name == "coin diverger":
                    cost = coin_cost(cell)
                    if side % 1 != 0: break
                    if traveler is not None and toll + cost > traveler.vars.get("coins", 0): break
                    toll += cost
                    crossed.append(cell)
                else:
                    break
        if passed is not None:
            passed.extend(crossed)
        if cell is not None:
            to_copy = cell.copy()
            to_copy.direction += to_dir(direction) - cell.direction
            return end_x, end_y, direction, to_copy
        return end_x, end_y, direction, None

    def step_backward(self, x, y, direction, passed=None):
        result = self.step_forward(x, y, -direction, passed=passed)
        result = [i for i in result]
        result[2] = -result[2]
        result[3] = None

        if self[*result[0:2]] is not None:
            cell = self[*result[0:2]]
            to_copy = cell.copy()

            old_dir = to_dir(-result[2])
            new_dir = to_dir(direction)

            to_copy.direction = (to_copy.direction - new_dir + old_dir + 2)
            result[3] = to_copy

        return result

    @staticmethod
    def custom_force(push=False, pull=False):
        def wrapper(self, x, y, direction, flags=None):
            flags = flags or {}
            ok = True
            if push:
                ok = self.push_cell(x, y, Vector(direction.x, direction.y), dict(flags or {}))
                if not ok:
                    return False
            if pull:
                cx, cy, cdir, _ = self.step_backward(x, y, Vector(direction.x, direction.y))
                ok = self.pull_cell(cx, cy, cdir, dict(flags or {}))
            return ok

        return wrapper
    advance_cell = custom_force(push=True, pull=True)

    def crush_cell(self, x, y, direction, flags=None):
        flags = flags or {}
        ok = self.push_cell(x, y, direction, flags)
        if not ok:
            nx, ny, ndir, _ = self.step_forward(x, y, direction)
            if (c:=self[nx, ny]) and not is_unbreakable(c, "crush", to_side(c.direction, to_dir(ndir))):
                self.eat_cell(nx, ny, x, y)
                self[nx, ny] = None
        return ok

    def nudge_cell(self, x, y, direction, flags=None):
        flags = flags if flags is not None else {}
        flags["nudge"] = True
        if self[x, y] is not None:
            nx, ny, ndir, _ = self.step_forward(x, y, Vector(direction.x, direction.y), traveler=self[x, y])
            front = self[nx, ny]
            if front is not None and not nudge_into(front, to_side(front.direction, to_dir(ndir))):
                return False
        return self.push_cell(x, y, Vector(direction.x, direction.y), flags)

    def push_cell(self, x, y, direction, flags=None):
        orig_x, orig_y = x, y
        cx, cy = x, y
        flags = flags if flags is not None else {}
        flags["force"] = flags.get("force", 1)
        flags["replacecell"] = flags.get("replacecell", None)
        flags["first"] = True

        to_push = []
        pending_tolls = []
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
                nx, ny, sim_dir, _ = self.step_forward(sim_cx, sim_cy, sim_dir, traveler=cell)
                sim_cx, sim_cy = nx, ny
            else:
                break

        grid_snapshot = {}
        if flags.get("test", False):
            for px, py in path_coords:
                c = self[px, py]
                if c is not None:
                    grid_snapshot[(px, py)] = c.copy()

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
            if flags.get("toll"):
                pending_tolls.append((cell, flags["toll"]))
            lastx, lasty = oldx, oldy
            flags["first"] = False

        def restore_snapshot():
            if flags.get("test", False):
                for px, py in path_coords:
                    self[px, py] = None
                for (px, py), cell in grid_snapshot.items():
                    self[px, py] = cell

        if not success:
            restore_snapshot()
            run_queue("postpush")
            return False

        if not flags.get("test", False):
            for c, amount in pending_tolls:
                c.vars["coins"] = c.vars.get("coins", 0) - amount
            for px, py, pcx, pcy in reversed(to_push):
                if self[px, py] is None: continue
                self[pcx, pcy] = self[px, py]
                self[px, py] = None

            if self[orig_x, orig_y] is None:
                self[orig_x, orig_y] = flags["replacecell"]
            run_queue("postpush")
        else:
            restore_snapshot()

        return True

    def handle_push(self, x, y, direction, flags):
        cell = self[x, y]
        if cell is None:
            return x, y, direction, flags, False

        old_direction = Vector(direction.x, direction.y)
        crossed = []
        nx, ny, direction, _ = self.step_forward(x, y, direction, traveler=cell, passed=crossed)
        flags["toll"] = total_toll(crossed)
        ddir = to_dir(direction)
        side = to_side(cell.direction, ddir)
        front_cell = self[nx, ny]

        lastpos = flags["lastpos"]
        if lastpos == (None, None):
            lastpos = None

        success = True

        if is_unbreakable(cell, "push", side):
            flags["force"] = 0

        if cell.name == "slide":
            if side % 2 != 0:
                flags["force"] = 0
        elif cell.name == "two directional":
            if side not in [0, 1]:
                flags["force"] = 0
        elif cell.name == "three directional":
            if side == 2:
                flags["force"] = 0
        elif cell.name == "random push":
            if random.random() > cell.properties["Numerator"]/cell.properties["Denominator"]:
                flags["force"] = 0
        elif cell.name == "one directional":
            if side != 0:
                flags["force"] = 0
        elif cell.name == "zero directional":
            flags["force"] = 0
        elif cell.name == "omega trash":
            if lastpos is not None:
                self.eat_cell(*lastpos, x, y)
                self[*lastpos] = None
            else:
                flags["replacecell"] = None
            flags["break"] = True
            play_sound("destroy")
            raise_random_error()
        elif cell.name == "weight":
            flags["force"] -= 1
        elif cell.name == "adjustable weight":
            flags["force"] -= cell.properties["Numerator"]/cell.properties["Denominator"]
        elif cell.name == "anti weight":
            flags["force"] += 1
        elif cell.name == "nano weight":
            if flags.get("first", False): flags["force"] = 0
        elif cell.name == "anti nano weight":
            if not flags.get("first", False): flags["force"] = 0
        elif cell.name == "bias":
            if side == 2:
                flags["force"] += 1
            elif side == 0:
                flags["force"] -= 1
        elif cell.name == "gold":
            if not math.isclose(side % 1, 0, abs_tol=1e-9):
                flags["force"] = 0
        elif cell.name == "lead":
            if math.isclose(side % 1, 0, abs_tol=1e-9):
                flags["force"] = 0
        elif cell.name == "inertia":
            cell.vars["momentum"] = {"direction": direction, "force": flags["force"]}

        if cell.name in ("coin", "anti coin", "chocolate coin"):
            amount = (1 if cell.name == "coin" else (-1 if cell.name == "anti coin" else 0))
            if lastpos is not None and self[*lastpos] is not None:
                self[*lastpos].vars["coins"] += amount
                self[x, y] = None
                flags["break"] = True
            elif flags["replacecell"] is not None:
                flags["replacecell"].vars["coins"] += amount
                self[x, y] = None
                flags["break"] = True

        if cell.name == "storage":
            old_storing = self[x, y].storing
            if lastpos is not None:
                self[x, y].storing = self[*lastpos].copy()
                self[*lastpos] = None
            else:
                self[x, y].storing = flags["replacecell"].copy() if flags["replacecell"] is not None else None
                flags["replacecell"] = None
            if old_storing is not None:
                old_storing.oldx, old_storing.oldy = (x, y)
                self.push_cell(nx, ny, direction, {"replacecell": old_storing})
            flags["break"] = True

        if cell.name in ["trash", "jump trash", "attack trash", "bulk trash"]:
            if lastpos is not None:
                self.eat_cell(*lastpos, x, y)
                self[*lastpos] = None
            else:
                flags["replacecell"] = None
            if cell.name in ["jump trash", "attack trash"]:
                v = dict(flags)
                v.pop("nudge", None)
                jump_dir = {
                    "jump trash": direction,
                    "attack trash": -direction,
                }[cell.name]
                v["ignore_first"] = True
                queue_task("postpush", lambda: self.push_cell(x, y, jump_dir, v))
            if cell.name == "bulk trash":
                success = False
            else:
                flags["break"] = True
            play_sound("destroy")

        elif cell.name == "squish trash":
            v = deepcopy(flags)
            v["test"] = True
            v["ignore_first"] = True
            if not self.push_cell(x, y, direction, v):
                if lastpos is not None:
                    self.eat_cell(*lastpos, x, y)
                    self[*lastpos] = None
                else:
                    flags["replacecell"] = None
                flags["break"] = True
                play_sound("destroy")

        elif cell.name == "lichen":
            self.eat_cell(x, y, x, y)
            self[x, y] = None
            flags["break"] = True

            up_dir = (cell.direction + 1)
            down_dir = (cell.direction - 1)

            upcopy = cell.copy()
            downcopy = cell.copy()
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

        elif cell.name in ["enemy", "bulk enemy", "bread"]:
            can_collide = True
            if cell.name == "bread":
                if cell.properties["Numerator"]/cell.properties["Denominator"] > flags["force"]:
                    flags["force"] = 0
                    can_collide = False
            if can_collide:
                self.eat_cell(x, y, x, y)
                self[x, y] = None
                if lastpos is not None:
                    self.eat_cell(*lastpos, x, y)
                    self[*lastpos] = None
                else:
                    flags["replacecell"] = None
                if cell.name == "bulk enemy":
                    success = False
                else:
                    flags["break"] = True
                play_sound("destroy")

        elif cell.name == "squish enemy":
            v = deepcopy(flags)
            v["test"] = True
            v["ignore_first"] = True
            if not self.push_cell(x, y, direction, v):
                self.eat_cell(x, y, x, y)
                self[x, y] = None
                if lastpos is not None:
                    self.eat_cell(*lastpos, x, y)
                    self[*lastpos] = None
                else:
                    flags["replacecell"] = None
                flags["break"] = True
                play_sound("destroy")

        if front_cell is not None:
            if front_cell.name in ["mover", "leaper", "hydra", "skidhi 90", "player mover", "advancer", "crusher",
                                   "purple mover"] and not front_cell.effects.frozen:
                if front_cell.direction == ddir:
                    flags["force"] += 1
                elif front_cell.direction == (ddir + 2) % 4:
                    flags["force"] -= 1
            if front_cell.name == "slow mover" and not front_cell.effects.frozen and self.ticks % 2 == 0:
                if front_cell.direction == ddir:
                    flags["force"] += 1
                elif front_cell.direction == (ddir + 2) % 4:
                    flags["force"] -= 1

        if flags["force"] <= 0:
            success = False

        if success and not flags.get("break", False) and self[x, y] is not None:
            old_dir = to_dir(old_direction)
            new_dir = to_dir(direction)
            self[x, y].direction = (self[x, y].direction + new_dir - old_dir)

        return nx, ny, direction, flags, success

    def pull_cell(self, x, y, direction, flags=None):
        orig_x, orig_y = x, y
        cx, cy = x, y
        flags = flags if flags is not None else {}
        flags["replacecell"] = flags.get("replacecell", None)
        flags["force"] = flags.get("force", 1)
        flags["first"] = True
        flags["tolls"] = []
        direction = Vector(direction.x, direction.y)

        to_pull = []
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
                cx, cy, direction, flags, success = self.handle_pull(cx, cy, direction, flags)
                if not success:
                    break
                if lastx is None:
                    destx, desty = flags["frontpos"]
                else:
                    destx, desty = lastx, lasty
                to_pull.append((oldx, oldy, destx, desty))
                lastx, lasty = oldx, oldy
                if flags.get("break", False):
                    break
            else:
                break
            flags["first"] = False

        if not success or not to_pull:
            return False

        if not flags.get("test", False):
            for c, amount in flags["tolls"]:
                c.vars["coins"] = c.vars.get("coins", 0) - amount
            for px, py, pcx, pcy in to_pull:
                if self[px, py] is None: continue
                self[pcx, pcy] = self[px, py]
                self[px, py] = None

        run_queue("postpull")

        return True

    def handle_pull(self, x, y, direction, flags):
        cell = self[x, y]
        if cell is None:
            return x, y, direction, flags, False

        front_crossed = []
        back_crossed = []
        nx, ny, front_direction, front_cell = self.step_forward(x, y, Vector(direction.x, direction.y), traveler=cell, passed=front_crossed)
        bx, by, direction, _ = self.step_backward(x, y, Vector(direction.x, direction.y), passed=back_crossed)
        back_cell = self[bx, by]
        side = to_side(cell.direction, to_dir(direction))

        lastpos = flags["lastpos"]
        if lastpos == (None, None):
            lastpos = None

        success = True
        flags["end"] = False

        tolls = flags.setdefault("tolls", [])
        if lastpos is None and front_crossed:
            tolls.append((cell, total_toll(front_crossed)))
        if back_cell is not None and back_crossed:
            back_toll = total_toll(back_crossed)
            if back_toll > back_cell.vars.get("coins", 0):
                flags["break"] = True
            else:
                tolls.append((back_cell, back_toll))

        if lastpos is None:
            flags["frontpos"] = (nx, ny)
            flags["frontdir"] = front_direction
            front_cell = self[nx, ny]
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                success = False
            elif front_cell is not None:
                if front_cell.name not in []:
                    success = False
                elif not flags.get("test", False):
                    if front_cell.name == "enemy":
                        self.eat_cell(nx, ny, nx, ny)
                        self[nx, ny] = None
                    self.eat_cell(x, y, nx, ny)
                    self[x, y] = None
                    play_sound("destroy")
                    if front_cell.name == "jump trash":
                        queue_task("postpull", lambda: self.push_cell(nx, ny, front_direction, {"ignore_first": True}))
                    if front_cell.name == "attack trash":
                        queue_task("postpull", lambda: self.push_cell(nx, ny, -front_direction, {"ignore_first": True}))
                    if "bulk" in front_cell.name:
                        success = False

        if is_unbreakable(cell, "pull", side):
            flags["force"] = 0

        if cell.name == "slide":
            if side % 2 != 0:
                flags["force"] = 0
        elif cell.name == "two directional":
            if side not in [0, 1]:
                flags["force"] = 0
        elif cell.name == "three directional":
            if side == 2:
                flags["force"] = 0
        elif cell.name == "random push":
            if random.random() < 0.5:
                flags["force"] = 0
        elif cell.name == "one directional":
            if side != 0:
                flags["force"] = 0
        elif cell.name == "zero directional":
            flags["force"] = 0

        elif cell.name == "weight":
            flags["force"] -= 1
        elif cell.name == "adjustable weight":
            flags["force"] -= cell.properties["Numerator"] / cell.properties["Denominator"]
        elif cell.name == "anti weight":
            flags["force"] += 1
        elif cell.name == "nano weight":
            if flags.get("first", False): flags["force"] = 0
        elif cell.name == "anti nano weight":
            if not flags.get("first", False): flags["force"] = 0
        elif cell.name == "bias":
            if side == 2:
                flags["force"] += 1
            elif side == 0:
                flags["force"] -= 1
        elif cell.name == "gold":
            if not math.isclose(side % 1, 0, abs_tol=1e-9):
                flags["force"] = 0
        elif cell.name == "lead":
            if math.isclose(side % 1, 0, abs_tol=1e-9):
                flags["force"] = 0

        if back_cell is not None:
            if back_cell.name in ["puller", "advancer"] and not cell.effects.frozen:
                if back_cell.direction == cell.direction:
                    flags["force"] += 1
                if back_cell.direction == (cell.direction+2)%4:
                    flags["force"] -= 1

        if flags["force"] <= 0: success = False

        return bx, by, direction, flags, success

    def swap_cells(self, x1, y1, x2, y2, side1, side2):
        a, b = self[x1, y1], self[x2, y2]

        a_copy = a.copy() if a is not None else None
        b_copy = b.copy() if b is not None else None

        if a_copy and is_unbreakable(a_copy, "swap", side1): return False
        if b_copy and is_unbreakable(b_copy, "swap", side2): return False

        self[x1, y1] = b_copy
        self[x2, y2] = a_copy
        return True

    def DoMirror(self, x, y, cell):
        if cell.name == "mirror":
            fx, fy, _, _ = self.direct_step_forward(x, y, to_vec(cell.direction))
            bx, by, _, _ = self.direct_step_forward(x, y, to_vec((cell.direction + 2)))

            side1 = to_side(cell.direction, to_dir(to_vec(cell.direction)))
            side2 = to_side(cell.direction, to_dir(to_vec((cell.direction + 2))))

            self.swap_cells(fx, fy, bx, by, side1, side2)

    def DoInertia(self, x, y, cell):
        if cell.name == "inertia":
            if (momentum:=cell.vars.get("momentum", None)) is not None:
                ok = self.push_cell(x, y, momentum["direction"], {"force": momentum["force"]})
                if not ok:
                    cell.vars["momentum"] = None

    def DoNudger(self, x, y, cell):
        if cell.name == "nudger":
            self.nudge_cell(x, y, to_vec(cell.direction))

    def DoMover(self, x, y, cell):
        if cell.name in ["mover", "skidhi 90", "player mover"]:
            self.push_cell(x, y, to_vec(cell.direction))
        elif cell.name == "leaper":
            self.push_cell(x, y, to_vec(cell.direction) * 2)
        elif cell.name == "slow mover":
            if self.ticks % 2 == 0:
                self.push_cell(x, y, to_vec(cell.direction))
        elif cell.name == "bird":
            if cell.direction % 2 != 0:
                ok = self.push_cell(x, y, to_vec(cell.direction))
                if not ok:
                    self.rotate_cell(x, y, 1)
                return
            if self.ticks % 2 == 1:
                ok = self.push_cell(x, y, to_vec(cell.direction))
                if not ok:
                    self.rotate_cell(x, y, 1)
            if self.ticks % 4 == 0:
                self.push_cell(x, y, to_vec(1))
            if self.ticks % 4 == 2:
                self.push_cell(x, y, to_vec(3))
        elif cell.name == "bee":
            if cell.direction % 2 != 0:
                ok = self.push_cell(x, y, to_vec(cell.direction))
                if not ok:
                    self.rotate_cell(x, y, 1)
                return
            if self.ticks % 2 == 0:
                if cell.direction == 0:
                    self.push_cell(x, y, to_vec(0.5))
                else:
                    self.push_cell(x, y, to_vec(1.5))
            if self.ticks % 2 == 1:
                if cell.direction == 0:
                    self.push_cell(x, y, to_vec(3.5))
                else:
                    self.push_cell(x, y, to_vec(2.5))
        elif cell.name == "hydra":
            if not self.push_cell(x, y, to_vec(cell.direction)):
                up_dir = (cell.direction + 1)
                down_dir = (cell.direction - 1)

                upcopy = cell.copy()
                downcopy = cell.copy()
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
        elif cell.name == "crusher":
            self.crush_cell(x, y, to_vec(cell.direction))
        elif cell.name == "purple mover":
            ok = self.push_cell(x, y, to_vec(cell.direction))
            if not ok:
                self.eat_cell(x, y, x, y)
                self[x, y] = None

    def get_player_input(self):
        if not player_input:
            return None
        return {
            "up": Vector(0, -1),
            "down": Vector(0, 1),
            "left": Vector(-1, 0),
            "right": Vector(1, 0),
        }.get(player_input[-1])

    def DoPlayer(self, x, y, cell):
        vec = self.get_player_input()
        if vec is not None:
            if cell.name == "player":
                self.push_cell(x, y, vec)
            if cell.name == "anti player":
                self.push_cell(x, y, -vec)
            if cell.name == "pull player":
                self.pull_cell(x, y, vec)

    def DoSteer(self, x, y, cell):
        vec = self.get_player_input()
        if vec is not None:
            cell.direction = to_dir(vec)
        cell.noupdate = True

    def DoRepulsor(self, x, y, cell):
        if cell.name == "repulsor":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if c is None: continue
                if is_unbreakable(c, "repulse", to_side(c.direction, k)): continue
                self.push_cell(i, j, to_vec(k))

    def DoImpulsor(self, x, y, cell):
        if cell.name == "impulsor":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y, dist=2).items():
                if c is None: continue
                if is_unbreakable(c, "impulse", to_side(c.direction, k)): continue
                self.pull_cell(i, j, -to_vec(k))

    def DoIntaker(self, x, y, cell):
        if cell.name == "intaker":
            cx, cy, cdir, _ = self.step_forward(x, y, to_vec(cell.direction))
            self.pull_cell(cx, cy, -cdir)

    def DoPuller(self, x, y, cell):
        if cell.name == "puller":
            self.pull_cell(x, y, to_vec(cell.direction))
        if cell.name == "advancer":
            self.advance_cell(x, y, to_vec(cell.direction))
        if cell.name == "leaper puller":
            self.pull_cell(x, y, to_vec(cell.direction)*2)
        if cell.name == "slow puller":
            if self.ticks % 2 == 0:
                self.pull_cell(x, y, to_vec(cell.direction))

    def DoRotator(self, x, y, cell):
        if cell.name == "adjustable rotator":
            current_rot = cell.properties["Numerator"]/cell.properties["Denominator"]
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_neighbors
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                force_dir = to_dir(Vector(i - x, j - y))
                self.rotate_cell(i, j, current_rot, to_side(c.direction, force_dir))
            return
        if "ana" in cell.name or "kata" in cell.name:
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_neighbors
            current_w_rot = next((val for key, val in {"ana": 1, "kata": -1}.items() if key in cell.name), 0)
            if "half" in cell.name:
                current_w_rot /= 2
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                force_dir = to_dir(Vector(i - x, j - y))
                self.w_rotate_cell(i, j, current_w_rot, to_side(c.direction, force_dir))
            return
        rotation = next(
            (val for key, val in {"22.5": 22.5, "45": 45, "90": 90, "135": 135, "180": 180, "360": 360}.items() if key in cell.name),
            0) / 90

        if "skidhi" in cell.name:
            fx, fy, _, f = self.direct_step_forward(x, y, to_vec(cell.direction))
            bx, by, _, b = self.direct_step_forward(x, y, to_vec((cell.direction + 2) % 4))

            if "random" in cell.name:
                r_f = random.choice([rotation, -rotation])
                r_b = random.choice([rotation, -rotation])
            else:
                r_f = rotation
                r_b = -rotation

            if "ccw" in cell.name:
                r_f = -r_f
                r_b = -r_b

            if f is not None: self.rotate_cell(fx, fy, r_f, to_side(f.direction, cell.direction))
            if b is not None: self.rotate_cell(bx, by, r_b, to_side(b.direction, (cell.direction + 2) % 4))
            cell.noupdate = True
            return

        if "ccw" in cell.name:
            rotation = -rotation

        neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
        for k, (i, j, c) in neighbor_func(x, y).items():
            if not c: continue
            if "random" in cell.name:
                current_rot = random.choice([rotation, -rotation])
            else:
                current_rot = rotation

            force_dir = to_dir(Vector(i - x, j - y))
            self.rotate_cell(i, j, current_rot, to_side(c.direction, force_dir))

    def DoGyro(self, x, y, amt):
        self.do_basic_gear(x, y, amt)

    def DoHelix(self, x, y, amt):
        if self[x, y] is None: return
        self.push_cell(x, y, to_vec(self[x, y].direction))

    def DoSuperGenerator(self, x, y, cell):
        to_generate = []
        cx, cy = x, y
        front_outputs = {
            "cw super generator": 1,
            "ccw super generator": -1,
        }
        front_output = front_outputs.get(cell.name, 0)
        fx, fy, k, _ = self.step_forward(x, y, to_vec(cell.direction+front_output))
        while True:
            cx, cy, j, cc = self.step_backward(cx, cy, to_vec(cell.direction))
            if cc is None:
                break
            else:
                cc.direction += front_output
                cc.direction %= 4
                side = to_side(cc.direction, to_dir(j))
                if gen_as(cc, side) is None:
                    cc = None
                    to_generate.append((Cell(0, "supergenstorage", v={"storing": cc}), side))
                else:
                    cc.name = gen_as(cc, side)
                    to_generate.append((Cell((cc.direction+front_output)%4, "supergenstorage", v={"storing": cc}), side))

        for c, side in to_generate:
            self.push_cell(fx, fy, k, {"replacecell": c})

        cx, cy = x, y
        i = 0
        while True:
            cx, cy, _, cc = self.step_forward(cx, cy, to_vec(cell.direction+front_output))
            if cc is None:
                break
            elif cc.name != "supergenstorage":
                break
            else:
                self[cx, cy] = self[cx, cy].storing_raw
            i += 1

    def DoGenerator(self, x, y, cell):
        front_outputs = {
            "cw generator": 1,
            "ccw generator": -1,
        }
        if cell.name == "single cell generator" and cell.vars.get("full", False): return
        front_output = front_outputs.get(cell.name, 0)
        bx, by, j, copy = self.step_backward(x, y, to_vec(cell.direction))
        fx, fy, k, _ = self.step_forward(x, y, to_vec((cell.direction + front_output)))
        if copy is None: return
        if copy.name == "ghost": return
        copy.direction += front_output
        g_a = gen_as(copy, to_side(copy.direction, to_dir(j)))
        if g_a is None:
            copy = None
        else:
            copy.name = g_a
        if self.push_cell(fx, fy, to_vec((cell.direction + front_output)), {"replacecell": copy}):
            if cell.name == "single cell generator":
                cell.vars["full"] = True

    def DoRedirector(self, x, y, cell):
        neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
        for k, (i, j, c) in neighbor_func(x, y).items():
            if not c: continue
            self.redirect_cell(i, j, cell.direction, to_side(c.direction, k))

    def DoThawer(self, x, y, cell):
        if cell.name == "thawer":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.thaw_cell(i, j, to_side(c.direction, k))
        elif cell.name == "summer":
            for nx, ny, ncell in self:
                if not ncell: continue
                self.thaw_cell(nx, ny)

    def DoFreezer(self, x, y, cell):
        if cell.name == "freezer":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.freeze_cell(i, j, to_side(c.direction, k))
        elif cell.name == "winter":
            for nx, ny, ncell in self:
                if not ncell: continue
                self.freeze_cell(nx, ny)

    def DoElectrocutor(self, x, y, cell):
        if cell.name == "electrocutor":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.electrocute_cell(i, j, cell.properties["Numerator"]/cell.properties["Denominator"], to_side(c.direction, k))

    def DoCopper(self, x, y, cell):
        if cell.name == "copper":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.copper_cell(i, j, to_side(c.direction, k))

    def DoDisabler(self, x, y, cell):
        if cell.name == "disabler":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.disable_cell(i, j)

    def DoEnabler(self, x, y, cell):
        if cell.name == "enabler":
            neighbor_func = self.get_neighbors if cell.direction % 1 == 0 else self.get_diagonals
            for k, (i, j, c) in neighbor_func(x, y).items():
                if not c: continue
                self.enable_cell(i, j)

    def do_basic_gear(self, gear_x, gear_y, rotation):
        neighbors = self.get_surrounding(gear_x, gear_y)
        gears = ["cw gear", "ccw gear", "slow cw gear", "slow ccw gear", "fast cw gear", "fast ccw gear", "jam"]

        for i, (nx, ny, c) in neighbors.items():
            if c is None: continue
            if c.name in gears:
                return
            if is_unbreakable(c, "gear", to_side(c.direction, i)):
                return

        ring = [i for i, (_, _, c) in neighbors.items() if c is None or c.name != "jelly"]
        steps = round(rotation * 2)

        self.rotate_cell_raw(gear_x, gear_y, rotation, 0)

        for i in ring:
            nx, ny, _ = neighbors[i]
            self[nx, ny] = None

        for idx, i in enumerate(ring):
            cell = neighbors[i][2]
            if cell is None: continue
            tx, ty, _ = neighbors[ring[(idx + steps) % len(ring)]]
            to_copy = cell.copy()
            to_copy.anim_center = (gear_x, gear_y)
            self[tx, ty] = to_copy
            self.rotate_cell(tx, ty, rotation, to_side(to_copy.direction, i))

    def DoGear(self, x, y, cell):
        rotation = (-1 if "ccw" in cell.name else (1 if "cw" in cell.name else (2 if "180" in cell.name else 0)))
        if "slow" in cell.name:
            rotation *= 0.5
        if "fast" in cell.name:
            rotation *= 1.5
        self.do_basic_gear(x, y, rotation)

grid = Grid(grid_width, grid_height)