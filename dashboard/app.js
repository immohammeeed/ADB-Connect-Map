// Asks the local server for the phone's stats every 2 seconds and updates the page.
const $ = (id) => document.getElementById(id);
let busy = false;

function setBar(id, percent) {
  $(id).style.width = percent + "%";
}

function showStatus(text, kind) {
  const el = $("status");
  el.textContent = text;
  el.className = "status " + kind;
}

async function refresh() {
  if (busy) return;   // don't start a new request while the last one is still running
  busy = true;
  try {
    const response = await fetch("/api/stats", { cache: "no-store" });
    const d = await response.json();
    if (!response.ok || d.error) throw new Error(d.error || "Phone not reachable");

    $("model").textContent = d.model;

    $("battery-level").textContent = d.battery.level_percent;
    setBar("battery-bar", d.battery.level_percent);
    $("battery-detail").textContent =
      `${d.battery.status}, ${d.battery.power_source} · ${d.battery.temperature_c} °C · ` +
      `${d.battery.voltage_v} V · health ${d.battery.health}`;

    $("storage-percent").textContent = d.storage.used_percent;
    setBar("storage-bar", d.storage.used_percent);
    $("storage-detail").textContent =
      `${d.storage.used_gb} of ${d.storage.total_gb} GB used · ${d.storage.free_gb} GB free`;

    $("ram-percent").textContent = d.memory.used_percent;
    setBar("ram-bar", d.memory.used_percent);
    $("ram-detail").textContent =
      `${d.memory.used_gb} of ${d.memory.total_gb} GB used · ${d.memory.available_gb} GB available`;

    showStatus("Connected · updated " + new Date().toLocaleTimeString(), "ok");
  } catch (error) {
    showStatus("Not connected: " + error.message, "bad");
  } finally {
    busy = false;
  }
}

refresh();
setInterval(refresh, 2000);
