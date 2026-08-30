/**
 * Charlie-yt High-Performance 144 FPS Frontend State Controller
 * Communicates natively with Win32 WebView2 C++ Host.
 */

// Application State
const state = {
  theme: "dark",
  currentInfo: null,
  activeItem: null,
  queuedItems: [],
  completedItems: [],
  selectedFormat: "1080p",
  isDownloading: false,
  isPaused: false,
  logVisible: true,
  isMiniWidget: false
};

// DOM Elements
const dom = {
  html: document.documentElement,
  mainApp: document.getElementById("main-app"),
  miniWidget: document.getElementById("mini-widget"),
  btnTheme: document.getElementById("btn-theme-toggle"),
  btnMiniWidget: document.getElementById("btn-mini-widget"),
  btnMiniExpand: document.getElementById("btn-mini-expand"),
  btnMiniClose: document.getElementById("btn-mini-close"),
  urlInput: document.getElementById("url-input"),
  btnPaste: document.getElementById("btn-paste"),
  btnInspect: document.getElementById("btn-inspect"),
  btnClearUrl: document.getElementById("btn-clear-url"),
  thumbImg: document.getElementById("thumb-img"),
  thumbContainer: document.getElementById("thumb-container"),
  platformBadge: document.getElementById("platform-badge"),
  durationBadge: document.getElementById("duration-badge"),
  mediaTitle: document.getElementById("media-title"),
  mediaAuthor: document.getElementById("media-author"),
  playlistRangeBox: document.getElementById("playlist-range-box"),
  plRangeInput: document.getElementById("pl-range-input"),
  speedVal: document.getElementById("speed-val"),
  sizeDetails: document.getElementById("size-details"),
  progressCircle: document.getElementById("progress-circle"),
  ringPercent: document.getElementById("ring-percent"),
  ringStatus: document.getElementById("ring-status"),
  playlistTrackerCard: document.getElementById("playlist-tracker-card"),
  playlistTrackerTitle: document.getElementById("playlist-tracker-title"),
  playlistItemsList: document.getElementById("playlist-items-list"),
  btnPlSelectAll: document.getElementById("btn-pl-select-all"),
  folderInput: document.getElementById("folder-input"),
  btnBrowseFolder: document.getElementById("btn-browse-folder"),
  btnOpenFolder: document.getElementById("btn-open-folder"),
  formatBtns: document.querySelectorAll(".seg-btn"),
  btnDownloadNow: document.getElementById("btn-download-now"),
  btnAddQueue: document.getElementById("btn-add-queue"),
  btnPause: document.getElementById("btn-pause"),
  btnCancel: document.getElementById("btn-cancel"),
  activeDownloadBox: document.getElementById("active-download-box"),
  queueHeaderTitle: document.getElementById("queue-header-title"),
  btnStartQueue: document.getElementById("btn-start-queue"),
  btnClearQueue: document.getElementById("btn-clear-queue"),
  btnClearHistory: document.getElementById("btn-clear-history"),
  totalQCount: document.getElementById("total-q-count"),
  totalQEta: document.getElementById("total-q-eta"),
  totalQPbar: document.getElementById("total-q-pbar"),
  queueItemsList: document.getElementById("queue-items-list"),
  statusMsgLbl: document.getElementById("status-msg-lbl"),
  btnToggleLog: document.getElementById("btn-toggle-log"),
  logBox: document.getElementById("log-box"),
  miniItemTitle: document.getElementById("mini-item-title"),
  miniPbar: document.getElementById("mini-pbar"),
  miniMetrics: document.getElementById("mini-metrics"),
  btnMiniPause: document.getElementById("btn-mini-pause")
};

// CIRCUMFERENCE of r=54 circle is 2 * PI * 54 = ~339.292
const CIRCUMFERENCE = 2 * Math.PI * 54;

function init() {
  bindEvents();
  loadSavedState();
  sendNativeMessage({ type: "READY" });
}

