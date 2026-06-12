# ShortestPath

面向多车辆路径规划实验的可视化项目，围绕 `Multi-Agent A*`、`CBS` 和重规划机制，对不同车辆规模下的集群路径优化结果进行生成、对比与展示。

项目当前聚焦两个优化目标：

- 目标一：集群路径总长度最短
- 目标二：在总路径长度受控的前提下，进一步关注集群总耗时

同时，项目提供了前端动画页面，可以按车辆数和算法版本切换查看实验结果。

> [!NOTE]
> 当前实验主场景固定为 `10 x 10` 栅格地图，在第 `4` 行第 `3 ~ 6` 列设置横向静态障碍。`3` 车场景严格使用原始 A/B/C 配置，`5/8/10` 车场景在同一运动原则下扩展。

## Features

- 多车辆路径规划：支持 `3 / 5 / 8 / 10` 辆车实验
- 双目标优化：分别输出目标一和目标二结果
- 多种求解策略：集中式联合状态 A*、CBS、预约表重规划
- 批量数据生成：自动生成前端所需 JSON 和 `manifest`
- 可视化展示：支持动画播放、时间轴拖动、车辆数切换、算法切换和趋势图

## Project Structure

```text
ShortestPath/
├── 目标一/
│   ├── README.md
│   ├── multi_agent_A_star (1).py
│   └── multi_agent_A_star_first_objective.py
├── 目标二/
│   └── multi_agent_A_star_second_objective.py
├── web/
│   ├── css/
│   ├── data/
│   ├── js/
│   └── index.html
├── experiment_utils.py
├── generate_experiments.py
├── scalable_planner.py
└── start.sh
```

各模块职责如下：

- `目标一/`：第一目标优化实现与历史基线代码
- `目标二/`：第二目标优化实现
- `experiment_utils.py`：实验场景、车辆模板、JSON payload 组装
- `scalable_planner.py`：CBS 与预约表重规划等大规模求解逻辑
- `generate_experiments.py`：批量生成 `3/5/8/10` 车辆实验数据
- `web/`：前端页面、渲染器、播放器和数据文件
- `start.sh`：一键生成数据并启动本地可视化服务

## Algorithms

### 目标一

文件：`目标一/multi_agent_A_star_first_objective.py`

- 优化目标：集群路径总长度最短
- 小规模场景：使用集中式联合状态 A*
- 更大规模场景：优先尝试 CBS，必要时回退到预约表重规划

### 目标二

文件：`目标二/multi_agent_A_star_second_objective.py`

- 优化目标：先控制总路径长度，再进一步关注总耗时
- 小规模场景：使用带标签支配的联合状态搜索
- 更大规模场景：优先尝试 CBS，必要时回退到预约表重规划

### 大规模扩展

文件：`scalable_planner.py`

- `CBS`：通过冲突检测与约束分裂，避免集中式联合状态全展开
- `replan`：当 CBS 在预算内无法收敛时，使用预约表进行逐车重规划，确保实验可运行

## Experiment Scenario

默认实验地图为 `10 x 10` 离散栅格：

- `0` 表示可通行区域
- `1` 表示静态障碍

当前基准障碍为：

```python
grid = [[0] * 10 for _ in range(10)]
grid[4][3:7] = [1, 1, 1, 1]
```

`3` 车基线场景为：

```python
agents = [
    {"id": "A", "start": (0, 0), "goal": (9, 9)},
    {"id": "B", "start": (9, 0), "goal": (0, 9)},
    {"id": "C", "start": (4, 0), "goal": (4, 9)},
]
```

其他车辆数场景遵循同一扩展原则：

- 一类车辆：从左上区域驶向右下区域
- 一类车辆：从左下区域驶向右上区域
- 一类车辆：从中部左侧驶向中部右侧，穿越障碍附近

## Getting Started

### Requirements

- Python 3.9+
- macOS / Linux / Windows 均可运行 Python 脚本

### Run Locally

直接运行：

```bash
bash start.sh
```

脚本会自动完成以下工作：

1. 创建 `web/data` 目录
2. 生成 `3,5,8,10` 车辆规模的实验 JSON
3. 自动选择可用端口并启动本地静态服务器

启动后可在浏览器中打开：

```text
http://localhost:8080
```

如果 `8080` 被占用，脚本会自动递增端口。

## Generate Data Only

如只想生成实验数据，不启动页面：

```bash
python3 generate_experiments.py --vehicle-counts 3,5,8,10
```

生成结果包括：

- `web/data/first_objective_*_vehicles.json`
- `web/data/second_objective_*_vehicles.json`
- `web/data/manifest.json`

## Visualization

前端页面支持：

- 按车辆数切换：`3 / 5 / 8 / 10`
- 按算法版本切换：目标一 / 目标二
- 动画播放与暂停
- 时间步滑条拖动
- 当前车辆状态查看
- 总路径长度与总耗时对比
- 不同车辆规模下的趋势图展示

右侧信息栏会显示：

- 实验场景
- 车辆数量
- 规划模式
- 集群路径总长度
- 集群总耗时
- 当前时间步说明

## Current Notes

- `3` 车场景是当前最严格的原始基线实验
- `5` 车场景通常可以直接由 CBS 求解
- `8/10` 车场景在当前约束下冲突密度更高，因此可能出现 `CBS` 回退到 `replan` 的情况

> [!TIP]
> 如果后续需要进一步提升 `8/10` 车场景的最优性和稳定性，可以继续优化 CBS，例如加入更好的冲突选择、`disjoint splitting`、低层搜索启发增强和约束缓存。

## Main Files

- `目标一/multi_agent_A_star_first_objective.py`
- `目标二/multi_agent_A_star_second_objective.py`
- `scalable_planner.py`
- `generate_experiments.py`
- `web/index.html`
- `web/js/app.js`
- `web/js/renderer.js`
- `web/css/style.css`

## Quick Preview

典型使用流程如下：

```bash
# 1. 生成实验数据并启动页面
bash start.sh

# 2. 或仅生成数据
python3 generate_experiments.py --vehicle-counts 3,5,8,10
```

生成完成后，在前端页面中切换不同车辆规模与目标版本，即可查看路径动画和指标对比。
