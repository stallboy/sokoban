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

PLAYMODE_STEP_PLAY = 0
PLAYMODE_STEP_WIN = 1


class SokobanGame(object):
    def __init__(self):
        loader = space.SokobanLoader()
        self.layouts = loader.load_maps()
        self.tiles = loader.load_tiles_sep()
        self.settings = space.SokobanSettings()
        self.solved = self.settings.solved
        print("{0}关未解决".format(len(self.layouts) - len(self.solved)))
        self.tile_width = self.tiles[0].width

        self.window = pyglet.window.Window(fullscreen=True) # width=1500, height=900,
        self.window.event(self.on_draw)
        self.window.event(self.on_key_press)

        self.play_mode = True
        self.play_mode_step = PLAYMODE_STEP_PLAY
        self.play_mode_win_remain = 0

        self.cur_level = None
        self.start_state = None
        self.state = None

        self.state_history = []

        self.step_state = STEP_NONE
        self.solver = None
        self.solver_algorithm = solver.ASTAR_DEADLOCK
        self.plan_explored = 0
        self.planned_actions = []
        self.planned_actions_idx = 0

        self.label1 = pyglet.text.Label('', font_size=16, x=10, y=self.window.height-80)
        self.label2 = pyglet.text.Label('', font_size=16, x=10, y=10)
        self.labelWin = pyglet.text.Label('', bold=True, color=(255, 0, 0, 255), font_size=24, x=10, y=400)

        self.batch = None
        self.all_sprites = None

        self.start_level(self.settings.getint("last_open", fallback=0))
        pyglet.clock.schedule_interval(self.step, 0.1)

    def start_level(self, level):
        if level < 0:
            level = len(self.layouts) - 1
        elif level >= len(self.layouts):
            level = 0

        if self.cur_level == level:
            return

        self.settings.set('last_open', level)

        self.cur_level = level
        self.start_state = self.layouts[level]
        self.state = self.start_state
        self.window.set_caption("level {0}".format(self.cur_level))

        self.stop_plan()

        self.state_history = []

        layout_height = len(self.state.layout) * self.tile_width
        layout_width = len(self.state.layout[0]) * self.tile_width
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
        if self.play_mode and self.state.is_finished():
            self.play_mode_step = PLAYMODE_STEP_WIN
            self.play_mode_win_remain = 5

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

        elif symbol == key.M:
            self.play_mode = not self.play_mode
            self.update_label()

        elif symbol == key._1:
            self.solver_algorithm = solver.BFS
            self.stop_plan()

        elif symbol == key._2:
            self.solver_algorithm = solver.ASTAR
            self.stop_plan()

        elif symbol == key._3:
            self.solver_algorithm = solver.ASTAR_DEADLOCK
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
        if self.play_mode and self.play_mode_step == PLAYMODE_STEP_WIN:
            self.play_mode_win_remain -= dt
            if self.play_mode_win_remain < 0:
                self.play_mode_step = PLAYMODE_STEP_PLAY
                nxt = self.cur_level + 1
                self.start_level(nxt)
            self.update_label()

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
                        self.settings.set_solved(self.solved)

                    self.start_act(action_str, explored)
                    progress = None
                    print(self.cur_level, "solution:", explored, action_str)

            if progress:
                self.plan_explored, frontier = progress
                self.update_label()

        if self.step_state == STEP_ACT:
            if self.planned_actions_idx < len(self.planned_actions):
                action = self.planned_actions[self.planned_actions_idx]
                self.act(action)
                self.planned_actions_idx += 1
            else:
                self.stop_plan()

    step_to_text = {STEP_NONE: '', STEP_THINK: 'think', STEP_ACT: 'act'}
    algorithm_to_text = {solver.BFS: 'bfs', solver.ASTAR: 'astar', solver.ASTAR_DEADLOCK: 'astar_deadlock'}

    def update_label(self):
        if self.play_mode:
            self.label1.text = "第 {0} 关 {1}".format(self.cur_level, SokobanGame.algorithm_to_text[self.solver_algorithm])
            if self.step_state == STEP_THINK:
                self.label2.text = '解决中... {0}'.format(self.plan_explored)
            else:
                self.label2.text = ""

            if self.play_mode_step == PLAYMODE_STEP_WIN:
                self.labelWin.text = "做的好，{0} 秒后进入第 {1} 关".format(int(self.play_mode_win_remain), self.cur_level + 1)
            else:
                self.labelWin.text = ""

        else:
            self.label1.text = SokobanGame.algorithm_to_text[self.solver_algorithm]
            solved_text = (self.cur_level in self.solved) and 'solved' or 'unsolved'
            explored_text = (self.cur_level not in self.solved and self.step_state == STEP_NONE) \
                            and ' ' or 'explored={0}'.format(self.plan_explored)
            self.label2.text = '{0} {1} {2}'.format(solved_text, SokobanGame.step_to_text[self.step_state],
                                                    explored_text)

    def start_plan(self):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.solver = ConcurrentSolver(self.state, self.solver_algorithm)
        self.solver.start()
        self.step_state = STEP_THINK
        self.plan_explored = 0
        self.update_label()

    def start_act(self, actions, explored):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.step_state = STEP_ACT
        self.plan_explored = explored
        self.planned_actions = actions
        self.planned_actions_idx = 0
        self.update_label()

    def stop_plan(self):
        if self.solver:
            self.solver.end()
            self.solver = None

        self.step_state = STEP_NONE
        if self.cur_level in self.solved:
            self.planned_actions, self.plan_explored = self.solved[self.cur_level]
        self.update_label()

    def on_draw(self):
        self.window.clear()
        self.batch.draw()
        self.label1.draw()
        self.label2.draw()
        self.labelWin.draw()

    def run(self):
        pyglet.app.run()


class ConcurrentSolver:
    def __init__(self, startState, algorithm):
        self.startState = startState
        self.queue = multiprocessing.Queue()
        self.problem = solver.SokobanSearchProblem(startState, progress=self._progress, algorithm=algorithm)
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

    def _progress(self, exploredSet, frontier):
        exploredSize, frontierSize = len(exploredSet), len(frontier)
        if exploredSize % 100 == 0:
            self.queue.put([0, (exploredSize, frontierSize)])

    def _solve(self):
        actions, exploredSet = self.problem.solve()
        exploredSize = len(exploredSet)
        self.queue.put([1, (actions, exploredSize)])


def main():
    game = SokobanGame()
    game.run()


if __name__ == '__main__':
    main()
