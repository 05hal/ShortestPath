#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$PROJECT_DIR/web"
DATA_DIR="$WEB_DIR/data"
VEHICLE_COUNTS="3,5,8,10"
PORT="${PORT:-8080}"

while lsof -i :"$PORT" >/dev/null 2>&1; do
  PORT=$((PORT + 1))
done

echo "========================================"
echo "  Multi-Agent A* 可视化启动脚本"
echo "========================================"

echo ""
echo "[1/3] 检查目录结构..."
mkdir -p "$DATA_DIR"

echo ""
echo "[2/3] 生成 JSON 数据..."
cd "$PROJECT_DIR"

echo "  - 生成车辆规模实验: $VEHICLE_COUNTS"
python3 "generate_experiments.py" --vehicle-counts "$VEHICLE_COUNTS"

echo ""
echo "[3/3] 启动本地服务器..."
echo "  服务器地址: http://localhost:$PORT"
echo "  按 Ctrl+C 停止服务器"
echo ""

cd "$WEB_DIR"
python3 -m http.server "$PORT"
