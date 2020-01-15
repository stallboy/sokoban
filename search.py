import util


class SearchProblem:
    def getStartState(self):
        raise NotImplementedError

    def isGoalState(self, state):
        raise NotImplementedError

    def getSuccessors(self, state):
        """
          state: Search state

        For a given state, this should return a list of triples, (successor,
        action, stepCost), where 'successor' is a successor to the current
        state, 'action' is the action required to get there, and 'stepCost' is
        the incremental cost of expanding to that successor.
        """
        raise NotImplementedError


def nullProgress(_explored, _frontier):
    pass


def depthFirstSearch(problem, progress=nullProgress):
    if progress is None:
        progress = nullProgress

    frontier = util.Stack()
    state = problem.getStartState()
    node = [state, []]
    frontier.push(node)
    exploredSet = set()

    while True:
        if frontier.isEmpty():
            return [], exploredSet

        state, solution = frontier.pop()
        if problem.isGoalState(state):
            return solution, exploredSet
        exploredSet.add(state)
        progress(exploredSet, frontier)

        for nextState, action, stepCost in problem.getSuccessors(state):
            if nextState not in exploredSet:
                nextNode = [nextState, [*solution, action]]
                frontier.push(nextNode)


def breadthFirstSearch(problem, progress=nullProgress):
    if progress is None:
        progress = nullProgress

    frontier = util.Queue()
    state = problem.getStartState()
    node = [state, []]
    frontier.push(node)
    exploredSet = {}

    while True:
        if frontier.isEmpty():
            return [], exploredSet

        state, solution = frontier.pop()
        if problem.isGoalState(state):
            return solution, exploredSet
        exploredSet[state] = solution
        progress(exploredSet, frontier)

        for nextState, action, stepCost in problem.getSuccessors(state):
            if nextState not in exploredSet:
                nextNode = [nextState, [*solution, action]]
                frontier.push(nextNode)


def nullHeuristic(state, problem):
    return 0


def aStarSearch(problem, heuristic=nullHeuristic, progress=nullProgress):
    if heuristic is None:
        heuristic = nullHeuristic
    if progress is None:
        progress = nullProgress

    frontier = util.PriorityQueue()
    state = problem.getStartState()
    g = 0
    h = heuristic(state, problem)
    f = g + h
    node = [state, [], g, h]

    frontier.push(node, f)
    frontierMap = {state: node}
    exploredSet = set()

    while True:
        if frontier.isEmpty():
            return [], exploredSet

        state, solution, curG, _ = frontier.pop()
        del frontierMap[state]

        if problem.isGoalState(state):
            return solution, exploredSet

        exploredSet.add(state)
        progress(exploredSet, frontier)

        for nextState, action, stepCost in problem.getSuccessors(state):
            if nextState in exploredSet:
                continue
            node = frontierMap.get(nextState)

            if node:
                g = curG + stepCost
                _, _, oldG, h = node
                if g < oldG:
                    f = g + h
                    node[1] = [*solution, action]
                    node[2] = g
                    frontier.update(node, f)
                else:
                    pass  # ignore
            else:
                g = curG + stepCost
                h = heuristic(nextState, problem)
                f = g + h
                node = [nextState, [*solution, action], g, h]
                frontier.push(node, f)
                frontierMap[nextState] = node


def uniformCostSearch(problem):
    """Search the node of least total cost first."""
    return aStarSearch(problem)


# Abbreviations
bfs = breadthFirstSearch
dfs = depthFirstSearch
astar = aStarSearch
ucs = uniformCostSearch
