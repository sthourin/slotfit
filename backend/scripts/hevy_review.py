"""Point-and-click review tool for hevy/exercise_map.yaml.

Serves a local page where each Hevy exercise is one card: pick a candidate,
search the full catalogue, create a new exercise, or skip. Saving writes the
YAML back in place, so the normal apply step is unchanged:

    python -m scripts.hevy_review          # opens a browser, review, Save
    python -m scripts.hevy_staples apply   # dry run
    python -m scripts.hevy_staples apply --commit

Run from backend/. Local only - binds 127.0.0.1 and is a development tool, not
part of the API.
"""

import argparse
import asyncio
import json
import webbrowser
from collections import defaultdict
from statistics import median
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Equipment, Exercise, MovementPattern
from app.services.hevy_import import (
    MACHINE_EQUIPMENT,
    apply_review_selections,
    dump_map,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "hevy" / "exercise_map.yaml"


async def _load_reference() -> dict:
    """Read everything the page needs to offer valid choices."""
    async with AsyncSessionLocal() as db:
        catalogue = sorted(
            (await db.execute(select(Exercise.name))).scalars().all()
        )
        patterns = (
            await db.execute(
                select(MovementPattern.slug).order_by(MovementPattern.display_order)
            )
        ).scalars().all()
        equipment = (await db.execute(select(Equipment.name))).scalars().all()
    all_equipment = sorted(set(equipment) | {name for name, _ in MACHINE_EQUIPMENT})
    return {
        "catalogue": catalogue,
        "patterns": list(patterns),
        "equipment": all_equipment,
    }


def _median_durations() -> dict[str, int]:
    """Median seconds per set for each Hevy exercise that logs duration.

    Pre-fills the variant form so a time-based exercise carries the interval
    length actually used, rather than a guess.
    """
    workouts_path = REPO_ROOT / "hevy" / "data" / "workouts.json"
    if not workouts_path.is_file():
        return {}
    seen: dict[str, list[int]] = defaultdict(list)
    for workout in json.loads(workouts_path.read_text(encoding="utf-8")):
        for entry in workout.get("exercises") or []:
            for one_set in entry.get("sets") or []:
                if one_set.get("duration_seconds"):
                    seen[entry.get("title")].append(one_set["duration_seconds"])
    return {title: int(median(values)) for title, values in seen.items() if values}


def _read_map() -> dict:
    if not MAP_PATH.is_file():
        raise SystemExit(
            f"error: {MAP_PATH} not found. Run: python -m scripts.hevy_staples generate"
        )
    return yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hevy exercise deconfliction</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #fff; --fg: #16191d; --muted: #6b7280;
    --line: #dfe3e8; --accent: #1f6feb; --accent-soft: #e8f0fe;
    --ok: #1a7f47; --ok-soft: #e6f4ec; --warn: #9a6700;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1216; --card: #171b21; --fg: #e6e9ee; --muted: #9aa4b2;
      --line: #2a313a; --accent: #4c8dff; --accent-soft: #16233a;
      --ok: #4ac07f; --ok-soft: #12271c; --warn: #d9a441;
    }
  }
  :root[data-theme="light"] {
    --bg: #f6f7f9; --card: #fff; --fg: #16191d; --muted: #6b7280;
    --line: #dfe3e8; --accent: #1f6feb; --accent-soft: #e8f0fe;
    --ok: #1a7f47; --ok-soft: #e6f4ec; --warn: #9a6700;
  }
  :root[data-theme="dark"] {
    --bg: #0f1216; --card: #171b21; --fg: #e6e9ee; --muted: #9aa4b2;
    --line: #2a313a; --accent: #4c8dff; --accent-soft: #16233a;
    --ok: #4ac07f; --ok-soft: #12271c; --warn: #d9a441;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--fg);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding-bottom: 90px;
  }
  header {
    position: sticky; top: 0; z-index: 5; background: var(--bg);
    border-bottom: 1px solid var(--line); padding: 14px 20px;
  }
  h1 { font-size: 17px; margin: 0 0 2px; }
  .sub { color: var(--muted); font-size: 13px; }
  .filters { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
  .filters button {
    font: inherit; font-size: 13px; padding: 4px 11px; cursor: pointer;
    background: var(--card); color: var(--fg);
    border: 1px solid var(--line); border-radius: 999px;
  }
  .filters button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
  main { max-width: 860px; margin: 0 auto; padding: 18px 20px; }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px; margin-bottom: 12px;
  }
  .card.resolved { border-left: 3px solid var(--ok); }
  .card.hidden { display: none; }
  .card h2 { font-size: 15px; margin: 0; display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .meta { color: var(--muted); font-size: 12px; font-weight: 400; }
  .opts { margin-top: 10px; display: grid; gap: 2px; }
  label.opt {
    display: flex; gap: 10px; align-items: flex-start; cursor: pointer;
    padding: 6px 9px; border-radius: 7px; border: 1px solid transparent;
  }
  label.opt:hover { background: var(--accent-soft); }
  label.opt input { margin: 3px 0 0; accent-color: var(--accent); flex: none; }
  label.opt.checked { background: var(--accent-soft); border-color: var(--accent); }
  .kbd {
    font: 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted);
    border: 1px solid var(--line); border-radius: 4px; padding: 2px 5px; margin-left: auto; flex: none;
  }
  .extra { margin: 6px 0 2px 30px; display: none; }
  .extra.show { display: block; }
  input[type=text], select {
    font: inherit; padding: 6px 9px; border: 1px solid var(--line);
    border-radius: 7px; background: var(--bg); color: var(--fg); width: 100%;
  }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
  .row > * { flex: 1 1 170px; }
  .results { max-height: 190px; overflow-y: auto; margin-top: 6px; border: 1px solid var(--line); border-radius: 7px; }
  .results:empty { display: none; }
  .results div { padding: 5px 10px; cursor: pointer; font-size: 14px; }
  .results div:hover, .results div.sel { background: var(--accent-soft); }
  .chosen { margin-top: 6px; font-size: 13px; color: var(--ok); font-weight: 600; }
  footer {
    position: fixed; bottom: 0; left: 0; right: 0; background: var(--card);
    border-top: 1px solid var(--line); padding: 12px 20px;
    display: flex; align-items: center; gap: 16px; justify-content: center;
  }
  .bar { flex: 1; max-width: 380px; height: 7px; background: var(--line); border-radius: 999px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--ok); width: 0; transition: width .2s; }
  button.save {
    font: inherit; font-weight: 600; padding: 9px 20px; cursor: pointer;
    background: var(--accent); color: #fff; border: 0; border-radius: 8px;
  }
  button.save:disabled { opacity: .5; cursor: default; }
  #status { font-size: 13px; color: var(--muted); min-width: 90px; }