function bindEvents() {
  // Theme Toggle
  dom.btnTheme.addEventListener("click", toggleTheme);

  // Mini Widget
  dom.btnMiniWidget.addEventListener("click", () => setMiniWidgetMode(true));
  dom.btnMiniExpand.addEventListener("click", () => setMiniWidgetMode(false));
  dom.btnMiniClose.addEventListener("click", () => setMiniWidgetMode(false));
  dom.btnMiniPause.addEventListener("click", togglePause);

  // URL Controls
  dom.btnPaste.addEventListener("click", pasteClipboard);
  dom.btnInspect.addEventListener("click", inspectUrl);
  dom.btnClearUrl.addEventListener("click", clearUrl);
  dom.urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") inspectUrl();
  });

  // Quality pills
  dom.formatBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      dom.formatBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.selectedFormat = btn.getAttribute("data-format");
      log(`Selected format: ${state.selectedFormat}`);
    });
  });

  // Folder Controls
  dom.btnBrowseFolder.addEventListener("click", () => sendNativeMessage({ type: "BROWSE_FOLDER" }));
  dom.btnOpenFolder.addEventListener("click", () => sendNativeMessage({ type: "OPEN_FOLDER", path: dom.folderInput.value }));

  // Actions
  dom.btnDownloadNow.addEventListener("click", downloadNow);
  dom.btnAddQueue.addEventListener("click", addToQueue);
  dom.btnStartQueue.addEventListener("click", startQueue);
  dom.btnPause.addEventListener("click", togglePause);
  dom.btnCancel.addEventListener("click", cancelActiveDownload);

  // Queue actions
  dom.btnClearQueue.addEventListener("click", clearQueued);
  dom.btnClearHistory.addEventListener("click", clearHistory);
  dom.btnPlSelectAll.addEventListener("click", selectAllPlaylistItems);

  // Log drawer
  dom.btnToggleLog.addEventListener("click", () => {
    state.logVisible = !state.logVisible;
    dom.logBox.style.display = state.logVisible ? "block" : "none";
  });

  // Native message listener from C++ Host
  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.addEventListener("message", handleNativeMessage);
  }
}

function toggleTheme() {
  if (state.theme === "dark") {
    state.theme = "light";
    dom.html.className = "light";
    dom.btnTheme.textContent = "☀️ Light";
  } else {
    state.theme = "dark";
    dom.html.className = "dark";
    dom.btnTheme.textContent = "🌙 Dark";
  }
}

function setMiniWidgetMode(isMini) {
  state.isMiniWidget = isMini;
  if (isMini) {
    dom.mainApp.classList.add("hidden");
    dom.miniWidget.classList.remove("hidden");
    sendNativeMessage({ type: "SET_WINDOW_SIZE", width: 340, height: 160, frameless: true, topmost: true });
  } else {
    dom.miniWidget.classList.add("hidden");
    dom.mainApp.classList.remove("hidden");
    sendNativeMessage({ type: "SET_WINDOW_SIZE", width: 1040, height: 960, frameless: false, topmost: false });
  }
}

async function pasteClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      dom.urlInput.value = text.trim();
      inspectUrl();
    }
  } catch (err) {
    sendNativeMessage({ type: "PASTE_CLIPBOARD" });
  }
}

function clearUrl() {
  dom.urlInput.value = "";
  state.currentInfo = null;
  dom.thumbImg.classList.add("hidden");
  dom.thumbImg.src = "";
  dom.thumbContainer.querySelector(".no-thumb-txt").style.display = "block";
  dom.mediaTitle.textContent = "Paste a link above to inspect video or playlist details.";
  dom.mediaAuthor.textContent = "";
  dom.durationBadge.textContent = "";
  dom.platformBadge.textContent = "READY";
  dom.playlistRangeBox.classList.add("hidden");
  dom.playlistTrackerCard.classList.add("hidden");
  setProgress(0, "Ready");
  dom.speedVal.textContent = "0.0";
  dom.sizeDetails.textContent = "0 MB / 0 MB";
  dom.statusMsgLbl.textContent = "Ready to download";
}

function inspectUrl() {
  const url = dom.urlInput.value.trim();
  if (!url) return;

  dom.btnInspect.disabled = true;
  dom.btnInspect.textContent = "...";
  dom.statusMsgLbl.textContent = "Inspecting media source...";
  log(`Inspecting URL: ${url}`);

  sendNativeMessage({
    type: "INSPECT_URL",
    url: url
  });
}

function setProgress(percent, statusText) {
  const pct = Math.min(100, Math.max(0, percent));
  const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;
  dom.progressCircle.style.strokeDashoffset = offset;
  dom.ringPercent.textContent = `${Math.round(pct)}%`;
  if (statusText) dom.ringStatus.textContent = statusText;

  // Mini Widget Sync
  dom.miniPbar.style.width = `${pct}%`;
}

function downloadNow() {
  const url = dom.urlInput.value.trim();
  if (!url) {
    if (state.queuedItems.length > 0) {
      startQueue();
      return;
    }
    alert("Please enter a URL or add items to the queue.");
    return;
  }

  const options = getCurrentOptions();
  const item = createQueueItem(url, state.currentInfo, options);
  state.queuedItems.unshift(item);
  saveState();
  renderQueueUI();
  startQueue();
}

