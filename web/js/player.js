const Player = (() => {
  let currentT = 0;
  let playing = false;
  let timer = null;
  let maxT = 0;
  let onUpdate = null;

  function init(maxTime, updateCallback) {
    maxT = maxTime;
    onUpdate = updateCallback;
    currentT = 0;
    playing = false;
  }

  function setMaxT(value) {
    maxT = value;
  }

  function getCurrentT() {
    return currentT;
  }

  function getMaxT() {
    return maxT;
  }

  function isPlaying() {
    return playing;
  }

  function seek(t) {
    stop();
    currentT = Math.max(0, Math.min(t, maxT));
    if (onUpdate) onUpdate(currentT);
  }

  function play() {
    if (currentT >= maxT) {
      currentT = 0;
    }
    playing = true;
    timer = setInterval(() => {
      currentT += 1;
      if (onUpdate) onUpdate(currentT);
      if (currentT >= maxT) {
        stop();
        if (onUpdate) onUpdate(currentT);
      }
    }, 600);
  }

  function stop() {
    playing = false;
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function toggle() {
    if (playing) {
      stop();
    } else {
      play();
    }
    if (onUpdate) onUpdate(currentT);
    return playing;
  }

  return { init, setMaxT, getCurrentT, getMaxT, isPlaying, seek, play, stop, toggle };
})();