</style>
</head>
<body>
<header>
  <h1>Hevy exercise deconfliction</h1>
  <div class="sub" id="count"></div>
  <div class="filters">
    <button data-filter="all" aria-pressed="true">All</button>
    <button data-filter="todo" aria-pressed="false">Unresolved</button>
    <button data-filter="done" aria-pressed="false">Resolved</button>
  </div>
</header>
<main id="list"></main>
<footer>
  <span id="status"></span>
  <div class="bar"><i id="fill"></i></div>
  <button class="save" id="save">Save to exercise_map.yaml</button>
</footer>
<script>
const DATA = __DATA__;
const state = {};           // hevy title -> selection object
let filter = "all";

// Seed state from any decisions already in the file, so a partial review resumes.
for (const e of DATA.entries) {
  if (e.create && e.create.variant_of) state[e.hevy] = {kind: "variant", ...e.create};
  else if (e.create) state[e.hevy] = {kind: "create", ...e.create};
  else if (e.slotfit === "SKIP") state[e.hevy] = {kind: "skip"};
  else if (e.slotfit) state[e.hevy] = {kind: "exercise", name: e.slotfit};
}

const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function card(e, i) {
  const id = "e" + i;
  const opts = e.candidates.map((c, n) => `
    <label class="opt" data-kind="exercise" data-name="${esc(c)}">
      <input type="radio" name="${id}"><span>${esc(c)}</span><span class="kbd">${n + 1}</span>
    </label>`).join("");
  return `
  <section class="card" data-hevy="${esc(e.hevy)}" data-idx="${i}">
    <h2>${esc(e.hevy)}
      <span class="meta">${e.sessions} sessions &middot; last ${e.last_performed} &middot; hevy: ${esc(e.hevy_equipment || "n/a")}</span>
    </h2>
    <div class="opts">
      ${opts}
      <label class="opt" data-kind="search">
        <input type="radio" name="${id}"><span>Search the full catalogue&hellip;</span><span class="kbd">s</span>
      </label>
      <div class="extra" data-for="search">
        <input type="text" placeholder="Type at least 2 characters" class="q">
        <div class="results"></div>
        <div class="chosen"></div>
      </div>
      <label class="opt" data-kind="variant">
        <input type="radio" name="${id}"><span>Training-style variant of an existing exercise</span><span class="kbd">v</span>
      </label>
      <div class="extra" data-for="variant">
        <div class="row">
          <input type="text" class="vbase" placeholder="Base exercise (search)" value="${esc(e.candidates[0] || "")}">
          <input type="text" class="vtype" placeholder="Style, e.g. HIIT" value="HIIT">
          <input type="text" class="vtime" placeholder="Seconds per set" value="${e.median_seconds || ""}">
        </div>
        <div class="results vresults"></div>
        <div class="chosen vchosen">${e.candidates[0] ? "Base: " + esc(e.candidates[0]) : ""}</div>
      </div>
      <label class="opt" data-kind="create">
        <input type="radio" name="${id}"><span>Create a new exercise</span><span class="kbd">c</span>
      </label>
      <div class="extra" data-for="create">
        <div class="row">
          <input type="text" class="cname" placeholder="Exercise name" value="${esc(e.hevy)}">
          <select class="cpattern">
            <option value="">movement pattern&hellip;</option>
            ${DATA.patterns.map(p => `<option value="${p}">${p}</option>`).join("")}
          </select>
          <select class="cequip">
            <option value="">equipment (optional)&hellip;</option>
            ${DATA.equipment.map(q => `<option value="${esc(q)}">${esc(q)}</option>`).join("")}
          </select>
        </div>
      </div>
      <label class="opt" data-kind="skip">
        <input type="radio" name="${id}"><span>Skip &mdash; not a real exercise</span><span class="kbd">x</span>
      </label>
    </div>
  </section>`;
}