function addToQueue() {
  const url = dom.urlInput.value.trim();
  if (!url) {
    alert("Please enter a URL to add to the queue.");
    return;
  }

  const options = getCurrentOptions();
  const item = createQueueItem(url, state.currentInfo, options);
  state.queuedItems.push(item);
  saveState();
  renderQueueUI();
  log(`Added to Queue: ${item.title} (${options.quality})`);
  dom.statusMsgLbl.textContent = `✓ Added to queue: ${item.title.substring(0, 35)}`;
}

function createQueueItem(url, info, options) {
  return {
    id: Math.random().toString(36).substring(2, 10),
    url: url,
    info: info || { title: "Media Download", platform: { name: "Media", badge: "🎬 Media" } },
    title: info ? info.title : "Media Download",
    platform: (info && info.platform) ? info.platform : { name: "Media", badge: "🎬 Media" },
    options: options,
    status: "Queued",
    progress: 0,
    file_path: "",
    total_bytes: (info && info.filesize) ? info.filesize : 0,
    total_str: (info && info.filesize_str) ? info.filesize_str : "Unknown"
  };
}

function getCurrentOptions() {
  return {
    quality: state.selectedFormat,
    download_dir: dom.folderInput.value.trim(),
    playlist_items: dom.plRangeInput.value.trim()
  };
}

function startQueue() {
  if (state.queuedItems.length === 0) return;
  if (!state.isDownloading) {
    state.isDownloading = true;
    dom.btnDownloadNow.disabled = true;
    dom.btnDownloadNow.textContent = "⏳ PROCESSING QUEUE...";
    dom.btnStartQueue.disabled = true;
    dom.btnPause.disabled = false;
    dom.btnCancel.disabled = false;
    processNextQueueItem();
  }
}

function processNextQueueItem() {
  if (state.queuedItems.length === 0) {
    state.isDownloading = false;
    state.activeItem = null;
    dom.btnDownloadNow.disabled = false;
    dom.btnDownloadNow.textContent = "🚀 DOWNLOAD NOW";
    dom.btnStartQueue.disabled = false;
    dom.btnPause.disabled = true;
    dom.btnCancel.disabled = true;
    setProgress(100, "All Done!");
    dom.statusMsgLbl.textContent = "All downloads finished!";
    renderActiveUI();
    renderQueueUI();
    log("=== All queue downloads finished! ===");
    return;
  }

  state.activeItem = state.queuedItems.shift();
  state.activeItem.status = "Downloading";
  renderActiveUI();
  renderQueueUI();
  saveState();

  dom.statusMsgLbl.textContent = `Downloading: ${state.activeItem.title}...`;
  dom.miniItemTitle.textContent = state.activeItem.title;
  setProgress(0, "Starting...");
  log(`--- Processing: ${state.activeItem.title} ---`);

  sendNativeMessage({
    type: "START_DOWNLOAD",
    item: state.activeItem
  });
}

function togglePause() {
  if (state.isDownloading) {
    state.isPaused = !state.isPaused;
    dom.btnPause.textContent = state.isPaused ? "▶ RESUME" : "⏸ PAUSE";
    dom.btnMiniPause.textContent = state.isPaused ? "▶" : "⏸";
    dom.statusMsgLbl.textContent = state.isPaused ? "Download Paused" : "Resuming download...";
    sendNativeMessage({ type: "TOGGLE_PAUSE", isPaused: state.isPaused });
  }
}

function cancelActiveDownload() {
  if (state.isDownloading) {
    log("Cancelling active download...");
    dom.statusMsgLbl.textContent = "Cancelling active download...";
    sendNativeMessage({ type: "CANCEL_DOWNLOAD" });
  }
}

function moveQueueItem(index, direction) {
  const target = index + direction;
  if (target >= 0 && target < state.queuedItems.length) {
    const item = state.queuedItems.splice(index, 1)[0];
    state.queuedItems.splice(target, 0, item);
    saveState();
    renderQueueUI();
  }
}

function removeQueueItem(id) {
  state.queuedItems = state.queuedItems.filter((i) => i.id !== id);
  state.completedItems = state.completedItems.filter((i) => i.id !== id);
  saveState();
  renderQueueUI();
}

function clearQueued() {
  state.queuedItems = [];
  saveState();
  renderQueueUI();
  log("Pending queued items cleared.");
}

function clearHistory() {
  state.completedItems = [];
  saveState();
  renderQueueUI();
  log("Download history cleared.");
}

