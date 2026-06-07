# -*- coding: utf-8 -*-
"""
第二优化目标：集群总耗时尽可能短。

优化规则：
1. 第一优先级：集群路径总长度最短。
2. 第二优先级：在集群路径总长度最短的前提下，集群总耗时最短。

这里的“集群总耗时”定义为：
从 t=0 第一辆车从起点出发开始，到所有车辆同时到达各自终点的最早时间。

路径长度计算规则：
- 车辆移动到相邻网格，长度 +1。
- 车辆原地等待，长度 +0。
"""

import heapq
import itertools
import json
import sys
from dataclasses import dataclass


MOVES = (
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0),
    (0, 0),
)


@dataclass(frozen=True)
class SearchNode:
    positions: tuple
    t: int
    g_length: int
    parent: object = None


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cluster_length_heuristic(positions, goals):
    """所有车辆到各自目标点曼哈顿距离之和，是剩余总路径长度的下界。"""
    return sum(manhattan(position, goal) for position, goal in zip(positions, goals))


def makespan_heuristic(positions, goals):
    """所有车辆中距离目标最远者的曼哈顿距离，是剩余总耗时的下界。"""
    if not positions:
        return 0
    return max(manhattan(position, goal) for position, goal in zip(positions, goals))


def path_length(path):
    """计算单车实际移动步数，原地等待不计入路径长度。"""
    if not path:
        return 0

    length = 0
    for previous, current in zip(path, path[1:]):
        previous_position = (previous[0], previous[1])
        current_position = (current[0], current[1])
        if previous_position != current_position:
            length += 1

    return length


def cluster_path_length(paths):
    """计算集群总路径长度。"""
    return sum(path_length(path) for path in paths.values() if path)


def cluster_makespan(paths):
    """计算集群总耗时。"""
    valid_paths = [path for path in paths.values() if path]
    if not valid_paths:
        return 0
    return max(path[-1][2] for path in valid_paths)


def in_bounds_and_free(grid, position):
    x, y = position
    return (
        0 <= x < len(grid)
        and 0 <= y < len(grid[0])
        and grid[x][y] == 0
    )


def has_vertex_conflict(positions):
    """顶点冲突：同一时刻两辆车不能占用同一个网格。"""
    return len(set(positions)) != len(positions)


def has_edge_conflict(previous_positions, next_positions):
    """边冲突：两辆车不能在同一时间步内相向交换位置。"""
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


def is_dominated(existing_labels, new_label):
    """判断新标签是否被已有标签支配。

    label = (路径长度, 当前时间)

    对于同一组联合位置，如果已有状态路径长度更短且时间更早，
    那么新状态没有继续扩展的必要。
    """
    new_length, new_time = new_label

    for old_length, old_time in existing_labels:
        if old_length <= new_length and old_time <= new_time:
            return True

    return False


def add_nondominated_label(existing_labels, new_label):
    """加入非支配标签，并删除被新标签支配的旧标签。"""
    new_length, new_time = new_label

    filtered_labels = []
    for old_length, old_time in existing_labels:
        if not (new_length <= old_length and new_time <= old_time):
            filtered_labels.append((old_length, old_time))

    filtered_labels.append(new_label)
    return filtered_labels


