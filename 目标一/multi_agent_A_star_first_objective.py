# -*- coding: utf-8 -*-
import heapq
import itertools
from dataclasses import dataclass


MOVES = ((0, 1), (0, -1), (1, 0), (-1, 0), (0, 0))


@dataclass(frozen=True)
class SearchNode:
    positions: tuple
    t: int
    g: int
    parent: "SearchNode | None" = None


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cluster_heuristic(positions, goals):
    return sum(manhattan(position, goal) for position, goal in zip(positions, goals))


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


def in_bounds_and_free(grid, position):
    x, y = position
    return (
        0 <= x < len(grid)
        and 0 <= y < len(grid[0])
        and grid[x][y] == 0
    )


def has_vertex_conflict(positions):
    return len(set(positions)) != len(positions)


def has_edge_conflict(previous_positions, next_positions):
    for i in range(len(previous_positions)):
        for j in range(i + 1, len(previous_positions)):
            if (
                previous_positions[i] == next_positions[j]
                and previous_positions[j] == next_positions[i]
            ):
                return True
    return False


def reconstruct_paths(node, agent_ids):
    timeline = []
    current = node
    while current:
        timeline.append((current.t, current.positions))
        current = current.parent
    timeline.reverse()

    paths = {agent_id: [] for agent_id in agent_ids}
    for t, positions in timeline:
        for agent_id, (x, y) in zip(agent_ids, positions):
            paths[agent_id].append((x, y, t))
    return paths


def multi_agent_a_star(grid, agents, max_time=None):
    """用于第一优化目标的集中式 multi-agent A*。

    优化值是集群路径总长度。车辆移动到相邻格时路径长度加 1；
    原地停留允许作为避让动作，但不增加路径长度。
    """
    if not agents:
        return {}, 0

    starts = tuple(agent["start"] for agent in agents)
    goals = tuple(agent["goal"] for agent in agents)
    agent_ids = tuple(agent["id"] for agent in agents)

    for position in starts + goals:
        if not in_bounds_and_free(grid, position):
            raise ValueError(f"Invalid start/goal position: {position}")

    if has_vertex_conflict(starts):
        return {agent_id: None for agent_id in agent_ids}, None

    if max_time is None:
        free_cells = sum(cell == 0 for row in grid for cell in row)
        max_time = max(cluster_heuristic(starts, goals) + free_cells * len(agents), free_cells)

    start = SearchNode(positions=starts, t=0, g=0)
    start_h = cluster_heuristic(starts, goals)
    tie = itertools.count()
    open_list = [(start_h, start_h, 0, 0, next(tie), start)]

    # 没有外部动态障碍时，同一组联合位置下，更早且总代价不高的状态支配更晚状态。
    best_cost = {starts: 0}

    while open_list:
        _, _, g, _, _, current = heapq.heappop(open_list)
        if g != best_cost.get(current.positions):
            continue

        if current.positions == goals:
            paths = reconstruct_paths(current, agent_ids)
            return paths, cluster_path_length(paths)

        if current.t >= max_time:
            continue

        candidate_lists = []
        for position in current.positions:
            candidates = []
            for dx, dy in MOVES:
                next_position = (position[0] + dx, position[1] + dy)
                if in_bounds_and_free(grid, next_position):
                    candidates.append(next_position)
            candidate_lists.append(candidates)

        for next_positions in itertools.product(*candidate_lists):
            next_positions = tuple(next_positions)
            if has_vertex_conflict(next_positions):
                continue
            if has_edge_conflict(current.positions, next_positions):
                continue

            move_cost = sum(
                previous != next_position
                for previous, next_position in zip(current.positions, next_positions)
            )
            next_g = current.g + move_cost
            if next_g >= best_cost.get(next_positions, float("inf")):
                continue

            next_node = SearchNode(
                positions=next_positions,
                t=current.t + 1,
                g=next_g,
                parent=current,
            )
            best_cost[next_positions] = next_g
            heuristic = cluster_heuristic(next_positions, goals)
            heapq.heappush(
                open_list,
                (
                    next_g + heuristic,
                    heuristic,
                    next_g,
                    next_node.t,
                    next(tie),
                    next_node,
                ),
            )

    return {agent_id: None for agent_id in agent_ids}, None


class MultiAgentScheduler:
    def __init__(self, grid, max_time=None):
        self.grid = grid
        self.max_time = max_time
        self.total_path_length = None

    def plan_paths(self, agents):
        paths, total_length = multi_agent_a_star(self.grid, agents, self.max_time)
        self.total_path_length = total_length
        return paths


if __name__ == "__main__":
    grid = [[0] * 10 for _ in range(10)]
    grid[4][3:7] = [1, 1, 1, 1]

    agents = [
        {"id": "A", "start": (0, 0), "goal": (9, 9)},
        {"id": "B", "start": (9, 0), "goal": (0, 9)},
        {"id": "C", "start": (4, 0), "goal": (4, 9)},
    ]

    scheduler = MultiAgentScheduler(grid)
    paths = scheduler.plan_paths(agents)

    if scheduler.total_path_length is None:
        print("No valid cluster path!")
    else:
        print(f"Cluster total path length: {scheduler.total_path_length}\n")

    for agent_id, path in paths.items():
        print(f"{agent_id} Path:")
        if path:
            for x, y, t in path:
                print(f"-> ({x},{y})@t={t}", end=" ")
            print(f"\nLength: {path_length(path)}\n")
        else:
            print("No valid path!\n")
