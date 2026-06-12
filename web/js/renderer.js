const Renderer = (() => {

  function cellSize(canvas, gridRows, gridCols) {
    return Math.min(canvas.width / gridCols, canvas.height / gridRows);
  }

  function centerOf(canvas, gridRows, gridCols, row, col) {
    const size = cellSize(canvas, gridRows, gridCols);
    return {
      x: col * size + size / 2,
      y: row * size + size / 2
    };
  }

  function drawGrid(ctx, canvas, gridRows, gridCols, obstacles) {
    const size = cellSize(canvas, gridRows, gridCols);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i <= gridCols; i += 1) {
      ctx.beginPath();
      ctx.moveTo(i * size, 0);
      ctx.lineTo(i * size, canvas.height);
      ctx.strokeStyle = "#e7ebf2";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    for (let i = 0; i <= gridRows; i += 1) {
      ctx.beginPath();
      ctx.moveTo(0, i * size);
      ctx.lineTo(canvas.width, i * size);
      ctx.strokeStyle = "#e7ebf2";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    ctx.fillStyle = "#2f3542";
    obstacles.forEach(([row, col]) => {
      ctx.fillRect(col * size + 2, row * size + 2, size - 4, size - 4);
    });

    ctx.fillStyle = "#667085";
    ctx.font = "12px Segoe UI, Arial";
    for (let i = 0; i < gridRows; i += 1) {
      ctx.fillText(String(i), 6, i * size + 16);
    }
    for (let i = 0; i < gridCols; i += 1) {
      ctx.fillText(String(i), i * size + 6, 16);
    }
  }

  function drawPath(ctx, canvas, gridRows, gridCols, vehicle) {
    const size = cellSize(canvas, gridRows, gridCols);
    if (!vehicle.path || vehicle.path.length === 0) return;

    ctx.beginPath();
    vehicle.path.forEach(([row, col], index) => {
      const point = centerOf(canvas, gridRows, gridCols, row, col);
      if (index === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.strokeStyle = vehicle.color;
    ctx.lineWidth = Math.max(3, size * 0.05);
    ctx.globalAlpha = 0.28;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function drawStartGoal(ctx, canvas, gridRows, gridCols, vehicle) {
    const size = cellSize(canvas, gridRows, gridCols);
    const start = centerOf(canvas, gridRows, gridCols, vehicle.start[0], vehicle.start[1]);
    const goal = centerOf(canvas, gridRows, gridCols, vehicle.goal[0], vehicle.goal[1]);

    ctx.fillStyle = vehicle.color;
    ctx.globalAlpha = 0.18;
    ctx.fillRect(start.x - size * 0.28, start.y - size * 0.28, size * 0.56, size * 0.56);
    ctx.globalAlpha = 1;

    ctx.strokeStyle = vehicle.color;
    ctx.lineWidth = 3;
    ctx.strokeRect(goal.x - size * 0.26, goal.y - size * 0.26, size * 0.52, size * 0.52);
  }

  function drawVehicle(ctx, canvas, gridRows, gridCols, vehicle, t) {
    const size = cellSize(canvas, gridRows, gridCols);
    const pos = vehicle.path[Math.min(t, vehicle.path.length - 1)];
    if (!pos) return;
    const [row, col] = pos;
    const point = centerOf(canvas, gridRows, gridCols, row, col);

    ctx.beginPath();
    ctx.arc(point.x, point.y, size * 0.27, 0, Math.PI * 2);
    ctx.fillStyle = vehicle.color;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.font = `700 ${Math.max(11, Math.round(size * 0.28))}px Segoe UI, Arial`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(vehicle.id.slice(0, 2), point.x, point.y + 1);
  }

  function render(canvas, data, currentT) {
    const ctx = canvas.getContext("2d");
    const { grid, vehicles } = data;
    const gridRows = grid.rows;
    const gridCols = grid.cols;

    drawGrid(ctx, canvas, gridRows, gridCols, grid.obstacles);
    vehicles.forEach(v => drawPath(ctx, canvas, gridRows, gridCols, v));
    vehicles.forEach(v => drawStartGoal(ctx, canvas, gridRows, gridCols, v));
    vehicles.forEach(v => drawVehicle(ctx, canvas, gridRows, gridCols, v, currentT));
  }

  return { render };
})();
