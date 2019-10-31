import multiprocessing
import pyglet
import pyglet.window.key as key
import solver
import space

KEY_TO_ACTIONS = {
    key.LEFT: 'l',
    key.RIGHT: 'r',
    key.DOWN: 'd',
    key.UP: 'u'
}

STEP_NONE = 0
STEP_THINK = 1
STEP_ACT = 2


def _load_tiles():
    tile = pyglet.resource.image("tile.png")
    tile_seq = pyglet.image.ImageGrid(tile, 1, 8)
    return pyglet.image.TextureGrid(tile_seq)


class SokobanGame(object):

    def __init__(self):
        self.layouts = space.load_layouts()
        self.config = space.load_settings()
        self.solved = solver.read_solution(self.config)
        print("{0}关未解决".format(len(self.layouts) - len(self.solved)))

        self.tiles = _load_tiles()
        self.tile_width = self.tiles[0].width

        self.window = pyglet.window.Window()
        self.window.event(self.on_draw)
        self.window.event(self.on_key_press)
        self.cur_level = None
        self.cur_layout = None
        self.state_history = []

        self.step_state = STEP_NONE
        self.solver = None
        self.plan_explored = 0
        self.planned_actions = []
        self.planned_actions_idx = 0
        pyglet.clock.schedule_interval(self.step, 0.1)
        self.label = pyglet.text.Label('', font_size=16, x=10, y=10)

        self.start_level(self.config.getint('DEFAULT', 'last_open'))

    def start_level(self, level):
        if level < 0:
            level = len(self.layouts) - 1
        elif level >= len(self.layouts):
            level = 0

        if self.cur_level == level:
            return

        self.config.set('DEFAULT', 'last_open', str(level))
        space.save_settings(self.config)

        self.cur_level = level
        self.cur_layout = self.layouts[level]
        self.window.set_caption("level {0}".format(self.cur_level))

        self.stop_plan()
        self.start_state = space.SokobanState(self.cur_layout)
        self.state = self.start_state

        self.state_history = []

        layout_height = len(self.cur_layout) * self.tile_width
        layout_width = len(self.cur_layout[0]) * self.tile_width
        self.window.set_minimum_size(layout_width, layout_height)

        start_x = (self.window.width - layout_width) / 2
        start_y = (self.window.height - layout_height) / 2

        self.batch = pyglet.graphics.Batch()
        self.all_sprites = []
        for y, line in enumerate(self.state.layout):
            line_sprite = []
            for x, idx in enumerate(line):
                sprite = pyglet.sprite.Sprite(self.tiles[idx], x=x * self.tile_width + start_x,
                                              y=y * self.tile_width + start_y,
                                              batch=self.batch)
                line_sprite.append(sprite)

            self.all_sprites.append(line_sprite)

        self.batch.invalidate()

    def act(self, action):
        dx, dy = space.ACTIONS[action]
        nxt = self.state.try_move(dx, dy)
        if nxt is None:
            return

        self.state_history.append(self.state)
        self._set_state(nxt)

    def _set_state(self, state):
        self.state = state
        for y, line in enumerate(self.state.layout):
            line_sprite = self.all_sprites[y]
            for x, idx in enumerate(line):
                sprite = line_sprite[x]
                sprite.image = self.tiles[idx]
        self.batch.invalidate()

    def undo(self):
        if self.state_history:
            last_state = self.state_history.pop()
            self._set_state(last_state)

    def on_key_press(self, symbol, modifiers):
        if symbol in KEY_TO_ACTIONS:
            self.stop_plan()
            self.act(KEY_TO_ACTIONS[symbol])

        elif symbol == key.B:
            self.stop_plan()
            self.undo()

        elif symbol in [key.PAGEDOWN, key.PAGEUP]:
            dir = symbol == key.PAGEDOWN and 1 or -1
            ctrl = modifiers & key.MOD_CTRL != 0
            if ctrl:
                nxt = self.next_unsolved_level(dir)
            else:
                nxt = self.cur_level + dir
            self.start_level(nxt)

        elif symbol == key.HOME:
            ctrl = modifiers & key.MOD_CTRL != 0
            if not ctrl and self.cur_level in self.solved:
                actions, explored = self.solved[self.cur_level]
                self.start_act(actions, explored)
            else:
                self.start_plan()

        elif symbol == key.END:
            self.stop_plan()

    def next_unsolved_level(self, dir):
        c = self.cur_level
        while True:
            c += dir
            if c == self.cur_level:
                return c

            if c < 0:
                c = len(self.layouts) - 1
            elif c >= len(self.layouts):
                c = 0

            if c not in self.solved:
                return c

    def step(self, dt):
        if self.step_state == STEP_NONE:
            return

        if self.step_state == STEP_THINK:
            progress = None
            while self.step_state == STEP_THINK:
                info = self.solver.poll()
                if info is None:
                    break
                typ, inf = info
                if typ == 0:
                    progress = inf
                elif typ == 1:
                    action_list, explored = inf
                    action_str = "".join(action_list)
                    if self.state == self.start_state:
                        self.solved[self.cur_level] = (action_str, explored)
                        solver.save_solution(self.config, self.solved)
                        space.save_settings(self.config)

                    self.start_act(action_str, explored)
                    progress = None
                    print(self.cur_level, "solution:", explored, action_str)

            if progress:
                explored, frontier = progress
                self.label.text = 'THINKING explored={0}'.format(explored)

        if self.step_state == STEP_ACT:
            if self.planned_actions_idx < len(self.planned_actions):
                action = self.planned_actions[self.planned_actions_idx]
                self.act(action)
                self.planned_actions_idx += 1
            else:
                self.stop_plan()

    def start_plan(self):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.solver = ConcurrentSolver(self.state)
        self.solver.start()
        self.step_state = STEP_THINK

    def start_act(self, actions, explored):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.step_state = STEP_ACT
        self.label.text = 'ACTING explored={0}'.format(explored)
        self.plan_explored = explored
        self.planned_actions = actions
        self.planned_actions_idx = 0

    def stop_plan(self):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.step_state = STEP_NONE
        if self.cur_level in self.solved:
            actions, explored = self.solved[self.cur_level]
            self.label.text = 'WAITING explored={0}'.format(explored)
        else:
            self.label.text = 'WAITING'

    def on_draw(self):
        self.window.clear()
        self.batch.draw()
        self.label.draw()

    def run(self):
        pyglet.app.run()


class ConcurrentSolver:
    def __init__(self, startState):
        self.startState = startState
        self.queue = multiprocessing.Queue()
        self.problem = solver.SokobanSearchProblem(startState, self._progress)
        self.process = multiprocessing.Process(target=self._solve)

    def start(self):
        self.process.start()

    def end(self):
        self.process.terminate()

    def poll(self):
        try:
            return self.queue.get_nowait()
        except:
            return None

    def _progress(self, exploredSize, frontierSize):
        if exploredSize % 100 == 0:
            self.queue.put([0, (exploredSize, frontierSize)])

    def _solve(self):
        actions, exploredSize = self.problem.solve()
        self.queue.put([1, (actions, exploredSize)])


def main():
    game = SokobanGame()
    game.run()


if __name__ == '__main__':
    main()
