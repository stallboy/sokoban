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


def nullProgress(explored, frontier):
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
    cost = 0
    node = [state, [], cost]
    frontier.push(node, cost + heuristic(state, problem))
    frontierStateToNode = {state: node}
    exploredSet = set()

    while True:
        if frontier.isEmpty():
            return [], exploredSet

        state, solution, cost = frontier.pop()
        del frontierStateToNode[state]
        if problem.isGoalState(state):
            return solution, exploredSet

        exploredSet.add(state)
        progress(exploredSet, frontier)

        for nextState, action, stepCost in problem.getSuccessors(state):
            if (nextState not in exploredSet) and (nextState not in frontierStateToNode):
                nextCost = cost + stepCost
                nextNode = [nextState, [*solution, action], nextCost]
                frontier.push(nextNode, nextCost + heuristic(nextState, problem))
                frontierStateToNode[nextState] = nextNode
            elif nextState in frontierStateToNode:
                nodeInFrontier = frontierStateToNode[nextState]
                nextCost = cost + stepCost
                if nextCost < nodeInFrontier[2]:
                    nodeInFrontier[1] = [*solution, action]
                    nodeInFrontier[2] = nextCost
                    frontier.update(nodeInFrontier, nextCost + heuristic(nextState, problem))


def uniformCostSearch(problem):
    """Search the node of least total cost first."""
    return aStarSearch(problem)


# Abbreviations
bfs = breadthFirstSearch
dfs = depthFirstSearch
astar = aStarSearch
ucs = uniformCostSearch
