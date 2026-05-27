const API = "http://localhost:8000";
let newRefs = new Set();

// ── Helpers ──────────────────────────────────────────────

function scoreClass(score, rank) {
  if (rank <= 3) return "podium";
  if (score >= 30) return "high";
  if (score >= 20) return "mid";
  return "low";
}

function barClass(val) {
  if (val >= 4) return "";
  if (val === 3) return "mid";
  return "low";
}

function setStatus(msg, type) {
  const el = document.getElementById("status");
  const text = document.getElementById("statusText");
  const spinner = document.getElementById("spinner");
  el.className = `status visible ${type}`;
  text.textContent = msg;
  spinner.style.display = type === "loading" ? "block" : "none";
}

function hideStatus() {
  document.getElementById("status").className = "status";
}

// ── Render ───────────────────────────────────────────────

function renderStats(theses) {
  const scores = theses.map((t) => t.weighted_total);
  const top = Math.max(...scores);
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;

  document.getElementById("statTotal").textContent = theses.length;
  document.getElementById("statTop").textContent = top.toFixed(1);
  document.getElementById("statAvg").textContent = avg.toFixed(1);
  document.getElementById("statNew").textContent = newRefs.size || "—";
  document.getElementById("stats").style.display = "grid";
}

function renderPodium(theses) {
  const podium = document.getElementById("podium");
  const stage = document.getElementById("podiumStage");

  const top3 = theses.filter((t) => t.rank <= 3);
  if (top3.length < 3) {
    podium.style.display = "none";
    return;
  }

  podium.style.display = "block";
  const maxScore = Math.max(...theses.map((t) => t.weighted_total));
  const order = [
    top3.find((t) => t.rank === 2),
    top3.find((t) => t.rank === 1),
    top3.find((t) => t.rank === 3),
  ];
  const labels = ["", "1st", "2nd", "3rd"];

  stage.innerHTML = order
    .map((t) => {
      const sc = scoreClass(t.weighted_total, t.rank);
      const label = labels[t.rank];
      return `
    <div class="podium-slot rank-${t.rank}" onclick="selectFromPodium('${t.ref}')">
      <div class="podium-card">
        <div class="podium-rank-badge rank-${t.rank}">${label}</div>
        <div class="podium-card-title">${t.title}</div>
        <div class="score-pill ${sc}" style="display:inline-block;margin-top:8px">${t.weighted_total.toFixed(1)}</div>
        <div class="podium-card-oneliner">${t.one_liner}</div>
      </div>
      <div class="podium-platform">
        <span class="podium-platform-label">${label}</span>
      </div>
    </div>`;
    })
    .join("");
}

function selectFromPodium(ref) {
  const row = document.getElementById(`row-${ref}`);
  if (!row.classList.contains("expanded")) row.classList.add("expanded");
  row.scrollIntoView({ behavior: "smooth", block: "center" });
}

function renderTheses(theses) {
  const list = document.getElementById("thesisList");

  document.getElementById("countBadge").textContent = `${theses.length} ideas`;

  if (!theses.length) {
    list.innerHTML = '<div class="empty">No theses loaded.</div>';
    return;
  }

  list.innerHTML = theses
    .map((t) => {
      const isNew = newRefs.has(t.ref);
      const sc = scoreClass(t.weighted_total, t.rank);
      const criteria = [
        { label: "Buildability", key: "buildability", weight: "×2" },
        { label: "Speed to Revenue", key: "speed_to_revenue", weight: "×2" },
        { label: "Distribution", key: "distribution", weight: "×1.5" },
        { label: "Defensibility", key: "defensibility", weight: "×1" },
        { label: "Market Size", key: "market_size", weight: "×1.5" },
      ];

      const barsHTML = criteria
        .map((c) => {
          const val = t[c.key];
          const bc = barClass(val);
          return `
        <div class="criterion">
          <div class="criterion-label">${c.label} <span style="color:var(--border-active)">${c.weight}</span></div>
          <div class="bar-track"><div class="bar-fill ${bc}" style="width:${(val / 5) * 100}%"></div></div>
          <div class="criterion-score">${val}/5</div>
        </div>`;
        })
        .join("");

      return `
    <div class="thesis-row${isNew ? " new-entry" : ""}" id="row-${t.ref}">
      <div class="thesis-summary" onclick="toggle('${t.ref}')">
        <div class="rank-num ${t.rank <= 3 ? "top3" : ""}">#${t.rank}</div>
        <div class="thesis-info">
          <div class="thesis-title">
            ${t.title}
            ${isNew ? '<span class="new-badge">NEW</span>' : ""}
          </div>
          <div class="thesis-oneliner">${t.one_liner}</div>
        </div>
        <div class="score-pill ${sc}">${t.weighted_total.toFixed(1)}</div>
        <div class="chevron">▾</div>
      </div>
      <div class="thesis-detail">
        <div class="criteria-bars">${barsHTML}</div>
        <div class="detail-grid">
          <div class="detail-section">
            <h4>Example Customer</h4>
            <p>${t.example_customer}</p>
          </div>
          <div class="detail-section">
            <h4>The Wedge</h4>
            <p>${t.wedge}</p>
          </div>
        </div>
        <div class="rationale-box">
          <strong>Rationale</strong>
          ${t.rationale}
        </div>
      </div>
    </div>`;
    })
    .join("");

  renderPodium(theses);
  renderStats(theses);
}

function toggle(ref) {
  const row = document.getElementById(`row-${ref}`);
  row.classList.toggle("expanded");
}

// ── Data fetching ─────────────────────────────────────────

async function loadTheses() {
  try {
    const res = await fetch(`${API}/theses`);
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();
    renderTheses(data);
    hideStatus();
  } catch (e) {
    setStatus(`Failed to load theses: ${e.message}`, "error");
  }
}

async function uploadFile(file) {
  setStatus(`Scoring and ranking ${file.name}...`, "loading");

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(`${API}/rank`, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();

    // Track new refs for highlighting
    const existingRefs = new Set(
      Array.from(document.querySelectorAll(".thesis-row")).map((r) =>
        r.id.replace("row-", ""),
      ),
    );

    // Parse uploaded file to find new refs
    const text = await file.text().catch(() => "");
    if (file.name.endsWith(".json")) {
      try {
        const parsed = JSON.parse(text);
        parsed.forEach((t) => {
          if (!existingRefs.has(t.ref)) newRefs.add(t.ref);
        });
      } catch {}
    } else {
      text
        .split("\n")
        .slice(1)
        .forEach((line) => {
          const ref = line.split(",")[0].trim();
          if (ref && !existingRefs.has(ref)) newRefs.add(ref);
        });
    }

    renderTheses(data);
    setStatus(
      `Ranked ${data.length} ideas — ${newRefs.size} new added`,
      "success",
    );
    setTimeout(hideStatus, 4000);
  } catch (e) {
    setStatus(`Upload failed: ${e.message}`, "error");
  }
}

// ── Events ────────────────────────────────────────────────

document.getElementById("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) uploadFile(file);
  e.target.value = "";
});

const zone = document.getElementById("uploadZone");
zone.addEventListener("dragover", (e) => {
  e.preventDefault();
  zone.classList.add("drag-over");
});
zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
zone.addEventListener("drop", (e) => {
  e.preventDefault();
  zone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

// ── Init ──────────────────────────────────────────────────
loadTheses();
