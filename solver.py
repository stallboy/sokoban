import search
import space
import munkres

S_WALL = space.S_WALL
S_SPACE = space.S_SPACE
S_OUTSIZE = space.S_OUTSIZE
S_BOX = space.S_BOX
S_BOX_AT_DEST = space.S_BOX_AT_DEST
S_DEST = space.S_DEST
S_MAN = space.S_MAN
S_MAN_AT_DEST = space.S_MAN_AT_DEST


def distance(bp, dp):
    return abs(bp[0] - dp[0]) + abs(bp[1] - dp[1])


# 用匈牙利算法来算下最短分配距离
def munkres_distance(boxes, dests):
    matrix = [[distance(bp, dp) for dp in dests] for bp in boxes]
    m = munkres.Munkres()
    indexes = m.compute(matrix)
    return sum([matrix[row][column] for row, column in indexes])


# 满足Admissibility, 寻出的路径是最短的
def sokobanHeuristic(state, _problem):
    boxes = []
    dests = []

    for y, line in enumerate(state.layout):
        for x, c in enumerate(line):
            if c == S_BOX:
                boxes.append((x, y))
            elif c == S_DEST or c == S_MAN_AT_DEST:
                dests.append((x, y))

    dest_dis = 0
    if boxes:
        dest_dis = munkres_distance(boxes, dests)

    man_dis = 0
    mp = state.man_pos
    if boxes:
        man_dis = min([distance(bp, mp) for bp in boxes]) - 1
        if man_dis < 0:
            man_dis = 0
    return dest_dis + man_dis


class SokobanSearchProblem(search.SearchProblem):

    def __init__(self, startState, progress=None):
        self.startState = startState
        self.progress = progress

    def getStartState(self):
        return self.startState

    def isGoalState(self, state):
        return state.is_finished()

    def solve(self):
        return search.astar(self, heuristic=sokobanHeuristic, progress=self.progress)

    def getSuccessors(self, state):
        successors = []

        for action, (dx, dy) in space.ACTIONS.items():
            nxt, new_box_pos = state.try_move2(dx, dy)
            if nxt:
                if new_box_pos:
                    if not self.is_ok(nxt, new_box_pos, dx, dy):
                        continue
                successors.append((nxt, action, 1))

        return successors

    def is_ok(self, state, box_pos, dx, dy):
        bx, by = box_pos
        layout = state.layout
        # 这是4个一组，如果都被挡住则不能再移动了，又有非目的地的箱子则失败
        diagonals = [(-1, -1), (1, 1), (-1, 1), (1, -1)]
        quads = [[(bx, by), (bx + dx, by), (bx + dx, by + dy), (bx, by + dy)] for dx, dy in diagonals]
        for q in quads:
            ss = [layout[y][x] for x, y in q]
            all_block_or_box = all([s in [S_WALL, S_BOX, S_BOX_AT_DEST] for s in ss])
            all_block_or_boxAtDst = all([s in [S_WALL, S_BOX_AT_DEST] for s in ss])
            if all_block_or_box and not all_block_or_boxAtDst:
                return False

        # 一个有界边上的目的位置数量小于 已经在这个边上的箱子数量，则也失败
        hasLeftOrDownWall, numOfDest1, numOfBox1 = self.expand_wall(layout, bx, by, dx, dy, True)
        if hasLeftOrDownWall:
            hasRightOrUpWall, numOfDest2, numOfBox2 = self.expand_wall(layout, bx, by, dx, dy,
                                                                       False)
            if hasRightOrUpWall:
                if numOfDest1 + numOfDest2 < numOfBox1 + numOfBox2:
                    return False

        return True

    def expand_wall(self, layout, bx, by, dx, dy, left_or_down):  # return (hasWall, numOfDest, numOfBox)
        X = bx + dx  # X,Y是wall的位置
        if dx == 0 and not left_or_down:  # 当left or down时包含自己当前位置
            X = bx + 1

        Y = by + dy
        if dy == 0 and not left_or_down:
            Y = by + 1

        numOfDest = 0
        numOfBox = 0
        while True:
            if dx == 0:  # 横向沿wall检查
                if left_or_down:
                    if X < 0:
                        break
                else:
                    if X >= len(layout[0]):
                        break
            else:  # 纵向沿wall检查
                if left_or_down:
                    if Y < 0:
                        break
                else:
                    if Y >= len(layout):
                        break

            if layout[Y][X] == S_WALL:  # 这个是墙那一行或列
                s = layout[Y - dy][X - dx]  # 这是箱子那一行或列
                if s == S_WALL:
                    return True, numOfDest, numOfBox
                elif s == S_DEST:
                    numOfDest += 1
                elif s == S_BOX:
                    numOfBox += 1
                elif s == S_BOX_AT_DEST:
                    numOfBox += 1
                    numOfDest += 1
            else:
                break

            if dx == 0:  # 横向沿wall检查
                X += left_or_down and -1 or 1
            else:  # 纵向沿wall检查
                Y += left_or_down and -1 or 1

        return False, numOfDest, numOfBox


def read_solution(config):
    return {int(sec): (config[sec]['actions'], int(config[sec]['explored']))
            for sec in config.sections()}


def save_solution(config, solution):
    for sec in config.sections():
        del config[sec]
    keys = list(solution.keys())
    keys.sort()
    for key in keys:
        actions, explored = solution[key]
        config[str(key)] = {
            'explored': str(explored),
            'actions': actions
        }


def _solve(lvl, problem, queue):
    queue.put([0, lvl])
    actions, exploredSize = problem.solve()
    queue.put([1, (lvl, actions, exploredSize)])


def main():
    from multiprocessing import Pool, Manager
    m = Manager()
    queue = m.Queue()

    thinking = set()
    config = space.load_settings()
    solved = read_solution(config)

    layouts = space.load_layouts()
    problems = [(lvl, SokobanSearchProblem(space.SokobanState(layout)), queue)
                for lvl, layout in enumerate(layouts) if lvl not in solved]
    import random
    random.shuffle(problems)

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
                    solved[lvl] = (action_str, explored)
                    print("lvl={0} think={1} solved={2}, wait={3}: res={4}, {5}".format(
                        lvl,
                        len(thinking),
                        len(solved),
                        len(layouts) - len(thinking) - len(solved),
                        explored,
                        action_str
                    ))

                    # 排序后再保存
                    save_solution(config, solved)
                    space.save_settings(config)

            except:
                pass


if __name__ == '__main__':
    main()
