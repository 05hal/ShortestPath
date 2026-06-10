#!/bin/bash

set -e

PROJECT_DIR="/Users/fengzhu/ShortestPath"
WEB_DIR="$PROJECT_DIR/web"
DATA_DIR="$WEB_DIR/data"

echo "========================================"
echo "  Multi-Agent A* 可视化启动脚本"
echo "========================================"

echo ""
echo "[1/3] 检查目录结构..."
mkdir -p "$DATA_DIR"

echo ""
echo "[2/3] 生成 JSON 数据..."
cd "$PROJECT_DIR"

echo "  - 第一目标优化..."
python3 "目标一/multi_agent_A_star_first_objective.py" --json > "$DATA_DIR/first_objective.json"

echo "  - 第二目标优化..."
python3 "目标二/multi_agent_A_star_second_objective.py" --json > "$DATA_DIR/second_objective.json"

echo ""
echo "[3/3] 启动本地服务器..."
echo "  服务器地址: http://localhost:8080"
echo "  按 Ctrl+C 停止服务器"
echo ""

cd "$WEB_DIR"
python3 -m http.server 8080