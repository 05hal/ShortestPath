# -*- coding: utf-8 -*-
import argparse
import heapq
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from experiment_utils import build_center_obstacle_scenario, build_payload
from scalable_planner import cbs_plan, has_complete_solution, prioritized_plan


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


def cluster_makespan(paths):
    valid_paths = [path for path in paths.values() if path]
    if not valid_paths:
        return 0
    return max(path[-1][2] for path in valid_paths)


def get_candidate_positions(grid, position, goal, guided=False):
    candidates = []
    for dx, dy in MOVES:
        next_position = (position[0] + dx, position[1] + dy)
        if in_bounds_and_free(grid, next_position):
            candidates.append(next_position)

    if not guided or not candidates:
        return candidates

    moving_candidates = [candidate for candidate in candidates if candidate != position]
    if not moving_candidates:
        return candidates

    best_distance = min(manhattan(candidate, goal) for candidate in moving_candidates)
    guided_candidates = [
        candidate
        for candidate in moving_candidates
        if manhattan(candidate, goal) == best_distance
    ]
    if position in candidates:
        guided_candidates.append(position)
    return guided_candidates


def multi_agent_a_star(grid, agents, max_time=None, guided=False):
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
        for position, goal in zip(current.positions, goals):
            candidate_lists.append(
                get_candidate_positions(grid, position, goal, guided=guided)
            )

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
    def __init__(self, grid, max_time=None, guided=False):
        self.grid = grid
        self.max_time = max_time
        self.guided = guided
        self.total_path_length = None

    def plan_paths(self, agents):
        paths, total_length = multi_agent_a_star(
            self.grid,
            agents,
            self.max_time,
            guided=self.guided,
        )
        self.total_path_length = total_length
        return paths


def run_experiment(vehicle_count, max_time=None):
    scenario = build_center_obstacle_scenario(vehicle_count)
    grid = scenario["grid"]
    agents = scenario["agents"]
    planner_mode = "centralized"
    planner_note = "3 车基线实验使用集中式联合状态 A*。"

    if vehicle_count <= 3:
        scheduler = MultiAgentScheduler(grid, max_time=max_time, guided=True)
        paths = scheduler.plan_paths(agents)
        total_length = scheduler.total_path_length
    else:
        planner_mode = "cbs"
        planner_note = "车辆数超过 3 时，优先使用 CBS；若冲突树超预算，则回退到预约表重规划。"
        paths = cbs_plan(grid, agents, objective="length")
        if not has_complete_solution(paths):
            planner_mode = "replan"
            planner_note = "CBS 未在预算内收敛，回退到预约表重规划，以保证多车场景可计算。"
            paths = prioritized_plan(grid, agents, objective="length")
        total_length = cluster_path_length(paths)

    makespan = cluster_makespan(paths)

    payload = build_payload(
        algorithm="first_objective",
        file_name="multi_agent_A_star_first_objective.py",
        description="第一目标优化版本",
        note="以集群路径总长度最短为主目标；大规模实验优先使用 CBS，并在必要时回退到预约表重规划。",
        scenario=scenario,
        paths=paths,
        total_length=total_length,
        makespan=makespan,
        planner_mode=planner_mode,
        planner_note=planner_note,
    )

    return payload, paths, total_length, makespan


def parse_args():
    parser = argparse.ArgumentParser(description="第一目标优化实验")
    parser.add_argument("--vehicles", type=int, default=3, help="实验车辆数")
    parser.add_argument("--max-time", type=int, default=None, help="搜索时间上界")
    parser.add_argument("--json", action="store_true", help="输出 JSON 数据")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    payload, paths, total_length, _ = run_experiment(
        vehicle_count=args.vehicles,
        max_time=args.max_time,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if total_length is None:
            print("No valid cluster path!")
        else:
            print(f"Scenario: {payload['scenario']['label']}")
            print(f"Vehicle count: {payload['metrics']['vehicleCount']}")
            print(f"Cluster total path length: {total_length}\n")

        for agent_id, path in paths.items():
            print(f"{agent_id} Path:")
            if path:
                for x, y, t in path:
                    print(f"-> ({x},{y})@t={t}", end=" ")
                print(f"\nLength: {path_length(path)}\n")
            else:
                print("No valid path!\n")
