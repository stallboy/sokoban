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


def nullHeuristic(state, problem=None):
    return 0


def nullProgress(exploredSize, frontierSize):
    pass


def GRAPH_SEARCH(problem, Strategy, heuristic=nullHeuristic, progress=nullProgress):
    hasPriority = (Strategy == util.PriorityQueue)
    if heuristic is None:
        heuristic = nullHeuristic
    if progress is None:
        progress = nullProgress

    frontier = Strategy()
    state = problem.getStartState()
    cost = 0
    node = [state, [], cost]
    if hasPriority:
        frontier.push(node, cost + heuristic(state, problem))
    else:
        frontier.push(node)
    frontierStateToNode = {state: node}

    exploredSet = set()

    while True:
        if frontier.isEmpty():
            return [], len(exploredSet)

        state, solution, cost = frontier.pop()
        del frontierStateToNode[state]
        if problem.isGoalState(state):
            return solution, len(exploredSet)

        exploredSet.add(state)
        progress(len(exploredSet), len(frontier))

        for nextState, action, stepCost in problem.getSuccessors(state):
            if (nextState not in exploredSet) and (nextState not in frontierStateToNode):
                nextCost = cost + stepCost
                nextNode = [nextState, [*solution, action], nextCost]
                if hasPriority:
                    frontier.push(nextNode, nextCost + heuristic(nextState, problem))
                else:
                    frontier.push(nextNode)
                frontierStateToNode[nextState] = nextNode
            elif hasPriority and nextState in frontierStateToNode:
                nodeInFrontier = frontierStateToNode[nextState]
                nextCost = cost + stepCost
                if nextCost < nodeInFrontier[2]:
                    nodeInFrontier[1] = [*solution, action]
                    nodeInFrontier[2] = nextCost
                    frontier.update(nodeInFrontier, nextCost + heuristic(nextState, problem))


def depthFirstSearch(problem):
    frontier = util.Stack()
    state = problem.getStartState()
    node = [state, []]
    frontier.push(node)
    exploredSet = set()

    while True:
        if frontier.isEmpty():
            return []

        state, solution = frontier.pop()
        if problem.isGoalState(state):
            return solution
        exploredSet.add(state)

        for nextState, action, stepCost in problem.getSuccessors(state):
            if nextState not in exploredSet:
                nextNode = [nextState, [*solution, action]]
                frontier.push(nextNode)


def breadthFirstSearch(problem):
    return GRAPH_SEARCH(problem, util.Queue)


def uniformCostSearch(problem):
    """Search the node of least total cost first."""
    return GRAPH_SEARCH(problem, util.PriorityQueue)


def aStarSearch(problem, heuristic=nullHeuristic, progress=nullProgress):
    """Search the node that has the lowest combined cost and heuristic first."""
    return GRAPH_SEARCH(problem, util.PriorityQueue, heuristic=heuristic, progress=progress)


# Abbreviations
bfs = breadthFirstSearch
dfs = depthFirstSearch
astar = aStarSearch
ucs = uniformCostSearch
