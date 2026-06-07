const App = (() => {
  const canvas = document.getElementById("map");
  const fileSelect = document.getElementById("fileSelect");
  const fileDescription = document.getElementById("fileDescription");
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

  let datasets = {};
  let active = null;

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

  function updateSidebar(t) {
    fileDescription.textContent = active.description;
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
      ? `当前时间步 t=${t}，车辆 ${waiting.join("、")} 原地停留。${active.note}`
      : `当前时间步 t=${t}，车辆按规划路径运行。${active.note}`;
  }

  function updateComparisonTable() {
    const algoKeys = Object.keys(datasets);
    if (algoKeys.length < 2) return;

    comparisonTable.innerHTML = `
      <thead>
        <tr>
          <th>版本</th>
          <th>总路径长度</th>
          <th>总耗时</th>
          <th>说明</th>
        </tr>
      </thead>
      <tbody>
        ${algoKeys.map(key => {
          const d = datasets[key];
          const isActive = active && active.algorithm === d.algorithm;
          const tag = isActive ? ' style="font-weight:700"' : '';
          return `
            <tr${tag}>
              <td>${d.description}</td>
              <td>${d.metrics.totalLength}</td>
              <td>${d.metrics.makespan}</td>
              <td>${d.note}</td>
            </tr>
          `;
        }).join("")}
      </tbody>
    `;
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

  function switchAlgorithm(key) {
    Player.stop();
    active = datasets[key];
    const mT = maxT(active);
    Player.init(mT, onPlayerUpdate);
    update(0);
    updateComparisonTable();
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

  function handleSwitch(event) {
    switchAlgorithm(event.target.value);
  }

  function init(loadedDatasets) {
    datasets = loadedDatasets;
    const firstKey = Object.keys(datasets)[0];
    if (!firstKey) return;

    active = datasets[firstKey];
    fileSelect.value = firstKey;

    const mT = maxT(active);
    slider.min = "0";
    slider.max = String(mT);

    Player.init(mT, onPlayerUpdate);

    playButton.addEventListener("click", handlePlay);
    resetButton.addEventListener("click", handleReset);
    slider.addEventListener("input", handleSlider);
    fileSelect.addEventListener("change", handleSwitch);

    update(0);
    updateComparisonTable();
  }

  return { init };
})();
