import time
import multiprocessing

import space
import solver


class TimeoutThinker:
    def __init__(self, level, startState, queue):
        self.level = level
        self.startState = startState
        self.queue = queue
        self.problem = solver.SokobanSearchProblem(startState, self._progress)
        self.process = multiprocessing.Process(target=self._solve)
        self.startTime = time.time()
        self.exploredSize = 0

    def start(self):
        self.process.start()

    def end(self):
        self.process.terminate()

    def _progress(self, exploredSet, frontier):
        exploredSize, frontierSize = len(exploredSet), len(frontier)
        if exploredSize % 100 == 0:
            self.queue.put([0, (self.level, exploredSize, frontierSize)])

    def _solve(self):
        actions, exploredSet = self.problem.solve()
        exploredSize = len(exploredSet)
        self.queue.put([1, (self.level, actions, exploredSize)])


class ThinkerManager:
    def __init__(self, ncpu=0, timeout=20):

        self.timeout = timeout
        if ncpu == 0:
            ncpu = multiprocessing.cpu_count()

        self.ncpu = ncpu
        m = multiprocessing.Manager()

        self.queue = m.Queue()
        self.settings = space.SokobanSettings()
        self.layouts = space.SokobanLoader().load_maps()

        self.problems = [(level, startState)
                         for level, startState in enumerate(self.layouts) if level not in self.settings.solved]

        self.thinking = {}
        self.problem_idx = 0

    def start(self):

        print("共{0}关卡，剩余{1}未解决，开启{2}个进程开始解决, 超时时间={3}".format(
            len(self.layouts), len(self.problems), self.ncpu, self.timeout))
        self._try_start_new_thinker()

        while True:
            if len(self.thinking) == 0 and self.problem_idx == len(self.problems):
                return
            self._end_timeout_thinker()
            self._try_start_new_thinker()
            try:
                info_type, info = self.queue.get(timeout=0.1)
                if info_type == 0:
                    level, exploredSize, _ = info
                    if level in self.thinking:
                        self.thinking[level].exploredSize = exploredSize

                elif info_type == 1:
                    level, actions, explored = info
                    action_str = "".join(actions)
                    if level in self.thinking:
                        del self.thinking[level]

                    self.settings.solved[level] = (action_str, explored)
                    print("lvl={0} think={1} solved={2}, wait={3}: res={4}, {5}".format(
                        level,
                        len(self.thinking),
                        len(self.settings.solved),
                        len(self.layouts) - len(self.thinking) - len(self.settings.solved),
                        explored,
                        action_str
                    ))

                    self.settings.set_solved(self.settings.solved)
            except:
                pass

    def _try_start_new_thinker(self):
        while len(self.thinking) < self.ncpu:
            if self.problem_idx < len(self.problems):
                level, startState = self.problems[self.problem_idx]
                self.problem_idx += 1
                thinker = TimeoutThinker(level, startState, self.queue)
                self.thinking[level] = thinker
                thinker.start()
            else:
                return

    def _end_timeout_thinker(self):
        timeout = []
        curTime = time.time()
        for level, thinker in self.thinking.items():
            if curTime - thinker.startTime > 30:
                timeout.append(level)
                thinker.end()
                print("lvl={0} timeout explored={1}".format(level, thinker.exploredSize))

        for level in timeout:
            del self.thinking[level]


def main():
    man = ThinkerManager(ncpu=0, timeout=180)
    man.start()


if __name__ == '__main__':
    main()