function renderActiveUI() {
  if (!state.activeItem) {
    dom.activeDownloadBox.innerHTML = '<p class="empty-txt">No active download in progress.</p>';
    return;
  }

  dom.activeDownloadBox.innerHTML = `
    <div class="item-row">
      <span class="item-badge badge-downloading">${state.activeItem.status.toUpperCase()}</span>
      <span class="item-title">${state.activeItem.platform.badge || "🎬"} ${escapeHtml(state.activeItem.title)} • ${state.activeItem.options.quality}</span>
      <button class="btn btn-danger btn-xs" onclick="cancelActiveDownload()">Stop Active</button>
    </div>
  `;
}

function renderQueueUI() {
  const total = state.queuedItems.length + (state.activeItem ? 1 : 0) + state.completedItems.length;
  const pending = state.queuedItems.length;
  const history = state.completedItems.length;

  dom.queueHeaderTitle.textContent = `📋 Queued Items & History (${pending} pending • ${history} in history)`;

  // Update Total Progress Dashboard
  const completedCount = state.completedItems.length;
  const activeProg = state.activeItem ? (state.activeItem.progress / 100) : 0;
  const overallPct = total > 0 ? Math.round(((completedCount + activeProg) / total) * 100) : 0;

  dom.totalQCount.textContent = `📊 Overall Queue: ${completedCount} of ${total} items Done (${overallPct}%)`;
  dom.totalQPbar.style.width = `${overallPct}%`;

  if (state.queuedItems.length === 0 && state.completedItems.length === 0) {
    dom.queueItemsList.innerHTML = '<p class="empty-txt">No queued downloads or history. Inspect a link and click \'Add to Queue\' to stage downloads.</p>';
    return;
  }

  let html = "";

  // 1. Pending items with ▲ and ▼
  state.queuedItems.forEach((item, idx) => {
    html += `
      <div class="item-row">
        <div class="item-reorder-btns">
          <button class="reorder-btn" ${idx === 0 ? "disabled" : ""} onclick="moveQueueItem(${idx}, -1)">▲</button>
          <button class="reorder-btn" ${idx === state.queuedItems.length - 1 ? "disabled" : ""} onclick="moveQueueItem(${idx}, 1)">▼</button>
        </div>
        <span class="item-badge">${item.status.toUpperCase()}</span>
        <span class="item-title">${item.platform.badge || "🎬"} ${escapeHtml(item.title)} • ${item.options.quality}</span>
        <div class="item-actions">
          <button class="btn btn-secondary btn-xs" onclick="removeQueueItem('${item.id}')">✕</button>
        </div>
      </div>
    `;
  });

  // 2. Completed history items
  state.completedItems.forEach((item) => {
    html += `
      <div class="item-row">
        <span class="item-badge badge-complete">COMPLETE</span>
        <span class="item-title">${item.platform.badge || "🎬"} ${escapeHtml(item.title)} • ${item.options.quality}</span>
        <div class="item-actions">
          ${item.file_path ? `<button class="btn btn-primary btn-xs" onclick="openFile('${escapePath(item.file_path)}')">▶ Play</button>` : ""}
          ${item.file_path ? `<button class="btn btn-secondary btn-xs" onclick="showInFolder('${escapePath(item.file_path)}')">📂</button>` : ""}
          <button class="btn btn-secondary btn-xs" onclick="removeQueueItem('${item.id}')">✕</button>
        </div>
      </div>
    `;
  });

  dom.queueItemsList.innerHTML = html;
}

function openFile(filePath) {
  sendNativeMessage({ type: "OPEN_FILE", path: filePath });
}

function showInFolder(filePath) {
  sendNativeMessage({ type: "SHOW_IN_FOLDER", path: filePath });
}

function selectAllPlaylistItems() {
  if (state.currentInfo && state.currentInfo.entries) {
    state.currentInfo.entries.forEach((e) => e.excluded = false);
    renderPlaylistTracker(state.currentInfo.entries);
  }
}

function togglePlaylistItem(idx) {
  if (state.currentInfo && state.currentInfo.entries) {
    const entry = state.currentInfo.entries.find((e) => e.index === idx);
    if (entry) {
      entry.excluded = !entry.excluded;
      renderPlaylistTracker(state.currentInfo.entries);
    }
  }
}

