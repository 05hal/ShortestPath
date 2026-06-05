# -*- coding: utf-8 -*-
import heapq
from collections import defaultdict

class Node:
    def __init__(self, x, y, t=0, parent=None):
        self.x = x
        self.y = y
        self.t = t  # 时间维度
        self.parent = parent
        self.g = 0  # 实际代价
        self.h = 0  # 启发代价
        self.f = 0  # 总代价
    
    def __lt__(self, other):
        return self.f < other.f

def heuristic(a, b):
    # 曼哈顿距离
    return abs(a.x - b.x) + abs(a.y - b.y)

def a_star(grid, start, goal, reservations):
    open_list = []
    closed_set = set()
    
    start_node = Node(start[0], start[1])
    goal_node = Node(goal[0], goal[1])
    
    heapq.heappush(open_list, start_node)
    
    while open_list:
        current = heapq.heappop(open_list)
        
        if current.x == goal_node.x and current.y == goal_node.y:
            path = []
            while current:
                path.append((current.x, current.y, current.t))
                current = current.parent
            return path[::-1]
        
        closed_set.add((current.x, current.y, current.t))
        
        # 生成相邻节点，包含时间维度；(0, 0) 表示车辆停留
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(0,0)]:
            x = current.x + dx
            y = current.y + dy
            t = current.t + 1
            
            if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
                if grid[x][y] == 1:  # 静态障碍检测
                    continue
                
                # 时空冲突检测
                conflict = False
                for check_t in [t-1, t, t+1]:  # 时间缓冲检测
                    if (x, y, check_t) in reservations:
                        conflict = True
                        break
                if conflict:
                    continue
                
                new_node = Node(x, y, t, current)
                new_node.g = current.g + 1
                new_node.h = heuristic(new_node, goal_node)
                new_node.f = new_node.g + new_node.h
                
                if (new_node.x, new_node.y, new_node.t) not in closed_set:
                    heapq.heappush(open_list, new_node)
    
    return None  # 无可行路径

# 多车辆调度器
class MultiAgentScheduler:
    def __init__(self, grid):
        self.grid = grid
        self.reservations = defaultdict(set)  # 时空预定记录
        
    def plan_paths(self, agents):
        # 按优先级排序，距离目标近的车辆优先规划
        sorted_agents = sorted(agents, 
                             key=lambda a: heuristic(
                                 Node(a['start'][0], a['start'][1]),
                                 Node(a['goal'][0], a['goal'][1])
                             ))
        
        results = {}
        for agent in sorted_agents:
            path = a_star(self.grid, 
                         agent['start'], 
                         agent['goal'],
                         self.reservations)
            
            if path:
                # 登记时空路径
                for step in path:
                    for dt in [-1, 0, 1]:  # 时空缓冲
                        self.reservations[(step[0], step[1])].add(step[2]+dt)
                results[agent['id']] = path
            else:
                results[agent['id']] = None
                
        return results

# 测试用例
if __name__ == "__main__":
    # 10x10 网格地图，0 表示可通行，1 表示障碍
    grid = [[0]*10 for _ in range(10)]
    grid[4][3:7] = [1,1,1,1]  # 横向障碍
    
    agents = [
        {'id': 'A', 'start': (0,0), 'goal': (9,9)},
        {'id': 'B', 'start': (9,0), 'goal': (0,9)},
        {'id': 'C', 'start': (4,0), 'goal': (4,9)}
    ]
    
    scheduler = MultiAgentScheduler(grid)
    paths = scheduler.plan_paths(agents)
    
    for agent_id, path in paths.items():
        print(f"{agent_id} Path:")
        if path:
            for x, y, t in path:
                print(f"-> ({x},{y})@t={t}", end=' ')
            print("\n")
        else:
            print("No valid path!\n")
