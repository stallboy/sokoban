import os
import configparser
import pyglet

S_WALL = 0
S_SPACE = 1
S_OUTSIZE = 2
S_BOX = 3
S_BOX_AT_DEST = 4
S_DEST = 5
S_MAN = 6
S_MAN_AT_DEST = 7

ACTIONS = {
    'l': (-1, 0),
    'r': (1, 0),
    'd': (0, -1),
    'u': (0, 1)
}


def is_dest(c):
    return c in [S_DEST, S_MAN_AT_DEST, S_BOX_AT_DEST]


def is_static_block(c):
    return c in [S_WALL, S_OUTSIZE]


class SokobanLoader(object):

    def __init__(self):
        pyglet.resource.path = ['res']
        pyglet.resource.reindex()

    def load_maps(self):
        sign_to_index = {'+': S_WALL,
                         ' ': S_SPACE,
                         '-': S_OUTSIZE,
                         '#': S_BOX,
                         '@': S_BOX_AT_DEST,
                         '.': S_DEST,
                         '^': S_MAN,
                         '$': S_MAN_AT_DEST}

        maps = []
        current_map = []
        MBegin = False
        with pyglet.resource.file('map.txt', 'r') as sf:
            for line in sf.readlines():
                if not MBegin and line.startswith("M"):
                    MBegin = True
                    continue
                if not MBegin:
                    continue

                if line.startswith("M") and current_map:
                    maps.append(current_map)
                    current_map = []
                elif len(line) > 0 and line[0] in sign_to_index:
                    current_map.insert(0, [sign_to_index[s] for s in line.strip()])

        maps.append(current_map)

        states = []
        for map in maps:
            man = None
            for y, line in enumerate(map):
                for x, idx in enumerate(line):
                    if idx == S_MAN or idx == S_MAN_AT_DEST:
                        if man:
                            raise Exception("multiple man")
                        else:
                            man = (x, y)
            if man:
                states.append(SokobanState(map, man))
            else:
                raise Exception("man not found")
        return states

    def load_tiles(self):
        tile = pyglet.resource.image("tile.png")
        tile_seq = pyglet.image.ImageGrid(tile, 1, 8)
        tiles = pyglet.image.TextureGrid(tile_seq)
        return tiles


class SokobanSettings(object):
    def __init__(self):
        dir = pyglet.resource.get_settings_path('sokoban')
        if not os.path.exists(dir):
            os.makedirs(dir)

        self.setting_fn = os.path.join(dir, 'settings.ini')
        self.config = configparser.ConfigParser()
        if os.path.exists(self.setting_fn):
            with open(self.setting_fn, 'r') as f:
                self.config.read_file(f)
        self.solved = {int(sec): (self.config[sec]['actions'], int(self.config[sec]['explored']))
                       for sec in self.config.sections()}

    def get(self, option, fallback=''):
        return self.config.get('DEFAULT', option, fallback=fallback)

    def getint(self, option, fallback=0):
        return self.config.getint('DEFAULT', option, fallback=fallback)

    def set(self, option, value):
        self.config.set('DEFAULT', option, str(value))
        self.save()

    def set_solved(self, solution):
        self.solved = solution
        for sec in self.config.sections():
            del self.config[sec]
        keys = list(solution.keys())
        keys.sort()  # 排序后再保存
        for key in keys:
            actions, explored = solution[key]
            self.config[str(key)] = {
                'explored': str(explored),
                'actions': actions
            }

        self.save()

    def save(self):
        with open(self.setting_fn, 'w') as f:
            self.config.write(f)


class SokobanState(object):
    def __init__(self, layout, man_pos):
        self.layout = [list(line) for line in layout]  # deep copy
        self.man_pos = man_pos

    def __eq__(self, other):
        return other and self.man_pos == other.man_pos and self.layout == other.layout

    def __hash__(self):
        return hash((tuple([tuple(line) for line in self.layout]), self.man_pos))

    def has_space(self, x, y):
        s = self.layout[y][x]
        return s == S_SPACE or s == S_DEST

    def has_box(self, x, y):
        s = self.layout[y][x]
        return s == S_BOX or s == S_BOX_AT_DEST

    def enter_man(self, x, y):
        self.man_pos = (x, y)
        if is_dest(self.layout[y][x]):
            self.layout[y][x] = S_MAN_AT_DEST
        else:
            self.layout[y][x] = S_MAN

    def leave_man(self, x, y):
        if self.layout[y][x] == S_MAN:
            self.layout[y][x] = S_SPACE
        elif self.layout[y][x] == S_MAN_AT_DEST:
            self.layout[y][x] = S_DEST

    def enter_box(self, x, y):
        if is_dest(self.layout[y][x]):
            self.layout[y][x] = S_BOX_AT_DEST
        else:
            self.layout[y][x] = S_BOX

    def copy(self):
        return SokobanState(self.layout, self.man_pos)

    def try_move(self, dx, dy):
        nxt, _ = self.try_move2(dx, dy)
        return nxt

    def try_move2(self, dx, dy):
        x, y = self.man_pos
        nx = x + dx
        ny = y + dy
        nnx = nx + dx
        nny = ny + dy

        if self.has_space(nx, ny):
            nxt = self.copy()
            nxt.enter_man(nx, ny)
            nxt.leave_man(x, y)
            return nxt, None
        elif self.has_box(nx, ny) and self.has_space(nnx, nny):
            nxt = self.copy()
            nxt.enter_box(nnx, nny)
            nxt.enter_man(nx, ny)
            nxt.leave_man(x, y)
            return nxt, (nnx, nny)
        else:
            return None, None

    def is_finished(self):
        for line in self.layout:
            for s in line:
                if s in [S_DEST, S_MAN_AT_DEST]:
                    return False
        return True
