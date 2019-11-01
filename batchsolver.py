import space
import solver


def _solve(lvl, problem, queue):
    queue.put([0, lvl])
    actions, exploredSet = problem.solve()
    queue.put([1, (lvl, actions, len(exploredSet))])


def main():
    from multiprocessing import Pool, Manager
    m = Manager()
    queue = m.Queue()

    thinking = set()
    settings = space.SokobanSettings()

    layouts = space.SokobanLoader().load_maps()
    problems = [(lvl, solver.SokobanSearchProblem(startState), queue)
                for lvl, startState in enumerate(layouts) if lvl not in settings.solved]
    import random
    random.shuffle(problems)
    print("共{0}关卡，剩余{1}未解决".format(len(layouts), len(problems)))

    with Pool() as p:
        q = m.Queue()
        r = p.starmap_async(_solve, problems)
        while not r.ready():
            try:
                info_type, info = queue.get(timeout=0.1)
                if info_type == 0:
                    lvl = info
                    thinking.add(lvl)

                elif info_type == 1:
                    lvl, actions, explored = info
                    action_str = "".join(actions)
                    thinking.remove(lvl)
                    settings.solved[lvl] = (action_str, explored)
                    print("lvl={0} think={1} solved={2}, wait={3}: res={4}, {5}".format(
                        lvl,
                        len(thinking),
                        len(settings.solved),
                        len(layouts) - len(thinking) - len(settings.solved),
                        explored,
                        action_str
                    ))

                    settings.set_solved(settings.solved)
            except:
                pass


if __name__ == '__main__':
    main()
