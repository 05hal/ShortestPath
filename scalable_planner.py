import copy
import heapq
import itertools


MOVES = ((0, 1), (0, -1), (1, 0), (-1, 0), (0, 0))


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def in_bounds_and_free(grid, position):
    row, col = position
    return 0 <= row < len(grid) and 0 <= col < len(grid[0]) and grid[row][col] == 0


def path_length(path):
    if not path:
        return 0
    return sum(
        1
        for previous, current in zip(path, path[1:])
        if (previous[0], previous[1]) != (current[0], current[1])
    )


def cluster_path_length(paths):
    return sum(path_length(path) for path in paths.values() if path)


def cluster_makespan(paths):
    valid_paths = [path for path in paths.values() if path]
    if not valid_paths:
        return 0
    return max(path[-1][2] for path in valid_paths)


def has_complete_solution(paths):
    return bool(paths) and all(path for path in paths.values())


def reconstruct_path(parents, end_state):
    path = []
    current = end_state
    while current is not None:
        position, time_step = current
        path.append((position[0], position[1], time_step))
        current = parents[current]
    path.reverse()
    return path


def path_position_at(path, time_step):
    if time_step < len(path):
        row, col, _ = path[time_step]
        return (row, col)
    row, col, _ = path[-1]
    return (row, col)


def build_agent_order(agents, objective):
    if objective == "makespan":
        return sorted(
            agents,
            key=lambda agent: (
                -manhattan(agent["start"], agent["goal"]),
                abs(agent["start"][0] - 4),
                agent["id"],
            ),
        )

    return sorted(
        agents,
        key=lambda agent: (
            abs(agent["start"][0] - 4),
            -manhattan(agent["start"], agent["goal"]),
            agent["id"],
        ),
    )


def single_agent_reservation_a_star(
    grid,
    start,
    goal,
    vertex_reservations,
    edge_reservations,
    max_time,
):
    start_state = (start, 0)
    parents = {start_state: None}
    best_cost = {start_state: (0, 0)}
    tie = itertools.count()
    open_list = [(manhattan(start, goal), 0, 0, next(tie), start_state)]

    while open_list:
        _, current_length, current_time, _, state = heapq.heappop(open_list)
        position, time_step = state

        if best_cost.get(state) != (current_length, current_time):
            continue

        if position == goal:
            return reconstruct_path(parents, state)

        if time_step >= max_time:
            continue

        for dx, dy in MOVES:
            next_position = (position[0] + dx, position[1] + dy)
            next_time = time_step + 1
            if not in_bounds_and_free(grid, next_position):
                continue
            if next_position in vertex_reservations.get(next_time, set()):
                continue
            if (next_position, position, next_time) in edge_reservations:
                continue

            move_cost = 0 if next_position == position else 1
            next_length = current_length + move_cost
            next_state = (next_position, next_time)
            next_label = (next_length, next_time)
            if next_label >= best_cost.get(next_state, (float("inf"), float("inf"))):
                continue

            best_cost[next_state] = next_label
            parents[next_state] = state
            priority = next_length + manhattan(next_position, goal)
            heapq.heappush(
                open_list,
                (priority, next_length, next_time, next(tie), next_state),
            )

    return None


def reserve_path(path, vertex_reservations, edge_reservations, max_time):
    for index, (row, col, time_step) in enumerate(path):
        vertex_reservations.setdefault(time_step, set()).add((row, col))
        if index > 0:
            previous_row, previous_col, _ = path[index - 1]
            edge_reservations.add(
                ((previous_row, previous_col), (row, col), time_step)
            )

    last_row, last_col, last_time = path[-1]
    for time_step in range(last_time, max_time + 1):
        vertex_reservations.setdefault(time_step, set()).add((last_row, last_col))


def prioritized_plan(grid, agents, objective):
    horizon = len(grid) * len(grid[0]) + len(agents) * 6
    vertex_reservations = {}
    edge_reservations = set()
    ordered_agents = build_agent_order(agents, objective)
    planned_paths = {}

    for agent in ordered_agents:
        path = single_agent_reservation_a_star(
            grid,
            agent["start"],
            agent["goal"],
            vertex_reservations,
            edge_reservations,
            horizon,
        )
        if path is None:
            return {item["id"]: None for item in agents}

        planned_paths[agent["id"]] = path
        reserve_path(path, vertex_reservations, edge_reservations, horizon)

    return {agent["id"]: planned_paths.get(agent["id"]) for agent in agents}


def build_constraint_tables(constraints, agent_id):
    vertex_constraints = {}
    edge_constraints = set()
    max_time = 0

    for constraint in constraints:
        if constraint["agent"] != agent_id:
            continue

        max_time = max(max_time, constraint["time"])
        if constraint["kind"] == "vertex":
            vertex_constraints.setdefault(constraint["time"], set()).add(
                constraint["position"]
            )
        else:
            edge_constraints.add(
                (
                    constraint["from_position"],
                    constraint["to_position"],
                    constraint["time"],
                )
            )

    return vertex_constraints, edge_constraints, max_time


def goal_is_safe(goal, arrival_time, vertex_constraints, edge_constraints, horizon):
    for time_step in range(arrival_time, horizon + 1):
        if goal in vertex_constraints.get(time_step, set()):
            return False
        if (goal, goal, time_step) in edge_constraints:
            return False
    return True


