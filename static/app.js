"use strict";

const $ = id => document.getElementById(id);
const qs = (sel, root = document) => root.querySelector(sel);

// Max visual rotation of the wheel rotor at LX = ±32767. A typical cheap wheel
// physically rotates 90-135° per side; if your wheel turns farther (sim wheels
// do 450° each side), bump this up. Pure cosmetic — does not affect what games see.
const WHEEL_VIS_MAX_DEG = 90;

const AXIS_FIELDS = [
  { key: "inner_deadzone_pct",   label: "input deadzone (ignore tiny inputs)",          min: 0,   max: 99,  step: 1 },
  { key: "outer_saturation_pct", label: "input saturation (treat near-max as max)",     min: 1,   max: 100, step: 1 },
  { key: "output_min_pct",       label: "output floor (jump past game's deadzone)",     min: 0,   max: 100, step: 1 },
  { key: "output_max_pct",       label: "output ceiling (cap virtual output)",          min: 0,   max: 100, step: 1 },
  { key: "curve_power",          label: "curve power (1=linear, >1=less center sens.)", min: 0.1, max: 4.0, step: 0.05 },
];

const state = {
  profile: null,
  profileNames: [],
  snapshot: null,
  allButtons: [],
};

function unipolarRemap(x, cfg) {
  if (cfg.invert) x = 1 - x;
  const inner = cfg.inner_deadzone_pct / 100;
  const outer = cfg.outer_saturation_pct / 100;
  const outMin = cfg.output_min_pct / 100;
  const outMax = cfg.output_max_pct / 100;
  if (x <= inner) return 0;
  if (x >= outer) return outMax;
  const norm = (x - inner) / Math.max(outer - inner, 1e-9);
  const shaped = Math.pow(norm, cfg.curve_power);
  return outMin + shaped * (outMax - outMin);
}

function bipolarRemap(x, cfg) {
  const inverted = cfg.invert ? -x : x;
  const sign = inverted >= 0 ? 1 : -1;
  const mag = Math.abs(inverted);
  const inner = cfg.inner_deadzone_pct / 100;
  const outer = cfg.outer_saturation_pct / 100;
  const outMin = cfg.output_min_pct / 100;
  const outMax = cfg.output_max_pct / 100;
  if (mag <= inner) return 0;
  if (mag >= outer) return sign * outMax;
  const norm = (mag - inner) / Math.max(outer - inner, 1e-9);
  const shaped = Math.pow(norm, cfg.curve_power);
  return sign * (outMin + shaped * (outMax - outMin));
}

function api(method, path, body) {
  return fetch("/api" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  }).then(r => {
    if (!r.ok) throw new Error(`${method} ${path}: ${r.status}`);
    return r.json();
  });
}

let pendingPushTimer = null;
function pushActive() {
  if (pendingPushTimer) clearTimeout(pendingPushTimer);
  pendingPushTimer = setTimeout(() => {
    api("POST", "/profiles/active", state.profile).catch(console.error);
  }, 40);
}

function buildAxisControls(panel) {
  const axis = panel.dataset.axis;
  const kind = panel.dataset.kind;
  const controls = qs(".controls", panel);
  controls.innerHTML = "";

  for (const field of AXIS_FIELDS) {
    const row = document.createElement("div");
    row.className = "row";

    const label = document.createElement("label");
    label.textContent = field.label;
    label.setAttribute("for", `${axis}-${field.key}`);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = field.min;
    slider.max = field.max;
    slider.step = field.step;
    slider.id = `${axis}-${field.key}-slider`;
    slider.dataset.axis = axis;
    slider.dataset.field = field.key;

    const number = document.createElement("input");
    number.type = "number";
    number.min = field.min;
    number.max = field.max;
    number.step = field.step;
    number.id = `${axis}-${field.key}`;
    number.dataset.axis = axis;
    number.dataset.field = field.key;

    const sliderCell = document.createElement("div");
    sliderCell.style.minWidth = 0;
    sliderCell.appendChild(slider);

    controls.appendChild(label);
    controls.appendChild(sliderCell);
    controls.appendChild(document.createElement("div"));
    controls.appendChild(number);

    const sync = (src) => {
      const v = parseFloat(src.value);
      slider.value = v;
      number.value = v;
      state.profile[axis][field.key] = v;
      drawCurve(panel);
      pushActive();
    };
    slider.addEventListener("input", () => sync(slider));
    number.addEventListener("change", () => sync(number));
  }

  const invertWrap = document.createElement("label");
  invertWrap.className = "invert";
  const invert = document.createElement("input");
  invert.type = "checkbox";
  invert.id = `${axis}-invert`;
  invert.addEventListener("change", () => {
    state.profile[axis].invert = invert.checked;
    drawCurve(panel);
    pushActive();
  });
  invertWrap.appendChild(invert);
  invertWrap.appendChild(document.createTextNode("invert direction"));
  controls.appendChild(invertWrap);
}