const list = document.getElementById("list");
list.innerHTML = DATA.entries.map(card).join("");

function restore(section) {
  const sel = state[section.dataset.hevy];
  if (!sel) return;
  let target = null;
  if (sel.kind === "exercise") {
    target = [...section.querySelectorAll('.opt[data-kind="exercise"]')]
      .find(l => l.dataset.name === sel.name);
    if (!target) {                       // chosen via search, not in the top 5
      target = section.querySelector('.opt[data-kind="search"]');
      section.querySelector('[data-for="search"] .chosen').textContent = "Selected: " + sel.name;
    }
  } else {
    target = section.querySelector(`.opt[data-kind="${sel.kind}"]`);
    if (sel.kind === "create") {
      section.querySelector(".cname").value = sel.name || "";
      section.querySelector(".cpattern").value = sel.pattern || "";
      section.querySelector(".cequip").value = sel.equipment || "";
    } else if (sel.kind === "variant") {
      section.querySelector(".vbase").value = sel.variant_of || "";
      section.querySelector(".vtype").value = sel.variant_type || "";
      section.querySelector(".vtime").value = sel.default_time_seconds || "";
      section.querySelector(".vchosen").textContent = "Base: " + (sel.variant_of || "");
    }
  }
  if (target) { target.querySelector("input").checked = true; paint(section); }
}

