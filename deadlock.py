import search
import space

UNREACHABLE = 10000000


class Area(object):
    def __init__(self, reachable_dest_count):
        self.reachable_dest_count = reachable_dest_count
        self.positions = []  # 包含哪些位置


DEADLOCK_AREA = Area(0)


class Deadlock(object):
    def __init__(self, layout):
        self.layout = layout

        # 给所有静态空格的地方，赋予一个id，从下到上从左到右从0开始递增。非空格的话是-1
        self.spaceid_layout = None
        self.space_cnt = 0
        self.spaceid_to_isdest = []
        self.spaceid_to_pos = []

        # 静态空格到静态空格的距离矩阵
        self.distance_matrix = None

        # 每个格子 ---> area
        self.spaceid_to_area = None

    def get_distance(self, from_pos, to_pos):
        return self.distance_matrix[self._id(from_pos)][self._id(to_pos)]

    def get_area(self, pos):
        return self.spaceid_to_area[self._id(pos)]

    def prepare(self):
        self._prepare_spaceid()
        self._prepare_distance_matrix()
        self._prepare_areas()

    def _id(self, pos):
        x, y = pos
        return self.spaceid_layout[y][x]

    def _prepare_spaceid(self):
        self.spaceid_layout = [[-1 for c in line] for line in self.layout]
        space_cnt = 0
        for y, line in enumerate(self.layout):
            for x, c in enumerate(line):
                if not space.is_static_block(c):
                    self.spaceid_layout[y][x] = space_cnt
                    self.spaceid_to_isdest.append(space.is_dest(c))
                    self.spaceid_to_pos.append((x, y))
                    space_cnt += 1
        self.space_cnt = space_cnt
        self.distance_matrix = [[UNREACHABLE for _ in range(space_cnt)] for _ in range(space_cnt)]

    def _prepare_distance_matrix(self):
        for y, line in enumerate(self.spaceid_layout):
            for x, spaceid in enumerate(line):
                if spaceid > -1:
                    self._prepare_one(x, y, spaceid)

    def _prepare_one(self, x, y, spaceid):
        problem = PushBoxProblem(self.spaceid_layout, spaceid, x, y)
        exploredDict = problem.solve()
        for state, solution in exploredDict.items():
            to_spaceid = state[0]
            self.distance_matrix[spaceid][to_spaceid] = len(solution)

    def _prepare_areas(self):
        # 每个空格 ---> 可到达的目的格子集合
        from_to_reachable_dests = {}
        for from_id in range(self.space_cnt):
            reachable_dests = []
            for to_id in range(self.space_cnt):
                distance = self.distance_matrix[from_id][to_id]
                if distance < UNREACHABLE and self.spaceid_to_isdest[to_id]:
                    reachable_dests.append(to_id)

            if reachable_dests:
                from_to_reachable_dests[from_id] = tuple(reachable_dests)

        # 目的格子集合 ---> 有哪些空格是只到这些目的地的
        dests_to_area = {}
        for from_id, dest_ids in from_to_reachable_dests.items():
            if dest_ids not in dests_to_area:
                area = Area(len(dest_ids))
                dests_to_area[dest_ids] = area

        # 填area，有哪些空格是只到这些目的地的
        for dest_ids, area in dests_to_area.items():
            for from_id, f_dest_ids in from_to_reachable_dests.items():
                if set(dest_ids).issuperset(set(f_dest_ids)):
                    area.positions.append(self.spaceid_to_pos[from_id])

        # 转化为spaceid_to_area
        self.spaceid_to_area = {}
        for from_id in range(self.space_cnt):
            if from_id in from_to_reachable_dests:
                reachable_dests = from_to_reachable_dests[from_id]
                area = dests_to_area[reachable_dests]
                self.spaceid_to_area[from_id] = area
            else:
                self.spaceid_to_area[from_id] = DEADLOCK_AREA


class PushBoxProblem(search.SearchProblem):
    def __init__(self, spaceid_layout, startid, x, y):
        self.spaceid_layout = spaceid_layout
        self.start = (startid, x, y)  # 加入id，方便提取exploredDict

    def getStartState(self):
        return self.start

    def isGoalState(self, state):
        return False  # 遍历所有可达目的地，没有具体的goal

    def getSuccessors(self, state):
        successors = []
        _, x, y = state
        for action, (dx, dy) in space.ACTIONS.items():
            nx = x + dx
            ny = y + dy
            man_x = x - dx
            man_y = y - dy
            nid = self.spaceid_layout[ny][nx]
            if nid > -1 and self.spaceid_layout[man_y][man_x] > -1:  # 上下或左右都是空间才能移动
                successors.append([(nid, nx, ny), action, 1])

        return successors

    def solve(self):
        actions, exploredDict = search.bfs(self)
        assert len(actions) == 0
        return exploredDict