function syncAxisInputs(panel) {
  const axis = panel.dataset.axis;
  const cfg = state.profile[axis];
  for (const field of AXIS_FIELDS) {
    const v = cfg[field.key];
    const s = $(`${axis}-${field.key}-slider`);
    const n = $(`${axis}-${field.key}`);
    if (s) s.value = v;
    if (n) n.value = v;
  }
  const inv = $(`${axis}-invert`);
  if (inv) inv.checked = !!cfg.invert;
}

function drawCurve(panel) {
  const axis = panel.dataset.axis;
  const kind = panel.dataset.kind;
  const cfg = state.profile[axis];
  const path = $(`curve-${axis}`);

  const W = 120, H = 100;
  const pts = [];
  const N = 100;
  if (kind === "bipolar") {
    for (let i = 0; i <= N; i++) {
      const x = -1 + (2 * i) / N;
      const y = bipolarRemap(x, cfg);
      const px = W / 2 + x * (W / 2);
      const py = H / 2 - y * (H / 2);
      pts.push(`${px.toFixed(2)},${py.toFixed(2)}`);
    }
  } else {
    for (let i = 0; i <= N; i++) {
      const x = i / N;
      const y = unipolarRemap(x, cfg);
      const px = x * W;
      const py = H - y * H;
      pts.push(`${px.toFixed(2)},${py.toFixed(2)}`);
    }
  }
  path.setAttribute("d", "M" + pts.join(" L "));
}

function buildRemapGrid() {
  const grid = $("remap-grid");
  grid.innerHTML = "";
  for (const phys of state.allButtons) {
    const row = document.createElement("div");
    row.className = "remap-row";
    row.id = `remap-${phys}`;

    const physEl = document.createElement("span");
    physEl.className = "phys";
    physEl.textContent = phys;

    const arrow = document.createElement("span");
    arrow.className = "arrow";
    arrow.textContent = "→";

    const sel = document.createElement("select");
    for (const target of state.allButtons) {
      const opt = document.createElement("option");
      opt.value = target;
      opt.textContent = target;
      sel.appendChild(opt);
    }
    sel.value = state.profile.button_remap[phys] || phys;
    sel.addEventListener("change", () => {
      state.profile.button_remap[phys] = sel.value;
      pushActive();
    });

    row.appendChild(physEl);
    row.appendChild(arrow);
    row.appendChild(sel);
    grid.appendChild(row);
  }
}

function syncRemap() {
  for (const phys of state.allButtons) {
    const row = $(`remap-${phys}`);
    if (!row) continue;
    const sel = qs("select", row);
    if (sel) sel.value = state.profile.button_remap[phys] || phys;
  }
}

function renderButtonGrids(allButtons) {
  for (const id of ["buttons-real", "buttons-virtual"]) {
    const el = $(id);
    el.innerHTML = "";
    for (const name of allButtons) {
      const div = document.createElement("div");
      div.className = "btn";
      div.dataset.name = name;
      div.textContent = name;
      el.appendChild(div);
    }
  }
}

function updateLive(s) {
  state.snapshot = s;
  if (state.allButtons.length === 0) {
    state.allButtons = s.all_buttons;
    renderButtonGrids(s.all_buttons);
  }

  $("status").textContent = s.connected ? "wheel connected" : "wheel disconnected";
  $("status").className = "status " + (s.connected ? "ok" : "bad");
  $("real-slot").textContent = s.real_slot;
  $("virtual-slot").textContent = s.virtual_slot ?? "-";
  $("hz").textContent = s.hz;

  const ang = (s.real.lx / 32767) * WHEEL_VIS_MAX_DEG;
  $("wheel-rotor").setAttribute("transform", `rotate(${ang})`);
  const angV = (s.virtual.lx / 32767) * WHEEL_VIS_MAX_DEG;
  $("wheel-rotor-virtual").setAttribute("transform", `rotate(${angV})`);

  $("lt-fill").style.width = (s.real.lt / 255 * 100) + "%";
  $("rt-fill").style.width = (s.real.rt / 255 * 100) + "%";
  $("vlt-fill").style.width = (s.virtual.lt / 255 * 100) + "%";
  $("vrt-fill").style.width = (s.virtual.rt / 255 * 100) + "%";
  $("lt-val").textContent = s.real.lt;
  $("rt-val").textContent = s.real.rt;
  $("vlt-val").textContent = s.virtual.lt;
  $("vrt-val").textContent = s.virtual.rt;

  for (const name of s.all_buttons) {
    const r = qs(`#buttons-real .btn[data-name="${name}"]`);
    const v = qs(`#buttons-virtual .btn[data-name="${name}"]`);
    if (r) r.classList.toggle("on", s.real_button_names.includes(name));
    if (v) v.classList.toggle("on", s.virtual_button_names.includes(name));
    const row = $(`remap-${name}`);
    if (row) row.classList.toggle("pressed", s.real_button_names.includes(name));
  }

  $("real-lx").textContent = s.real.lx;
  $("real-lt").textContent = s.real.lt;
  $("real-rt").textContent = s.real.rt;
  $("real-ly").textContent = s.real.ly;
  $("real-rx").textContent = s.real.rx;
  $("real-ry").textContent = s.real.ry;
  $("real-btns").textContent = "0x" + s.real.buttons.toString(16).padStart(4, "0");
  $("virt-lx").textContent = s.virtual.lx;
  $("virt-lt").textContent = s.virtual.lt;
  $("virt-rt").textContent = s.virtual.rt;
  $("virt-ly").textContent = s.virtual.ly;
  $("virt-rx").textContent = s.virtual.rx;
  $("virt-ry").textContent = s.virtual.ry;
  $("virt-btns").textContent = "0x" + s.virtual.buttons.toString(16).padStart(4, "0");

  // input dot on curve plots
  if (state.profile) {
    const lxN = s.real.lx / 32767;
    const dotS = $("dot-steering");
    dotS.setAttribute("cx", 60 + lxN * 60);
    dotS.setAttribute("cy", 50 - bipolarRemap(lxN, state.profile.steering) * 50);

    const ltN = s.real.lt / 255;
    const dotB = $("dot-brake");
    dotB.setAttribute("cx", ltN * 120);
    dotB.setAttribute("cy", 100 - unipolarRemap(ltN, state.profile.brake) * 100);

    const rtN = s.real.rt / 255;
    const dotT = $("dot-throttle");
    dotT.setAttribute("cx", rtN * 120);
    dotT.setAttribute("cy", 100 - unipolarRemap(rtN, state.profile.throttle) * 100);
  }
}