function paint(section) {
  section.querySelectorAll("label.opt").forEach(l =>
    l.classList.toggle("checked", l.querySelector("input").checked));
  section.querySelectorAll(".extra").forEach(x => {
    const owner = section.querySelector(`.opt[data-kind="${x.dataset.for}"] input`);
    x.classList.toggle("show", owner.checked);
  });
  section.classList.toggle("resolved", !!state[section.dataset.hevy]);
}

function choose(section, label) {
  const kind = label.dataset.kind;
  const hevy = section.dataset.hevy;
  label.querySelector("input").checked = true;
  if (kind === "exercise") state[hevy] = {kind: "exercise", name: label.dataset.name};
  else if (kind === "skip") state[hevy] = {kind: "skip"};
  else if (kind === "create") readCreate(section);
  else if (kind === "variant") readVariant(section);
  else {
    const prior = section.querySelector('[data-for="search"] .chosen').textContent;
    if (!prior) delete state[hevy];       // search picked but nothing chosen yet
  }
  paint(section); tally();
  if (kind === "search") section.querySelector(".q").focus();
}

function readVariant(section) {
  const hevy = section.dataset.hevy;
  const variant_of = section.querySelector(".vbase").value.trim();
  const variant_type = section.querySelector(".vtype").value.trim();
  const secs = section.querySelector(".vtime").value.trim();
  // Only a decision once the base exists in the catalogue and a style is named.
  if (variant_of && variant_type && DATA.catalogue.includes(variant_of)) {
    state[hevy] = {kind: "variant", variant_of, variant_type, default_time_seconds: secs};
    section.querySelector(".vchosen").textContent = "Base: " + variant_of;
  } else {
    delete state[hevy];
    section.querySelector(".vchosen").textContent =
      variant_of ? "Base not found in catalogue - pick from the list" : "";
  }
  paint(section); tally();
}

function readCreate(section) {
  const hevy = section.dataset.hevy;
  const name = section.querySelector(".cname").value.trim();
  const pattern = section.querySelector(".cpattern").value;
  const equipment = section.querySelector(".cequip").value;
  // A create is only a decision once it has both a name and a pattern.
  if (name && pattern) state[hevy] = {kind: "create", name, pattern, equipment};
  else delete state[hevy];
  paint(section); tally();
}

list.addEventListener("click", ev => {
  const label = ev.target.closest("label.opt");
  if (label) return choose(label.closest(".card"), label);
  const hit = ev.target.closest(".results div");
  if (hit) {
    const section = hit.closest(".card");
    if (hit.closest(".vresults")) {           // choosing a variant's base
      section.querySelector(".vbase").value = hit.textContent;
      section.querySelector(".vresults").innerHTML = "";
      readVariant(section);
      return;
    }
    state[section.dataset.hevy] = {kind: "exercise", name: hit.textContent};
    section.querySelector('[data-for="search"] .chosen').textContent = "Selected: " + hit.textContent;
    section.querySelector(".results").innerHTML = "";
    paint(section); tally();
  }
});

function searchInto(box, query) {
  const q = query.trim().toLowerCase();
  if (q.length < 2) { box.innerHTML = ""; return; }
  const terms = q.split(/\\s+/);
  const hits = DATA.catalogue
    .filter(n => { const l = n.toLowerCase(); return terms.every(t => l.includes(t)); })
    .slice(0, 40);
  box.innerHTML = hits.map(n => `<div>${esc(n)}</div>`).join("")
    || '<div style="color:var(--muted);cursor:default">no match</div>';
}

list.addEventListener("input", ev => {
  const section = ev.target.closest(".card");
  if (ev.target.classList.contains("q")) {
    searchInto(section.querySelector('[data-for="search"] .results'), ev.target.value);
  }
  if (ev.target.classList.contains("vbase")) {
    searchInto(section.querySelector(".vresults"), ev.target.value);
    readVariant(section);
  }
  if (ev.target.matches(".vtype, .vtime")) readVariant(section);
  if (ev.target.matches(".cname, .cpattern, .cequip")) readCreate(section);
});

