// Fetches the phone's stats every 2 seconds, animates the wavy indicators with a spring,
// and builds the color palette from a seed color.
const $ = (id) => document.getElementById(id);
const root = document.documentElement;

// ---------- wavy progress indicators ----------
const W = 300, MID = 14, WAVELENGTH = 26, AMPLITUDE = 3.6;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const bars = {};
document.querySelectorAll(".wave").forEach((svg) => {
  bars[svg.dataset.bar] = {
    active: svg.querySelector(".active"), track: svg.querySelector(".track"),
    value: 0, velocity: 0, target: 0,
  };
});
let phase = 0;

function wavePath(length) {
  let d = `M0 ${MID}`;
  for (let x = 2; x <= length; x += 3) {
    d += ` L${x} ${(MID + AMPLITUDE * Math.sin((x / WAVELENGTH) * 2 * Math.PI - phase)).toFixed(2)}`;
  }
  return d;
}

function frame() {
  if (!reduceMotion) phase += 0.07;                   // the wave travels
  for (const b of Object.values(bars)) {
    b.velocity = (b.velocity + (b.target - b.value) * 0.09) * 0.7;   // spring: overshoots, then settles
    b.value += b.velocity;
    const length = Math.max(0, Math.min(W, (b.value / 100) * W));
    b.active.setAttribute("d", wavePath(length));
    b.track.setAttribute("d", `M${Math.min(W, length + 14)} ${MID} L${W} ${MID}`);
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ---------- color from a seed ----------
function hueOf(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  if (d === 0) return 0;
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}

function applySeed(hex) {
  const h = hueOf(hex), set = (k, v) => root.style.setProperty(k, v);
  set("--bg", `hsl(${h} 25% 8%)`);
  set("--card", `hsl(${h} 22% 15%)`);
  set("--track", `hsl(${h} 18% 27%)`);
  set("--text", `hsl(${h} 25% 93%)`);
  set("--muted", `hsl(${h} 12% 70%)`);
  set("--primary", `hsl(${h} 85% 75%)`);
  set("--secondary", `hsl(${(h + 40) % 360} 70% 76%)`);
  set("--tertiary", `hsl(${(h + 110) % 360} 60% 72%)`);
}

const seedInput = $("seed");
let saved = null;
try { saved = localStorage.getItem("seed"); } catch (e) {}
if (saved) seedInput.value = saved;
applySeed(seedInput.value);
seedInput.addEventListener("input", () => {
  applySeed(seedInput.value);
  try { localStorage.setItem("seed", seedInput.value); } catch (e) {}
});

// ---------- live data ----------
let busy = false;
function showStatus(text, kind) { const el = $("status"); el.textContent = text; el.className = "status " + kind; }

async function refresh() {
  if (busy) return;
  busy = true;
  try {
    const response = await fetch("/api/stats", { cache: "no-store" });
    const d = await response.json();
    if (!response.ok || d.error) throw new Error(d.error || "Phone not reachable");

    $("model").textContent = d.model;
    $("battery-level").textContent = d.battery.level_percent;
    $("battery-detail").textContent =
      `${d.battery.status}, ${d.battery.power_source} · ${d.battery.temperature_c} °C · ${d.battery.voltage_v} V · health ${d.battery.health}`;
    $("storage-percent").textContent = d.storage.used_percent;
    $("storage-detail").textContent = `${d.storage.used_gb} of ${d.storage.total_gb} GB used · ${d.storage.free_gb} GB free`;
    $("ram-percent").textContent = d.memory.used_percent;
    $("ram-detail").textContent = `${d.memory.used_gb} of ${d.memory.total_gb} GB used · ${d.memory.available_gb} GB available`;

    bars.battery.target = d.battery.level_percent;
    bars.storage.target = d.storage.used_percent;
    bars.ram.target = d.memory.used_percent;
    showStatus("● Connected · updated " + new Date().toLocaleTimeString(), "ok");
  } catch (error) {
    showStatus("Not connected: " + error.message, "bad");
  } finally {
    busy = false;
  }
}
refresh();
setInterval(refresh, 2000);