function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/live`);
  ws.onmessage = ev => {
    try { updateLive(JSON.parse(ev.data)); } catch (e) { console.error(e); }
  };
  ws.onclose = () => {
    $("status").textContent = "disconnected, retrying…";
    $("status").className = "status bad";
    setTimeout(connectWS, 1000);
  };
}

async function loadProfiles() {
  const list = await api("GET", "/profiles");
  state.profileNames = list.profiles;
  const sel = $("profile-select");
  sel.innerHTML = "";
  for (const n of list.profiles) {
    const opt = document.createElement("option");
    opt.value = n;
    opt.textContent = n;
    sel.appendChild(opt);
  }
  sel.value = list.active;
  const profile = await api("GET", `/profiles/${encodeURIComponent(list.active)}`);
  state.profile = profile;
  document.querySelectorAll(".panel.editor").forEach(p => {
    syncAxisInputs(p);
    drawCurve(p);
  });
  if (state.allButtons.length) buildRemapGrid();
}

async function init() {
  document.querySelectorAll(".panel.editor").forEach(buildAxisControls);

  $("profile-select").addEventListener("change", async (e) => {
    const name = e.target.value;
    await api("POST", `/profiles/${encodeURIComponent(name)}/activate`);
    await loadProfiles();
  });
  $("btn-save").addEventListener("click", async () => {
    const name = state.profile.name;
    await api("PUT", `/profiles/${encodeURIComponent(name)}`, state.profile);
    flash($("btn-save"), "saved");
  });
  $("btn-new").addEventListener("click", async () => {
    const name = prompt("name for new profile:");
    if (!name) return;
    const newProfile = JSON.parse(JSON.stringify(state.profile));
    newProfile.name = name;
    await api("PUT", `/profiles/${encodeURIComponent(name)}`, newProfile);
    await api("POST", `/profiles/${encodeURIComponent(name)}/activate`);
    await loadProfiles();
  });
  $("btn-delete").addEventListener("click", async () => {
    const name = state.profile.name;
    if (name === "default") { alert("can't delete the default profile"); return; }
    if (!confirm(`delete profile "${name}"?`)) return;
    await api("DELETE", `/profiles/${encodeURIComponent(name)}`);
    await loadProfiles();
  });
  $("btn-quit").addEventListener("click", async () => {
    if (!confirm("Stop wheelcraft? The server will exit and this page will stop working.")) return;
    try { await api("POST", "/shutdown"); } catch (e) { /* connection will drop */ }
    setTimeout(() => {
      document.body.innerHTML =
        '<div style="text-align:center;margin-top:25vh;font:14px system-ui;color:#8a93a0;">' +
        '<h1 style="color:#e6e8eb;font-weight:600;">wheelcraft stopped</h1>' +
        '<p>You can close this tab. To restart, launch wheelcraft from the Start menu or your desktop shortcut.</p>' +
        '</div>';
    }, 400);
  });
  $("btn-remap-reset").addEventListener("click", () => {
    for (const b of state.allButtons) state.profile.button_remap[b] = b;
    syncRemap();
    pushActive();
  });

  await loadProfiles();
  connectWS();

  setInterval(() => {
    if (state.allButtons.length && !$("remap-grid").children.length) buildRemapGrid();
  }, 250);
}

function flash(el, text) {
  const orig = el.textContent;
  el.textContent = text;
  setTimeout(() => { el.textContent = orig; }, 700);
}

init();