// Number keys pick a candidate on whichever card the pointer is over.
let hovered = null;
list.addEventListener("mouseover", ev => { hovered = ev.target.closest(".card") || hovered; });
document.addEventListener("keydown", ev => {
  if (!hovered || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) return;
  const map = {s: "search", c: "create", v: "variant", x: "skip"};
  let label = null;
  if (/^[1-9]$/.test(ev.key)) {
    label = hovered.querySelectorAll('.opt[data-kind="exercise"]')[+ev.key - 1];
  } else if (map[ev.key.toLowerCase()]) {
    label = hovered.querySelector(`.opt[data-kind="${map[ev.key.toLowerCase()]}"]`);
  }
  if (label) { ev.preventDefault(); choose(hovered, label); }
});

document.querySelectorAll(".filters button").forEach(b => b.addEventListener("click", () => {
  filter = b.dataset.filter;
  document.querySelectorAll(".filters button").forEach(o =>
    o.setAttribute("aria-pressed", String(o === b)));
  tally();
}));

function tally() {
  const total = DATA.entries.length;
  const done = Object.keys(state).length;
  document.getElementById("count").textContent =
    `${total} exercises from the last ${DATA.meta.window_days} days, ${DATA.meta.min_sessions}+ sessions`;
  document.getElementById("status").textContent = `${done} / ${total} resolved`;
  document.getElementById("fill").style.width = (done / total * 100) + "%";
  document.querySelectorAll(".card").forEach(s => {
    const resolved = !!state[s.dataset.hevy];
    s.classList.toggle("hidden",
      (filter === "todo" && resolved) || (filter === "done" && !resolved));
  });
}

document.getElementById("save").addEventListener("click", async () => {
  const btn = document.getElementById("save");
  btn.disabled = true; btn.textContent = "Saving\\u2026";
  try {
    const r = await fetch("/save", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(state),
    });
    const out = await r.json();
    btn.textContent = r.ok ? "Saved \\u2713" : "Save failed";
    document.getElementById("status").textContent =
      r.ok ? `wrote ${out.resolved} of ${out.total} to exercise_map.yaml` : (out.error || "error");
  } catch (err) {
    btn.textContent = "Save failed";
    document.getElementById("status").textContent = String(err);
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = "Save to exercise_map.yaml"; tally(); }, 2500);
});

document.querySelectorAll(".card").forEach(restore);
tally();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    reference: dict = {}

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain")
            return
        document = _read_map()
        entries = document.get("exercises") or []
        durations = _median_durations()
        for entry in entries:
            entry["median_seconds"] = durations.get(entry.get("hevy"))
        payload = {
            "entries": entries,
            "meta": document.get("meta") or {},
            **self.reference,
        }
        page = PAGE.replace("__DATA__", json.dumps(payload))
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path != "/save":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            selections = json.loads(self.rfile.read(length) or b"{}")
            document = apply_review_selections(_read_map(), selections)
            MAP_PATH.write_text(dump_map(document), encoding="utf-8")
        except Exception as exc:  # surfaced in the page's status line
            self._send(
                500,
                json.dumps({"error": str(exc)}).encode("utf-8"),
                "application/json",
            )
            return
        body = json.dumps(
            {"resolved": len(selections), "total": len(document.get("exercises") or [])}
        ).encode("utf-8")
        print(f"Saved {len(selections)} decisions to {MAP_PATH}")
        self._send(200, body, "application/json")

    def log_message(self, *args) -> None:
        """Silence the per-request access log; the page is the interface."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    _read_map()  # fail fast if the mapping file is missing
    Handler.reference = asyncio.run(_load_reference())

    url = f"http://127.0.0.1:{args.port}/"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Review tool at {url}")
    print("Pick an option per card, click Save, then Ctrl-C here.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