function renderPlaylistTracker(entries) {
  const activeCount = entries.filter((e) => !e.excluded).length;
  dom.playlistTrackerTitle.textContent = `📑 Playlist Items (${activeCount} of ${entries.length} selected)`;

  let html = "";
  entries.forEach((e) => {
    html += `
      <div class="item-row" style="${e.excluded ? 'opacity: 0.5;' : ''}">
        <span class="meta-txt">#${String(e.index).padStart(2, '0')}</span>
        <span class="item-title">${escapeHtml(e.title)}</span>
        <span class="item-badge">${e.excluded ? 'EXCLUDED' : 'QUEUED'}</span>
        <button class="btn btn-secondary btn-xs" onclick="togglePlaylistItem(${e.index})">${e.excluded ? '+' : '✕'}</button>
      </div>
    `;
  });
  dom.playlistItemsList.innerHTML = html;
}

function log(msg) {
  const time = new Date().toLocaleTimeString();
  dom.logBox.textContent += `[${time}] ${msg}\n`;
  dom.logBox.scrollTop = dom.logBox.scrollHeight;
}

function handleNativeMessage(event) {
  const data = event.data;
  if (!data) return;

  switch (data.type) {
    case "INSPECT_RESULT":
      dom.btnInspect.disabled = false;
      dom.btnInspect.textContent = "🔍 Inspect";
      if (data.success && data.info) {
        state.currentInfo = data.info;
        dom.mediaTitle.textContent = data.info.title;
        dom.mediaAuthor.textContent = `By: ${data.info.uploader || "Creator"}`;
        dom.platformBadge.textContent = data.info.platform ? data.info.platform.badge : "READY";
        dom.durationBadge.textContent = `• ${data.info.duration || "Clip"}`;

        if (data.info.thumbnail) {
          dom.thumbImg.src = data.info.thumbnail;
          dom.thumbImg.classList.remove("hidden");
          dom.thumbContainer.querySelector(".no-thumb-txt").style.display = "none";
        }

        if (data.info.type === "playlist" && data.info.entries) {
          dom.playlistRangeBox.classList.remove("hidden");
          dom.playlistTrackerCard.classList.remove("hidden");
          renderPlaylistTracker(data.info.entries);
        } else {
          dom.playlistRangeBox.classList.add("hidden");
          dom.playlistTrackerCard.classList.add("hidden");
        }

        dom.statusMsgLbl.textContent = `Loaded ${data.info.title.substring(0, 35)}...`;
        log(`Loaded: ${data.info.title}`);
      } else {
        dom.statusMsgLbl.textContent = "Failed to inspect URL.";
        alert(data.error || "Unable to retrieve media details.");
      }
      break;

    case "PROGRESS":
      if (data.percent !== undefined) {
        setProgress(data.percent, state.isPaused ? "Paused" : `ETA ${data.eta || "--"}`);
        dom.speedVal.textContent = data.speed ? data.speed.split(" ")[0] : "0.0";
        dom.sizeDetails.textContent = `${data.downloaded_str || "0 MB"} / ${data.total_str || "0 MB"}`;
        dom.miniMetrics.textContent = `${Math.round(data.percent)}% • ${data.speed || "0.0 MB/s"} • ETA ${data.eta || "--"}`;
        if (state.activeItem) {
          state.activeItem.progress = data.percent;
        }
      }
      break;

    case "DOWNLOAD_COMPLETE":
      if (state.activeItem) {
        state.activeItem.status = "Complete";
        state.activeItem.file_path = data.file_path || "";
        state.completedItems.unshift(state.activeItem);
        log(`✓ Completed: ${state.activeItem.title}`);
      }
      processNextQueueItem();
      break;

    case "DOWNLOAD_ERROR":
      if (state.activeItem) {
        state.activeItem.status = "Failed";
        state.completedItems.unshift(state.activeItem);
        log(`✕ Failed: ${state.activeItem.title} - ${data.error}`);
      }
      processNextQueueItem();
      break;

    case "CONFIG_LOADED":
      if (data.download_dir) {
        dom.folderInput.value = data.download_dir;
      }
      break;
  }
}

function sendNativeMessage(msg) {
  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.postMessage(msg);
  } else {
    console.log("[Native Msg]", msg);
  }
}

function saveState() {
  const queueData = {
    queued: state.queuedItems,
    history: state.completedItems.slice(0, 100)
  };
  localStorage.setItem("charlie_yt_state", JSON.stringify(queueData));
  sendNativeMessage({ type: "SAVE_QUEUE", data: queueData });
}

function loadSavedState() {
  try {
    const raw = localStorage.getItem("charlie_yt_state");
    if (raw) {
      const data = JSON.parse(raw);
      state.queuedItems = data.queued || [];
      state.completedItems = data.history || [];
      renderQueueUI();
    }
  } catch (e) {}
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapePath(str) {
  if (!str) return "";
  return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

// Start
document.addEventListener("DOMContentLoaded", init);
