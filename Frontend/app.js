const API = ""; // same-origin, backend serves the frontend too

const $ = (sel) => document.querySelector(sel);

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";
  } catch {
    return iso;
  }
}

// ---------- status pill ----------

async function loadHealth() {
  const dot = $("#status-dot");
  const text = $("#status-text");
  try {
    const res = await fetch(`${API}/api/health`);
    if (!res.ok) throw new Error("bad response");
    const data = await res.json();
    dot.classList.add("ok");
    text.textContent = `online · ${data.total_rows} rows`;
  } catch (e) {
    dot.classList.add("err");
    text.textContent = "backend unreachable";
  }
}

// ---------- catalog card ----------

async function loadCatalog() {
  try {
    const res = await fetch(`${API}/api/datasets/github_repos/catalog`);
    if (!res.ok) throw new Error("no catalog yet");
    const c = await res.json();

    $("#stat-rows").textContent = c.row_count ?? "—";
    $("#stat-quarantined").textContent = c.quarantined_count ?? "0";
    $("#stat-updated").textContent = fmtDate(c.last_updated_utc);

    const tbody = $("#fields-tbody");
    tbody.innerHTML = "";
    (c.fields || []).forEach((f) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${f.name}</td><td>${f.type}</td><td>${(f.null_rate * 100).toFixed(0)}%</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    $("#fields-tbody").innerHTML =
      `<tr><td colspan="3" class="muted">No catalog yet — run the pipeline (python backend/run_pipeline.py) first.</td></tr>`;
  }
}

// ---------- browse table ----------

async function loadLanguages() {
  try {
    const res = await fetch(`${API}/api/datasets/github_repos/languages`);
    const langs = await res.json();
    const sel = $("#filter-language");
    langs.forEach((l) => {
      const opt = document.createElement("option");
      opt.value = l;
      opt.textContent = l;
      sel.appendChild(opt);
    });
  } catch (e) {
    /* non-fatal */
  }
}

function renderBrowseRows(rows) {
  const tbody = $("#browse-tbody");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="muted">No rows match those filters.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map(
      (r) => `
      <tr>
        <td><a href="${r.url}" target="_blank" rel="noopener">${r.full_name}</a></td>
        <td>${r.language ? `<span class="tag">${r.language}</span>` : "—"}</td>
        <td class="num">${r.stars.toLocaleString()}</td>
        <td class="num">${r.forks.toLocaleString()}</td>
        <td>${r.license ?? "—"}</td>
        <td>${fmtDate(r.pushed_at)}</td>
      </tr>`
    )
    .join("");
}

async function loadBrowse() {
  const language = $("#filter-language").value;
  const minStars = $("#filter-stars").value || 0;
  const params = new URLSearchParams({ min_stars: minStars, limit: 25 });
  if (language) params.set("language", language);

  $("#browse-tbody").innerHTML = `<tr><td colspan="6" class="muted">loading…</td></tr>`;
  try {
    const res = await fetch(`${API}/api/datasets/github_repos/query?${params}`);
    const rows = await res.json();
    renderBrowseRows(rows);
  } catch (e) {
    $("#browse-tbody").innerHTML = `<tr><td colspan="6" class="muted">Could not load rows.</td></tr>`;
  }
}

// ---------- ask console ----------

function renderResultsTable(rows) {
  const thead = $("#results-thead");
  const tbody = $("#results-tbody");
  if (!rows.length) {
    thead.innerHTML = "";
    tbody.innerHTML = `<tr><td class="muted">No rows returned.</td></tr>`;
    return;
  }
  const cols = Object.keys(rows[0]);
  thead.innerHTML = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  tbody.innerHTML = rows
    .map(
      (r) =>
        `<tr>${cols
          .map((c) => {
            const v = r[c];
            const isNum = typeof v === "number";
            return `<td class="${isNum ? "num" : ""}">${v === null || v === undefined ? "—" : v}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");
}

async function askQuestion(question) {
  const output = $("#ask-output");
  const errBox = $("#ask-error");
  const submitBtn = $("#ask-submit");

  output.hidden = false;
  errBox.hidden = true;
  submitBtn.disabled = true;
  $("#ask-sql").textContent = "…thinking…";
  $("#ask-explanation").textContent = "";
  $("#results-thead").innerHTML = "";
  $("#results-tbody").innerHTML = "";

  try {
    const res = await fetch(`${API}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "request failed");

    $("#ask-sql").textContent = data.sql || "(no query generated)";
    $("#ask-explanation").textContent = data.explanation || "";

    if (data.error) {
      errBox.hidden = false;
      errBox.textContent = data.error;
    }
    renderResultsTable(data.results || []);
  } catch (e) {
    $("#ask-sql").textContent = "(request failed)";
    errBox.hidden = false;
    errBox.textContent = e.message || "Something went wrong asking DataHub.";
  } finally {
    submitBtn.disabled = false;
  }
}

// ---------- wire up ----------

$("#ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("#ask-input").value.trim();
  if (q) askQuestion(q);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    $("#ask-input").value = chip.dataset.q;
    askQuestion(chip.dataset.q);
  });
});

$("#filter-apply").addEventListener("click", loadBrowse);

loadHealth();
loadCatalog();
loadLanguages().then(loadBrowse);
