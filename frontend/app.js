// ---- Chart.js global theme (light) ----
if (window.Chart) {
  Chart.defaults.font.family =
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
  Chart.defaults.color = "#5c6270";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.legend.labels.padding = 16;
}

// ===================== Tabs (segmented control) =====================
const tabButtons = document.querySelectorAll(".tab-btn");
const tabIndicator = document.querySelector(".tab-indicator");
const views = { location: document.getElementById("view-location"), trip: document.getElementById("view-trip") };

function moveTabIndicator(btn) {
  if (!tabIndicator) return;
  tabIndicator.style.width = `${btn.offsetWidth}px`;
  tabIndicator.style.transform = `translateX(${btn.offsetLeft}px)`;
}

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    moveTabIndicator(btn);
    Object.entries(views).forEach(([key, el]) => el.classList.toggle("hidden", key !== btn.dataset.view));
    if (btn.dataset.view === "trip" && tripMap) {
      setTimeout(() => tripMap.invalidateSize(), 50);
    }
  });
});

// position the indicator under the initially-active tab; re-measure once
// more after full load in case icon webfonts shifted button widths
moveTabIndicator(document.querySelector(".tab-btn.active"));
window.addEventListener("load", () => moveTabIndicator(document.querySelector(".tab-btn.active")));
window.addEventListener("resize", () => moveTabIndicator(document.querySelector(".tab-btn.active")));

// ===================== Generic region search picker =====================
function createRegionSearch(inputEl, resultsEl, onSelect) {
  let debounce = null;

  inputEl.addEventListener("input", () => {
    clearTimeout(debounce);
    const q = inputEl.value.trim();
    if (q.length < 3) {
      resultsEl.classList.add("hidden");
      resultsEl.innerHTML = "";
      return;
    }
    debounce = setTimeout(() => runSearch(q), 300);
  });

  document.addEventListener("click", (e) => {
    if (!resultsEl.contains(e.target) && e.target !== inputEl) {
      resultsEl.classList.add("hidden");
    }
  });

  async function runSearch(q) {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      renderResults(data.results || []);
    } catch (err) {
      console.error(err);
    }
  }

  function renderResults(results) {
    if (!results.length) {
      resultsEl.innerHTML = `<li class="no-results"><i class="fa-regular fa-face-frown"></i> Tidak ditemukan. Coba nama kota/kecamatan lain.</li>`;
      resultsEl.classList.remove("hidden");
      return;
    }
    resultsEl.innerHTML = results
      .map(
        (r, i) => `<li data-idx="${i}">
          <i class="fa-solid fa-location-dot result-icon"></i>
          <div class="result-text">
            <div class="name">${r.desa}, ${r.kecamatan}</div>
            <div class="path">${r.kotkab}, ${r.provinsi} — ${r.adm4}</div>
          </div>
        </li>`
      )
      .join("");
    resultsEl.classList.remove("hidden");
    [...resultsEl.children].forEach((li, i) => {
      li.addEventListener("click", () => {
        resultsEl.classList.add("hidden");
        inputEl.value = `${results[i].desa}, ${results[i].kecamatan}`;
        onSelect(results[i]);
      });
    });
  }
}

// ===================== Location (single-place) view =====================
const regionInfo = document.getElementById("region-info");
const regionTitle = document.getElementById("region-title");
const regionTitleText = regionTitle.querySelector("span");
const regionBreadcrumb = document.getElementById("region-breadcrumb");
const statusBanner = document.getElementById("status-banner");
const dashboard = document.getElementById("dashboard");
const nowContent = document.getElementById("now-content");
const metricsContent = document.getElementById("metrics-content");
const bmkgTable = document.getElementById("bmkg-table");
const retrainBtn = document.getElementById("retrain-btn");

let currentAdm4 = null;
let tempChart = null;
let rainChart = null;

function showStatus(el, message, isError = false) {
  const icon = isError
    ? '<i class="fa-solid fa-triangle-exclamation"></i>'
    : '<i class="fa-solid fa-circle-notch fa-spin"></i>';
  el.innerHTML = `${icon} <span>${message}</span>`;
  el.classList.remove("hidden");
  el.classList.toggle("error", isError);
}
function hideStatus(el) {
  el.classList.add("hidden");
}