def single_agent_constrained_a_star(grid, agent, constraints, objective, horizon):
    start = agent["start"]
    goal = agent["goal"]
    vertex_constraints, edge_constraints, max_constraint_time = build_constraint_tables(
        constraints,
        agent["id"],
    )

    if start in vertex_constraints.get(0, set()):
        return None

    upper_time = max(horizon, max_constraint_time + 2)
    start_state = (start, 0)
    parents = {start_state: None}
    best_cost = {start_state: (0, 0)}
    tie = itertools.count()
    open_list = [
        (
            manhattan(start, goal),
            manhattan(start, goal),
            0,
            0,
            next(tie),
            start_state,
        )
    ]

    while open_list:
        _, _, current_length, current_time, _, state = heapq.heappop(open_list)
        position, time_step = state

        if best_cost.get(state) != (current_length, current_time):
            continue

        if position == goal and goal_is_safe(
            goal,
            time_step,
            vertex_constraints,
            edge_constraints,
            upper_time,
        ):
            return reconstruct_path(parents, state)

        if time_step >= upper_time:
            continue

        for dx, dy in MOVES:
            next_position = (position[0] + dx, position[1] + dy)
            next_time = time_step + 1

            if not in_bounds_and_free(grid, next_position):
                continue
            if next_position in vertex_constraints.get(next_time, set()):
                continue
            if (position, next_position, next_time) in edge_constraints:
                continue

            move_cost = 0 if next_position == position else 1
            next_length = current_length + move_cost
            next_state = (next_position, next_time)
            next_label = (next_length, next_time)

            if next_label >= best_cost.get(next_state, (float("inf"), float("inf"))):
                continue

            best_cost[next_state] = next_label
            parents[next_state] = state
            length_lb = next_length + manhattan(next_position, goal)
            time_lb = next_time + manhattan(next_position, goal)
            if objective == "makespan":
                priority = (length_lb, time_lb, next_length, next_time, next(tie), next_state)
            else:
                priority = (length_lb, time_lb, next_length, next_time, next(tie), next_state)
            heapq.heappush(open_list, priority)

    return None


def detect_first_conflict(paths, agent_ids):
    max_time = cluster_makespan(paths)
    for time_step in range(max_time + 1):
        positions = {}
        for agent_id in agent_ids:
            position = path_position_at(paths[agent_id], time_step)
            if position in positions:
                return {
                    "kind": "vertex",
                    "time": time_step,
                    "agents": (positions[position], agent_id),
                    "position": position,
                }
            positions[position] = agent_id

        if time_step == 0:
            continue

        for index, left_id in enumerate(agent_ids):
            left_prev = path_position_at(paths[left_id], time_step - 1)
            left_curr = path_position_at(paths[left_id], time_step)
            for right_id in agent_ids[index + 1 :]:
                right_prev = path_position_at(paths[right_id], time_step - 1)
                right_curr = path_position_at(paths[right_id], time_step)
                if left_prev == right_curr and right_prev == left_curr:
                    return {
                        "kind": "edge",
                        "time": time_step,
                        "agents": (left_id, right_id),
                        "from_positions": (left_prev, right_prev),
                        "to_positions": (left_curr, right_curr),
                    }
    return None


def make_child_constraint(conflict, agent_id):
    if conflict["kind"] == "vertex":
        return {
            "agent": agent_id,
            "kind": "vertex",
            "time": conflict["time"],
            "position": conflict["position"],
        }

    agent_index = 0 if conflict["agents"][0] == agent_id else 1
    return {
        "agent": agent_id,
        "kind": "edge",
        "time": conflict["time"],
        "from_position": conflict["from_positions"][agent_index],
        "to_position": conflict["to_positions"][agent_index],
    }


def cbs_plan(grid, agents, objective="length", max_high_level_nodes=2000):
    horizon = len(grid) * len(grid[0]) + len(agents) * 6
    paths = {}
    for agent in agents:
        path = single_agent_constrained_a_star(
            grid,
            agent,
            constraints=[],
            objective=objective,
            horizon=horizon,
        )
        if path is None:
            return {item["id"]: None for item in agents}
        paths[agent["id"]] = path

    tie = itertools.count()
    root = {
        "constraints": [],
        "paths": paths,
        "total_length": cluster_path_length(paths),
        "makespan": cluster_makespan(paths),
    }
    open_list = [
        (
            root["total_length"],
            root["makespan"],
            next(tie),
            root,
        )
    ]

    expanded = 0
    agent_ids = [agent["id"] for agent in agents]
    agents_by_id = {agent["id"]: agent for agent in agents}

    while open_list and expanded < max_high_level_nodes:
        _, _, _, node = heapq.heappop(open_list)
        expanded += 1

        conflict = detect_first_conflict(node["paths"], agent_ids)
        if conflict is None:
            return node["paths"]

        for agent_id in conflict["agents"]:
            child_constraints = copy.deepcopy(node["constraints"])
            child_constraints.append(make_child_constraint(conflict, agent_id))
            child_paths = dict(node["paths"])
            replanned_path = single_agent_constrained_a_star(
                grid,
                agents_by_id[agent_id],
                child_constraints,
                objective=objective,
                horizon=horizon,
            )
            if replanned_path is None:
                continue

            child_paths[agent_id] = replanned_path
            heapq.heappush(
                open_list,
                (
                    cluster_path_length(child_paths),
                    cluster_makespan(child_paths),
                    next(tie),
                    {
                        "constraints": child_constraints,
                        "paths": child_paths,
                        "total_length": cluster_path_length(child_paths),
                        "makespan": cluster_makespan(child_paths),
                    },
                ),
            )

    return {item["id"]: None for item in agents}