def multi_agent_a_star_second_objective(grid, agents, max_time=None):
    """第二优化目标的集中式 Multi-Agent A*。

    返回：
    - paths：每辆车的时空路径。
    - total_length：集群总路径长度。
    - makespan：集群总耗时。

    搜索优先级：
    1. g_length + h_length 最小。
    2. 当前时间 + h_makespan 最小。
    3. 已用路径长度更小。
    4. 当前时间更小。
    """
    if not agents:
        return {}, 0, 0

    starts = tuple(agent["start"] for agent in agents)
    goals = tuple(agent["goal"] for agent in agents)
    agent_ids = tuple(agent["id"] for agent in agents)

    for position in starts + goals:
        if not in_bounds_and_free(grid, position):
            raise ValueError(f"Invalid start/goal position: {position}")

    if has_vertex_conflict(starts):
        return {agent_id: None for agent_id in agent_ids}, None, None

    if max_time is None:
        free_cells = sum(cell == 0 for row in grid for cell in row)
        lower_makespan = makespan_heuristic(starts, goals)
        lower_total_length = cluster_length_heuristic(starts, goals)
        max_time = max(
            lower_makespan + free_cells * len(agents),
            lower_total_length + free_cells,
            free_cells,
        )

    start = SearchNode(
        positions=starts,
        t=0,
        g_length=0,
        parent=None,
    )

    tie = itertools.count()

    start_length_lower_bound = cluster_length_heuristic(starts, goals)
    start_time_lower_bound = makespan_heuristic(starts, goals)

    open_list = [
        (
            start_length_lower_bound,
            start_time_lower_bound,
            0,
            0,
            next(tie),
            start,
        )
    ]

    labels_by_positions = {
        starts: [(0, 0)]
    }

    while open_list:
        _, _, current_length, current_time, _, current = heapq.heappop(open_list)

        if current_length != current.g_length or current_time != current.t:
            continue

        if current.positions == goals:
            paths = reconstruct_paths(current, agent_ids)
            total_length = cluster_path_length(paths)
            makespan = cluster_makespan(paths)
            return paths, total_length, makespan

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
                previous_position != next_position
                for previous_position, next_position in zip(current.positions, next_positions)
            )

            next_length = current.g_length + move_cost
            next_time = current.t + 1
            next_label = (next_length, next_time)

            existing_labels = labels_by_positions.get(next_positions, [])

            if is_dominated(existing_labels, next_label):
                continue

            labels_by_positions[next_positions] = add_nondominated_label(
                existing_labels,
                next_label,
            )

            next_node = SearchNode(
                positions=next_positions,
                t=next_time,
                g_length=next_length,
                parent=current,
            )

            length_lower_bound = next_length + cluster_length_heuristic(
                next_positions,
                goals,
            )
            time_lower_bound = next_time + makespan_heuristic(
                next_positions,
                goals,
            )

            heapq.heappush(
                open_list,
                (
                    length_lower_bound,
                    time_lower_bound,
                    next_length,
                    next_time,
                    next(tie),
                    next_node,
                ),
            )

    return {agent_id: None for agent_id in agent_ids}, None, None


class MultiAgentScheduler:
    def __init__(self, grid, max_time=None):
        self.grid = grid
        self.max_time = max_time
        self.total_path_length = None
        self.total_makespan = None

    def plan_paths(self, agents):
        paths, total_length, makespan = multi_agent_a_star_second_objective(
            self.grid,
            agents,
            self.max_time,
        )
        self.total_path_length = total_length
        self.total_makespan = makespan
        return paths


if __name__ == "__main__":
    grid = [[0] * 10 for _ in range(10)]
    grid[4][3:7] = [1, 1, 1, 1]

    agents = [
        {"id": "A", "start": (0, 0), "goal": (9, 9)},
        {"id": "B", "start": (9, 0), "goal": (0, 9)},
        {"id": "C", "start": (4, 0), "goal": (4, 9)},
    ]

    output_json = "--json" in sys.argv

    scheduler = MultiAgentScheduler(grid)
    paths = scheduler.plan_paths(agents)

    if output_json:
        obstacles_list = [
            [r, c]
            for r in range(len(grid))
            for c in range(len(grid[r]))
            if grid[r][c] == 1
        ]
        vehicle_colors = {
            "A": "#2364aa",
            "B": "#2a9d8f",
            "C": "#e76f51",
        }
        vehicles_list = []
        for agent in agents:
            vehicle_id = agent["id"]
            path = paths.get(vehicle_id)
            vehicles_list.append({
                "id": vehicle_id,
                "color": vehicle_colors.get(vehicle_id, "#333333"),
                "start": list(agent["start"]),
                "goal": list(agent["goal"]),
                "path": [[row, col, t] for row, col, t in path] if path else [],
                "length": path_length(path) if path else 0,
            })

        payload = {
            "algorithm": "second_objective",
            "file": "multi_agent_A_star_second_objective.py",
            "description": "第二目标优化版本",
            "note": "在集群总路径长度最短的前提下，进一步最小化集群总耗时（最后一辆车到达终点的时间）。",
            "grid": {
                "rows": len(grid),
                "cols": len(grid[0]),
                "obstacles": obstacles_list,
            },
            "metrics": {
                "totalLength": scheduler.total_path_length or 0,
                "makespan": scheduler.total_makespan or 0,
            },
            "vehicles": vehicles_list,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if scheduler.total_path_length is None:
            print("No valid cluster path!")
        else:
            print("Second objective result:")
            print(f"Cluster total path length: {scheduler.total_path_length}")
            print(f"Cluster total makespan: {scheduler.total_makespan}\n")

        for agent_id, path in paths.items():
            print(f"{agent_id} Path:")

            if path:
                for x, y, t in path:
                    print(f"-> ({x},{y})@t={t}", end=" ")

                print(f"\nLength: {path_length(path)}")
                print(f"Arrival time: {path[-1][2]}\n")
            else:
                print("No valid path!\n")
