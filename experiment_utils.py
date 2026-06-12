import string


VEHICLE_COLORS = [
    "#2364aa",
    "#2a9d8f",
    "#e76f51",
    "#ffb703",
    "#8e7dbe",
    "#ef476f",
    "#06d6a0",
    "#118ab2",
    "#f28482",
    "#6a994e",
]


def build_center_obstacle_scenario(vehicle_count):
    if vehicle_count <= 0:
        raise ValueError("vehicle_count must be positive")
    if vehicle_count > len(string.ascii_uppercase):
        raise ValueError("vehicle_count is too large for the built-in id generator")

    rows = 10
    cols = 10
    grid = [[0] * cols for _ in range(rows)]
    for col in range(3, 7):
        grid[4][col] = 1

    # 车辆模板遵循 3 车原始实验的三类运动原则：
    # 1. 左上 -> 右下
    # 2. 左下 -> 右上
    # 3. 中部左侧 -> 中部右侧，穿越障碍附近区域
    # 其他车辆数通过在这三类模式附近对称扩展得到。
    route_templates = [
        ((0, 0), (9, 9)),
        ((9, 0), (0, 9)),
        ((4, 0), (4, 9)),
        ((1, 0), (8, 9)),
        ((8, 0), (1, 9)),
        ((5, 0), (5, 9)),
        ((2, 0), (7, 9)),
        ((7, 0), (2, 9)),
        ((3, 0), (6, 9)),
        ((6, 0), (3, 9)),
    ]

    agents = []
    for index in range(vehicle_count):
        vehicle_id = string.ascii_uppercase[index]
        start, goal = route_templates[index]
        agents.append(
            {
                "id": vehicle_id,
                "start": start,
                "goal": goal,
                "color": VEHICLE_COLORS[index % len(VEHICLE_COLORS)],
            }
        )

    return {
        "name": "center_obstacle",
        "label": "10x10 中部障碍场景",
        "note": "固定 10x10 网格，在第 4 行第 3 至 6 列设置横向障碍；多车场景按 A/B/C 三类原始运动模式做对称扩展。",
        "grid": grid,
        "agents": agents,
    }


def path_length(path):
    if not path:
        return 0
    return sum(
        1
        for previous, current in zip(path, path[1:])
        if (previous[0], previous[1]) != (current[0], current[1])
    )


def build_payload(
    *,
    algorithm,
    file_name,
    description,
    note,
    scenario,
    paths,
    total_length,
    makespan,
    planner_mode="centralized",
    planner_note="",
):
    grid = scenario["grid"]
    agents = scenario["agents"]
    obstacles = [
        [row, col]
        for row in range(len(grid))
        for col in range(len(grid[row]))
        if grid[row][col] == 1
    ]

    vehicles = []
    for agent in agents:
        vehicle_id = agent["id"]
        path = paths.get(vehicle_id)
        vehicles.append(
            {
                "id": vehicle_id,
                "color": agent["color"],
                "start": list(agent["start"]),
                "goal": list(agent["goal"]),
                "path": [[row, col, t] for row, col, t in path] if path else [],
                "length": path_length(path) if path else 0,
            }
        )

    return {
        "algorithm": algorithm,
        "file": file_name,
        "description": description,
        "note": note,
        "scenario": {
            "name": scenario["name"],
            "label": scenario["label"],
            "note": scenario["note"],
            "vehicleCount": len(agents),
        },
        "planner": {
            "mode": planner_mode,
            "note": planner_note,
        },
        "grid": {
            "rows": len(grid),
            "cols": len(grid[0]),
            "obstacles": obstacles,
        },
        "metrics": {
            "vehicleCount": len(agents),
            "totalLength": total_length or 0,
            "makespan": makespan or 0,
        },
        "vehicles": vehicles,
    }
