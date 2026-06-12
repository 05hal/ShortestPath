const App = (() => {
  const canvas = document.getElementById("map");
  const vehicleCountSelect = document.getElementById("vehicleCountSelect");
  const algorithmSelect = document.getElementById("algorithmSelect");
  const scenarioLabelEl = document.getElementById("scenarioLabel");
  const vehicleCountEl = document.getElementById("vehicleCount");
  const fileDescription = document.getElementById("fileDescription");
  const plannerModeEl = document.getElementById("plannerMode");
  const totalLengthEl = document.getElementById("totalLength");
  const totalMakespanEl = document.getElementById("totalMakespan");
  const totalTimeEl = document.getElementById("totalTime");
  const legendEl = document.getElementById("legend");
  const playButton = document.getElementById("play");
  const resetButton = document.getElementById("reset");
  const slider = document.getElementById("slider");
  const timeLabel = document.getElementById("time");
  const vehicleTable = document.getElementById("vehicleTable");
  const statusEl = document.getElementById("status");
  const comparisonTable = document.getElementById("comparisonTable");
  const lengthTrendEl = document.getElementById("lengthTrend");
  const makespanTrendEl = document.getElementById("makespanTrend");

  let datasets = {};
  let active = null;
  let activeKey = null;

  function vehicles() {
    return active ? active.vehicles : [];
  }

  function maxT(data) {
    if (!data || !data.vehicles) return 0;
    let maxVal = 0;
    data.vehicles.forEach(v => {
      if (v.path && v.path.length > 0) {
        maxVal = Math.max(maxVal, v.path[v.path.length - 1][2]);
      }
    });
    return maxVal;
  }

  function positionAt(vehicle, t) {
    if (!vehicle.path || vehicle.path.length === 0) return null;
    return vehicle.path[Math.min(t, vehicle.path.length - 1)];
  }

  function movedAt(vehicle, t) {
    if (t === 0) return false;
    const prev = positionAt(vehicle, t - 1);
    const curr = positionAt(vehicle, t);
    if (!prev || !curr) return false;
    return prev[0] !== curr[0] || prev[1] !== curr[1];
  }

  function activeVehicleCount() {
    return active && active.metrics ? active.metrics.vehicleCount : 0;
  }

  function availableVehicleCounts() {
    return [...new Set(Object.values(datasets).map(data => data.metrics.vehicleCount))]
      .sort((left, right) => left - right);
  }

  function availableAlgorithms(count) {
    return Object.entries(datasets)
      .filter(([, data]) => data.metrics.vehicleCount === count)
      .map(([key, data]) => ({ key, algorithm: data.algorithm, description: data.description }))
      .sort((left, right) => left.algorithm.localeCompare(right.algorithm));
  }

  function datasetsForActiveCount() {
    const count = activeVehicleCount();
    return Object.values(datasets).filter(data => data.metrics.vehicleCount === count);
  }

  function syncSelectOptions() {
    const selectedCount = activeVehicleCount();
    const counts = availableVehicleCounts();
    vehicleCountSelect.innerHTML = counts.map(count => `
      <option value="${count}">${count} 辆车</option>
    `).join("");
    vehicleCountSelect.value = String(selectedCount);

    const algorithms = availableAlgorithms(selectedCount);
    algorithmSelect.innerHTML = algorithms.map(item => `
      <option value="${item.key}">${item.description}</option>
    `).join("");
    algorithmSelect.value = activeKey;
  }

  function updateSidebar(t) {
    scenarioLabelEl.textContent = active.scenario ? active.scenario.label : "-";
    vehicleCountEl.textContent = String(activeVehicleCount());
    fileDescription.textContent = active.description;
    plannerModeEl.textContent = active.planner ? active.planner.mode : "-";
    totalLengthEl.textContent = String(active.metrics.totalLength);
    totalMakespanEl.textContent = String(active.metrics.makespan);
    totalTimeEl.textContent = String(maxT(active));
    slider.max = String(maxT(active));
    timeLabel.textContent = `t = ${t} / ${maxT(active)}`;

    legendEl.innerHTML = vehicles().map(v => {
      const start = v.start ? `(${v.start[0]},${v.start[1]})` : "";
      const goal = v.goal ? `(${v.goal[0]},${v.goal[1]})` : "";
      return `
        <div class="legend-item">
          <span class="dot" style="background:${v.color}"></span>
          <span>${v.id}: ${start} 到 ${goal}</span>
          <strong>${v.length}</strong>
        </div>
      `;
    }).join("");

    vehicleTable.innerHTML = vehicles().map(v => {
      const pos = positionAt(v, t);
      if (!pos) return "";
      const [row, col] = pos;
      const state = v.goal && row === v.goal[0] && col === v.goal[1]
        ? "已到达"
        : movedAt(v, t)
          ? "移动"
          : "停留";
      return `
        <tr>
          <td>${v.id}</td>
          <td>(${row}, ${col})</td>
          <td>${state}</td>
        </tr>
      `;
    }).join("");

    const waiting = vehicles()
      .filter(v => !movedAt(v, t) && t !== 0)
      .map(v => v.id);
    statusEl.textContent = waiting.length
      ? `当前时间步 t=${t}，车辆 ${waiting.join("、")} 原地停留。${active.note} ${active.planner ? active.planner.note : ""}`
      : `当前时间步 t=${t}，车辆按规划路径运行。${active.note} ${active.planner ? active.planner.note : ""}`;
  }

  function updateComparisonTable() {
    const currentDatasets = datasetsForActiveCount();
    if (currentDatasets.length === 0) {
      comparisonTable.innerHTML = "";
      return;
    }

    comparisonTable.innerHTML = `
      <thead>
        <tr>
          <th>版本</th>
          <th>车辆数</th>
          <th>总路径长度</th>
          <th>总耗时</th>
          <th>说明</th>
        </tr>
      </thead>
      <tbody>
        ${currentDatasets.map(d => {
          const isActive = active && active.algorithm === d.algorithm;
          const tag = isActive ? ' style="font-weight:700"' : '';
          return `
            <tr${tag}>
              <td>${d.description}</td>
              <td>${d.metrics.vehicleCount}</td>
              <td>${d.metrics.totalLength}</td>
              <td>${d.metrics.makespan}</td>
              <td>${d.note}</td>
            </tr>
          `;
        }).join("")}
      </tbody>
    `;
  }

  function buildTrendSvg(metricKey) {
    const allData = Object.values(datasets)
      .sort((a, b) => a.metrics.vehicleCount - b.metrics.vehicleCount || a.algorithm.localeCompare(b.algorithm));
    if (allData.length === 0) return "";

    const width = 540;
    const height = 220;
    const margin = { top: 18, right: 20, bottom: 40, left: 48 };
    const vehicleCounts = [...new Set(allData.map(data => data.metrics.vehicleCount))];
    const metricValues = allData.map(data => data.metrics[metricKey]);
    const maxMetric = Math.max(...metricValues, 1);
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const xStep = vehicleCounts.length > 1 ? innerWidth / (vehicleCounts.length - 1) : 0;
    const xOf = count => margin.left + vehicleCounts.indexOf(count) * xStep;
    const yOf = value => margin.top + innerHeight - (value / maxMetric) * innerHeight;

    const series = [
      {
        algorithm: "first_objective",
        color: "#0891b2",
        label: "目标一",
        items: allData.filter(data => data.algorithm === "first_objective"),
      },
      {
        algorithm: "second_objective",
        color: "#7c3aed",
        label: "目标二",
        items: allData.filter(data => data.algorithm === "second_objective"),
      },
    ];

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map(ratio => {
      const value = Math.round(maxMetric * ratio);
      const y = margin.top + innerHeight - ratio * innerHeight;
      return `
        <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="#e5e7eb" />
        <text x="${margin.left - 8}" y="${y + 4}" text-anchor="end" fill="#6b7280" font-size="11">${value}</text>
      `;
    }).join("");

    const xLabels = vehicleCounts.map(count => `
      <text x="${xOf(count)}" y="${height - 12}" text-anchor="middle" fill="#6b7280" font-size="11">${count}</text>
    `).join("");

    const seriesSvg = series.map(item => {
      if (item.items.length === 0) return "";
      const points = item.items
        .map(data => `${xOf(data.metrics.vehicleCount)},${yOf(data.metrics[metricKey])}`)
        .join(" ");
      const markers = item.items.map(data => {
        const isActivePoint = active
          && active.algorithm === data.algorithm
          && active.metrics.vehicleCount === data.metrics.vehicleCount;
        return `
          <circle cx="${xOf(data.metrics.vehicleCount)}" cy="${yOf(data.metrics[metricKey])}" r="${isActivePoint ? 6 : 4}" fill="${item.color}" />
        `;
      }).join("");
      return `
        <polyline fill="none" stroke="${item.color}" stroke-width="3" points="${points}" />
        ${markers}
      `;
    }).join("");

    const legend = series.map((item, index) => `
      <g transform="translate(${margin.left + index * 88}, 10)">
        <line x1="0" y1="0" x2="18" y2="0" stroke="${item.color}" stroke-width="3" />
        <text x="24" y="4" fill="#334155" font-size="12">${item.label}</text>
      </g>
    `).join("");

    return `
      <svg viewBox="0 0 ${width} ${height}" width="100%" aria-hidden="true">
        <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
        ${gridLines}
        <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="#94a3b8" />
        <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="#94a3b8" />
        ${xLabels}
        ${seriesSvg}
        ${legend}
      </svg>
    `;
  }

  function updateTrendCharts() {
    lengthTrendEl.innerHTML = buildTrendSvg("totalLength");
    makespanTrendEl.innerHTML = buildTrendSvg("makespan");
  }

  function update(t) {
    Renderer.render(canvas, active, t);
    slider.value = String(t);
    updateSidebar(t);
  }

  function onPlayerUpdate(t) {
    update(t);
    if (!Player.isPlaying()) {
      playButton.textContent = "播放";
    }
  }

  function switchDataset(key) {
    Player.stop();
    activeKey = key;
    active = datasets[key];
    const mT = maxT(active);
    syncSelectOptions();
    Player.init(mT, onPlayerUpdate);
    update(0);
    updateComparisonTable();
    updateTrendCharts();
  }

  function handlePlay() {
    const toggled = Player.toggle();
    playButton.textContent = toggled ? "暂停" : "播放";
    update(Player.getCurrentT());
  }

  function handleReset() {
    Player.stop();
    Player.seek(0);
    playButton.textContent = "播放";
    update(0);
  }

  function handleSlider(event) {
    const t = Number(event.target.value);
    Player.seek(t);
  }

  function handleVehicleCountSwitch(event) {
    const count = Number(event.target.value);
    const match = availableAlgorithms(count)[0];
    if (match) {
      switchDataset(match.key);
    }
  }

  function handleAlgorithmSwitch(event) {
    switchDataset(event.target.value);
  }

  function init(loadedDatasets) {
    datasets = loadedDatasets;
    const firstKey = Object.keys(datasets)
      .sort((left, right) => {
        const leftData = datasets[left];
        const rightData = datasets[right];
        return leftData.metrics.vehicleCount - rightData.metrics.vehicleCount
          || leftData.algorithm.localeCompare(rightData.algorithm);
      })[0];
    if (!firstKey) return;

    activeKey = firstKey;
    active = datasets[firstKey];
    syncSelectOptions();

    const mT = maxT(active);
    slider.min = "0";
    slider.max = String(mT);

    Player.init(mT, onPlayerUpdate);

    playButton.addEventListener("click", handlePlay);
    resetButton.addEventListener("click", handleReset);
    slider.addEventListener("input", handleSlider);
    vehicleCountSelect.addEventListener("change", handleVehicleCountSwitch);
    algorithmSelect.addEventListener("change", handleAlgorithmSwitch);

    update(0);
    updateComparisonTable();
    updateTrendCharts();
  }

  return { init };
})();