// Count a number up to its target on first render — small, task-relevant flourish.
function countUp(el) {
  if (!el) return;
  const to = parseFloat(el.dataset.countTo);
  const suffix = el.dataset.countSuffix || "";
  if (!isFinite(to) || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = `${to}${suffix}`;
    return;
  }
  const decimals = (String(to).split(".")[1] || "").length;
  const dur = 650;
  const start = performance.now();
  function frame(now) {
    const p = Math.min(1, (now - start) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = `${(to * eased).toFixed(decimals)}${suffix}`;
    if (p < 1) requestAnimationFrame(frame);
    else el.textContent = `${to}${suffix}`;
  }
  requestAnimationFrame(frame);
}

// Animated "spinning ring + cycling messages + shimmering bar" loading card,
// used for anything that takes a real, sometimes-slow round trip (model
// training, route + weather lookups) so waiting feels alive instead of a
// static spinner. Returns a stop() function to clear its message timer.
function showLoadingCard(el, messages, intervalMs = 1700) {
  el.classList.remove("error");
  el.classList.remove("hidden");
  el.innerHTML = `
    <div class="loading-card">
      <div class="loading-ring-wrap">
        <div class="loading-ring"></div>
        <i class="fa-solid fa-cloud-sun-rain loading-ring-icon"></i>
      </div>
      <span class="loading-text">${messages[0]}</span>
      <div class="loading-bar"><span></span></div>
    </div>
  `;
  const textEl = el.querySelector(".loading-text");
  let i = 0;
  const timer = messages.length > 1
    ? setInterval(() => {
        i = (i + 1) % messages.length;
        textEl.textContent = messages[i];
        textEl.style.animation = "none";
        void textEl.offsetWidth; // force reflow so the fade-in replays
        textEl.style.animation = "";
      }, intervalMs)
    : null;
  return () => { if (timer) clearInterval(timer); };
}

createRegionSearch(document.getElementById("search-input"), document.getElementById("search-results"), selectRegion);

// ===================== Saved locations + history (browser-local) =====================
// ponytail: localStorage, per-browser only; move to a backend table if accounts ever exist
const HISTORY_MAX = 8;
const saveBtn = document.getElementById("save-btn");
let currentRegion = null;

function loadList(key) {
  try { return JSON.parse(localStorage.getItem(key)) || []; } catch { return []; }
}
function storeList(key, list) {
  try { localStorage.setItem(key, JSON.stringify(list)); } catch {}
}
function placeName(r) {
  return `${r.desa}, ${r.kecamatan}`;
}

function renderPlaceRow(rowId, listId, key, removable) {
  const list = loadList(key);
  const row = document.getElementById(rowId);
  const listEl = document.getElementById(listId);
  row.classList.toggle("hidden", !list.length);
  listEl.innerHTML = "";
  list.forEach((r) => {
    const chip = document.createElement("span");
    chip.className = "place-chip";
    const go = document.createElement("button");
    go.type = "button";
    go.textContent = placeName(r);
    go.title = `${r.kotkab}, ${r.provinsi}`;
    go.addEventListener("click", () => {
      document.getElementById("search-input").value = placeName(r);
      selectRegion(r);
    });
    chip.append(go);
    if (removable) {
      const x = document.createElement("button");
      x.type = "button";
      x.className = "place-chip-x";
      x.setAttribute("aria-label", `Hapus ${placeName(r)}`);
      x.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
      x.addEventListener("click", () => toggleSaved(r));
      chip.append(x);
    }
    listEl.append(chip);
  });
}

function renderPlaces() {
  renderPlaceRow("saved-row", "saved-list", "savedPlaces", true);
  renderPlaceRow("history-row", "history-list", "placeHistory", false);
  const saved = currentRegion && loadList("savedPlaces").some((r) => r.adm4 === currentRegion.adm4);
  saveBtn.setAttribute("aria-pressed", String(!!saved));
  saveBtn.title = saved ? "Hapus dari tersimpan" : "Simpan lokasi";
  saveBtn.setAttribute("aria-label", saveBtn.title);
  saveBtn.innerHTML = `<i class="fa-${saved ? "solid" : "regular"} fa-star" aria-hidden="true"></i>`;
}

function toggleSaved(region) {
  const list = loadList("savedPlaces");
  const i = list.findIndex((r) => r.adm4 === region.adm4);
  if (i >= 0) list.splice(i, 1);
  else list.unshift(region);
  storeList("savedPlaces", list);
  renderPlaces();
}

function pushHistory(region) {
  const list = loadList("placeHistory").filter((r) => r.adm4 !== region.adm4);
  list.unshift(region);
  storeList("placeHistory", list.slice(0, HISTORY_MAX));
}

saveBtn.addEventListener("click", () => currentRegion && toggleSaved(currentRegion));
document.getElementById("history-clear").addEventListener("click", () => {
  storeList("placeHistory", []);
  renderPlaces();
});
renderPlaces();

async function selectRegion(region) {
  currentRegion = region;
  pushHistory(region);
  renderPlaces();
  currentAdm4 = region.adm4;
  document.getElementById("location-empty")?.classList.add("hidden");
  regionTitleText.textContent = `${region.desa}, ${region.kecamatan}`;
  regionBreadcrumb.innerHTML = `<i class="fa-solid fa-map"></i> ${region.kotkab}, ${region.provinsi} · kode wilayah ${region.adm4}`;
  regionInfo.classList.remove("hidden");
  dashboard.classList.add("hidden");
  await loadAll();
}

async function loadAll() {
  hideStatus(statusBanner);
  let stopLoading = showLoadingCard(statusBanner, ["Mengambil prakiraan resmi BMKG..."]);
  let live;
  try {
    const res = await fetch(`/api/region/${currentAdm4}/live`);
    if (!res.ok) throw new Error((await res.json()).detail || "Gagal memuat data BMKG");
    live = await res.json();
  } catch (err) {
    stopLoading();
    showStatus(statusBanner, `Gagal mengambil data BMKG: ${err.message}`, true);
    return;
  }

  renderNow(live);
  renderBmkgTable(live.forecast);

  const statusRes = await fetch(`/api/region/${currentAdm4}/model-status`);
  const statusData = await statusRes.json();
  stopLoading();
  stopLoading = showLoadingCard(
    statusBanner,
    statusData.trained
      ? ["Menjalankan prediksi model..."]
      : [
          "Belum ada model untuk lokasi ini...",
          "Mengunduh riwayat cuaca 1.5 tahun terakhir...",
          "Melatih model LSTM...",
          "Mengevaluasi akurasi model...",
          "Hampir selesai (bisa sampai ~1-2 menit)...",
        ],
    1900
  );

  try {
    const res = await fetch(`/api/region/${currentAdm4}/forecast`);
    if (!res.ok) throw new Error((await res.json()).detail || "Gagal melatih/menjalankan model");
    const modelData = await res.json();
    stopLoading();
    // Unhide the dashboard BEFORE drawing the charts: Chart.js measures its
    // canvas on creation, and a canvas inside a display:none container renders
    // at a stale/tiny size and won't reliably resize when it becomes visible.
    dashboard.classList.remove("hidden");
    hideStatus(statusBanner);
    renderModel(modelData, live.forecast);
  } catch (err) {
    stopLoading();
    showStatus(statusBanner, `Gagal menyiapkan model prediksi: ${err.message}`, true);
  }
}

function renderNow(live) {
  const first = live.forecast[0];
  if (!first) {
    nowContent.innerHTML = "<p>Tidak ada data.</p>";
    return;
  }
  nowContent.innerHTML = `
    <div class="now-temp" data-count-to="${first.temperature_c}" data-count-suffix="°C">${first.temperature_c}°C</div>
    <div class="now-desc"><i class="fa-solid fa-cloud"></i> ${first.weather_desc}</div>
    <div class="now-meta">
      <span><i class="fa-solid fa-droplet"></i> ${first.humidity_pct}% kelembapan</span>
      <span><i class="fa-solid fa-wind"></i> ${first.wind_speed_kmh} km/jam</span>
      <span class="now-updated"><i class="fa-regular fa-clock"></i> Diperbarui ${first.datetime}</span>
    </div>
  `;
  countUp(nowContent.querySelector(".now-temp"));
}

function renderBmkgTable(forecast) {
  const rows = forecast
    .slice(0, 16)
    .map(
      (f) => `<tr>
        <td data-label="Waktu">${f.datetime}</td>
        <td data-label="Suhu">${f.temperature_c}°C</td>
        <td data-label="Cuaca">${f.weather_desc}</td>
        <td data-label="Kelembapan">${f.humidity_pct}%</td>
        <td data-label="Angin">${f.wind_speed_kmh} km/j</td>
      </tr>`
    )
    .join("");
  bmkgTable.innerHTML = `
    <table>
      <thead><tr><th>Waktu</th><th>Suhu</th><th>Cuaca</th><th>Kelembapan</th><th>Angin</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function fmtStamp(s) {
  const d = new Date(s);
  return isNaN(d)
    ? s
    : d.toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function renderModel(modelData, bmkgForecast) {
  const m = modelData.model_metrics;
  metricsContent.innerHTML = `
    <div><span class="label"><i class="fa-regular fa-clock"></i> Model dilatih pada:</span> <span class="value">${fmtStamp(modelData.model_trained_at)}</span></div>
    <div><span class="label"><i class="fa-solid fa-temperature-half"></i> MAE suhu (validasi):</span> <span class="value">${m.mae_temperature_2m.toFixed(2)} °C</span></div>
    <div><span class="label"><i class="fa-solid fa-chart-line"></i> RMSE suhu (validasi):</span> <span class="value">${m.rmse_temperature_2m.toFixed(2)} °C</span></div>
    <div><span class="label"><i class="fa-solid fa-cloud-rain"></i> MAE curah hujan (validasi):</span> <span class="value">${m.mae_precipitation.toFixed(2)} mm</span></div>
  `;
  drawCharts(modelData.forecast, bmkgForecast);
}

function hourKey(dateStr) {
  const d = new Date(dateStr.replace(" ", "T"));
  d.setMinutes(0, 0, 0);
  return d.getTime();
}
function fmtLabel(ts) {
  // short "HH.mm" — the chart window is always "24 jam ke depan", so the
  // hour is enough and it keeps the mobile x-axis from becoming a label wall
  const d = new Date(ts);
  return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

function drawCharts(modelForecast, bmkgForecast) {
  const modelByHour = new Map(modelForecast.map((f) => [hourKey(f.datetime), f]));
  const rangeStart = modelForecast.length ? hourKey(modelForecast[0].datetime) : null;
  const rangeEnd = modelForecast.length ? hourKey(modelForecast[modelForecast.length - 1].datetime) : null;

  const bmkgByHour = new Map(
    bmkgForecast
      .map((f) => [hourKey(f.datetime), f])
      .filter(([k]) => rangeStart !== null && k >= rangeStart && k <= rangeEnd)
  );

  const allHours = [...new Set([...modelByHour.keys(), ...bmkgByHour.keys()])].sort((a, b) => a - b);
  const labels = allHours.map(fmtLabel);

  const modelTemp = allHours.map((h) => (modelByHour.has(h) ? modelByHour.get(h).temperature_2m : null));
  const bmkgTemp = allHours.map((h) => (bmkgByHour.has(h) ? bmkgByHour.get(h).temperature_c : null));
  const modelRain = allHours.map((h) => (modelByHour.has(h) ? modelByHour.get(h).precipitation : null));

  if (tempChart) tempChart.destroy();
  if (rainChart) rainChart.destroy();

  const gridColor = "rgba(23, 25, 31, 0.08)";
  const textColor = "#5c6270";
  const accent = "#2f6df0";
  const warm = "#c9691f";

  tempChart = new Chart(document.getElementById("temp-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Model LSTM (°C)", data: modelTemp, borderColor: accent, backgroundColor: accent, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.35, spanGaps: true },
        { label: "BMKG resmi (°C)", data: bmkgTemp, borderColor: warm, backgroundColor: warm, borderWidth: 2, borderDash: [5, 4], pointRadius: 0, pointHoverRadius: 4, tension: 0.35, spanGaps: true },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { color: textColor, maxRotation: 0, autoSkip: true, autoSkipPadding: 14, maxTicksLimit: 8 }, grid: { color: gridColor } },
        y: { ticks: { color: textColor }, grid: { color: gridColor }, border: { display: false } },
      },
      plugins: { legend: { labels: { color: textColor } } },
    },
  });

  rainChart = new Chart(document.getElementById("rain-chart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Curah hujan prediksi (mm/jam)", data: modelRain, backgroundColor: "rgba(47, 109, 240, 0.55)", borderColor: accent, borderWidth: 1, borderRadius: 4, borderSkipped: false }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: textColor, maxRotation: 0, autoSkip: true, autoSkipPadding: 14, maxTicksLimit: 8 }, grid: { color: gridColor } },
        y: { ticks: { color: textColor }, grid: { color: gridColor }, border: { display: false }, beginAtZero: true },
      },
      plugins: { legend: { labels: { color: textColor } } },
    },
  });
}

retrainBtn.addEventListener("click", async () => {
  if (!currentAdm4) return;
  const originalHtml = retrainBtn.innerHTML;
  retrainBtn.disabled = true;
  retrainBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Melatih...';
  const stopLoading = showLoadingCard(statusBanner, [
    "Melatih ulang model dari data terbaru...",
    "Mengunduh riwayat cuaca terkini...",
    "Melatih model LSTM...",
    "Mengevaluasi akurasi model...",
  ], 1900);
  try {
    await fetch(`/api/region/${currentAdm4}/retrain`, { method: "POST" });
    stopLoading();
    await loadAll();
  } catch (err) {
    stopLoading();
    showStatus(statusBanner, `Gagal melatih ulang: ${err.message}`, true);
  } finally {
    retrainBtn.disabled = false;
    retrainBtn.innerHTML = originalHtml;
  }
});

// ===================== Trip planner view =====================
const tripFromInput = document.getElementById("trip-from-input");
const tripToInput = document.getElementById("trip-to-input");
const tripDepartInput = document.getElementById("trip-depart-input");
const tripGoBtn = document.getElementById("trip-go-btn");
const tripSwapBtn = document.getElementById("trip-swap-btn");
const tripStatusBanner = document.getElementById("trip-status-banner");
const tripResults = document.getElementById("trip-results");
const tripWaypointsEl = document.getElementById("trip-waypoints");

let tripFrom = null;
let tripTo = null;
let tripMap = null;
let tripRouteLayer = [];
let tripMarkers = [];

createRegionSearch(tripFromInput, document.getElementById("trip-from-results"), (r) => (tripFrom = r));
createRegionSearch(tripToInput, document.getElementById("trip-to-results"), (r) => (tripTo = r));

// default departure = now (local browser time), min = now
(function initDepartInput() {
  const pad = (n) => String(n).padStart(2, "0");
  const now = new Date();
  const value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  tripDepartInput.value = value;
  tripDepartInput.min = value;
})();

tripSwapBtn.addEventListener("click", () => {
  [tripFrom, tripTo] = [tripTo, tripFrom];
  [tripFromInput.value, tripToInput.value] = [tripToInput.value, tripFromInput.value];
});

tripGoBtn.addEventListener("click", async () => {
  if (!tripFrom || !tripTo) {
    showStatus(tripStatusBanner, "Pilih lokasi asal dan tujuan dari daftar pencarian terlebih dahulu.", true);
    return;
  }
  tripResults.classList.add("hidden");
  const originalHtml = tripGoBtn.innerHTML;
  tripGoBtn.disabled = true;
  tripGoBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Menghitung...';
  const stopLoading = showLoadingCard(
    tripStatusBanner,
    [
      "Menghitung rute terbaik...",
      "Mengambil prakiraan cuaca di sepanjang rute...",
      "Menyusun titik-titik perjalanan...",
      "Hampir selesai...",
    ],
    1400
  );

  try {
    const depart = tripDepartInput.value; // "YYYY-MM-DDTHH:MM"
    const url = `/api/route?from_adm4=${encodeURIComponent(tripFrom.adm4)}&to_adm4=${encodeURIComponent(tripTo.adm4)}&depart=${encodeURIComponent(depart)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error((await res.json()).detail || "Gagal menghitung rute");
    const data = await res.json();
    stopLoading();
    // Reveal the results section (and the map container inside it) BEFORE
    // rendering the map - Leaflet can't measure a display:none container,
    // so initializing/fitBounds-ing while still hidden produces a broken
    // zoom/pan that never corrects itself.
    hideStatus(tripStatusBanner);
    tripResults.classList.remove("hidden");
    renderTrip(data);
  } catch (err) {
    stopLoading();
    showStatus(tripStatusBanner, `Gagal merencanakan perjalanan: ${err.message}`, true);
  } finally {
    tripGoBtn.disabled = false;
    tripGoBtn.innerHTML = originalHtml;
  }
});

