import search
import space
import munkres
import deadlock


def manhattan_distance(bp, dp):
    return abs(bp[0] - dp[0]) + abs(bp[1] - dp[1])


# 用匈牙利算法来算下最短分配距离
def munkres_distance(boxes, dests, distance_func=manhattan_distance):
    matrix = [[distance_func(bp, dp) for dp in dests] for bp in boxes]
    m = munkres.Munkres()
    indexes = m.compute(matrix)
    return sum([matrix[row][column] for row, column in indexes])


# 满足Admissibility, 寻出的路径是最短的
def sokobanHeuristic(state, problem):
    boxes = []
    dests = []

    for y, line in enumerate(state.layout):
        for x, c in enumerate(line):
            if c == space.S_BOX:
                boxes.append((x, y))
            elif c in [space.S_DEST, space.S_MAN_AT_DEST]:
                dests.append((x, y))

    dest_dis = 0
    if boxes:
        dest_dis = munkres_distance(boxes, dests, distance_func=problem.deadlock.get_distance)

    man_dis = 0
    mp = state.man_pos
    if boxes:
        man_dis = min([manhattan_distance(bp, mp) for bp in boxes]) - 1
        if man_dis < 0:
            man_dis = 0
    return dest_dis + man_dis


class SokobanSearchProblem(search.SearchProblem):

    def __init__(self, startState, progress=None):
        self.startState = startState
        self.deadlock = deadlock.Deadlock(self.startState.layout)
        self.progress = progress
        self.deadlock.prepare()

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
                    if not self.is_ok(nxt, new_box_pos):
                        continue
                successors.append((nxt, action, 1))

        return successors

    def is_ok(self, state, new_box_pos):
        area = self.deadlock.get_area(new_box_pos)
        if area.reachable_dest_count == 0:
            return False

        max_box_cnt = area.reachable_dest_count
        cnt = 0
        for area_pos in area.positions:
            if state.has_box(area_pos[0], area_pos[1]):
                cnt += 1
        if cnt > max_box_cnt:
            return False

        # 这是4个一组，如果都被挡住则不能再移动了，又有非目的地的箱子则失败
        bx, by = new_box_pos
        layout = state.layout
        diagonals = [(-1, -1), (1, 1), (-1, 1), (1, -1)]
        quads = [[(bx, by), (bx + dx, by), (bx + dx, by + dy), (bx, by + dy)] for dx, dy in diagonals]
        for q in quads:
            ss = [layout[y][x] for x, y in q]
            # 不用考虑S_OUTSIDE,因为这种情况会被deadlock先干掉
            all_block_or_box = all([s in [space.S_WALL, space.S_BOX, space.S_BOX_AT_DEST] for s in ss])
            all_block_or_boxAtDst = all([s in [space.S_WALL, space.S_BOX_AT_DEST] for s in ss])
            if all_block_or_box and not all_block_or_boxAtDst:
                return False

        return True