function fmtDateTime(iso) {
  return new Date(iso).toLocaleString("id-ID", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function fmtDuration(min) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h} jam ${m} menit` : `${m} menit`;
}

function renderTrip(data) {
  document.getElementById("trip-distance").textContent = `${data.distance_km} km`;
  document.getElementById("trip-duration").textContent = fmtDuration(data.duration_min);
  document.getElementById("trip-arrival").textContent = fmtDateTime(data.arrival);

  renderTripMap(data);
  renderTripWaypoints(data.waypoints);
}

// darker than the map legend swatches on purpose: these also tint small
// bold text on white chips, which needs a real 4.5:1 contrast ratio
function rainColor(pct) {
  if (pct < 20) return "#1f7a44";
  if (pct < 50) return "#946412";
  return "#b8402f";
}

function renderTripMap(data) {
  if (!tripMap) {
    tripMap = L.map("trip-map", { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(tripMap);
  }

  tripRouteLayer.forEach((layer) => tripMap.removeLayer(layer));
  tripRouteLayer = [];
  tripMarkers.forEach((m) => tripMap.removeLayer(m));
  tripMarkers = [];

  // route line, drawn as separate coloured segments so the line itself
  // shows where along the trip rain is more/less likely
  const bounds = [];
  data.segments.forEach((seg) => {
    const latlngs = seg.coords.map(([lat, lon]) => [lat, lon]);
    const layer = L.polyline(latlngs, {
      color: seg.color,
      weight: 6,
      opacity: 0.9,
      lineCap: "round",
    }).addTo(tripMap);
    layer.bindTooltip(`Peluang hujan di ruas ini: ${seg.rain_probability_pct}%`, { sticky: true });
    tripRouteLayer.push(layer);
    latlngs.forEach((ll) => bounds.push(ll));
  });

  // one weather-icon marker per sampled waypoint along the route
  data.waypoints.forEach((w, i) => {
    const isEndpoint = i === 0 || i === data.waypoints.length - 1;
    const icon = tripDivIcon(w.weather_icon, rainColor(w.rain_probability_pct), isEndpoint);
    const marker = L.marker([w.lat, w.lon], { icon }).addTo(tripMap);
    marker.bindPopup(`
      <b>${w.label}</b><br/>
      <i class="fa-regular fa-clock"></i> ${fmtDateTime(w.eta)}<br/>
      <i class="fa-solid ${w.weather_icon}"></i> ${w.weather_label} · ${w.temperature_c}°C<br/>
      <i class="fa-solid fa-droplet"></i> Peluang hujan: ${w.rain_probability_pct}%
    `);
    tripMarkers.push(marker);
  });

  const latLngBounds = L.latLngBounds(bounds);
  tripMap.fitBounds(latLngBounds, { padding: [30, 30] });

  // The container may have just become visible (was display:none), so its
  // size wasn't measurable yet when fitBounds ran above. Re-measure and
  // re-fit once the browser has actually laid it out, so the route is
  // guaranteed to end up fully framed instead of stuck at the default zoom.
  requestAnimationFrame(() => {
    tripMap.invalidateSize();
    tripMap.fitBounds(latLngBounds, { padding: [30, 30] });
  });
}

function tripDivIcon(faClass, color, isEndpoint) {
  const size = isEndpoint ? 34 : 28;
  const ring = isEndpoint ? `box-shadow: 0 0 0 3px rgba(255,255,255,0.92), 0 2px 10px rgba(20,22,28,0.4);` : "";
  return L.divIcon({
    className: "trip-marker",
    html: `<span style="background:${color}; width:${size}px; height:${size}px; ${ring}"><i class="fa-solid ${faClass}"></i></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function renderTripWaypoints(waypoints) {
  tripWaypointsEl.innerHTML = waypoints
    .map(
      (w) => `
      <div class="waypoint-chip glass">
        <div class="wp-label">${w.label}</div>
        <div class="wp-time"><i class="fa-regular fa-clock"></i> ${fmtDateTime(w.eta)}</div>
        <div class="wp-icon" style="color:${rainColor(w.rain_probability_pct)}"><i class="fa-solid ${w.weather_icon}"></i></div>
        <div class="wp-temp">${w.temperature_c}°C</div>
        <div class="wp-desc">${w.weather_label}</div>
        <div class="wp-rain-prob" style="color:${rainColor(w.rain_probability_pct)}">
          <i class="fa-solid fa-umbrella"></i> ${w.rain_probability_pct}% hujan
        </div>
        <div class="wp-rain"><i class="fa-solid fa-droplet"></i> ${w.precipitation_mm} mm</div>
      </div>`
    )
    .join("");
}

// ===================== Scroll reveal (progressive enhancement) =====================
// Bands settle in as they enter the viewport. Without JS or an observer, or
// with reduced-motion, everything just stays visible.
(function initReveal() {
  const els = document.querySelectorAll("[data-reveal]");
  if (!els.length) return;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (!("IntersectionObserver" in window)) return;

  els.forEach((el) => el.classList.add("reveal-pending"));
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        e.target.classList.add("reveal-in");
        io.unobserve(e.target);
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.06 }
  );
  els.forEach((el) => io.observe(el));
})();
