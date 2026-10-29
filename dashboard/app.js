const statusEl = document.querySelector("#status");
const outcomeEl = document.querySelector("#outcome");
const emailEl = document.querySelector("#email");
const stepsEl = document.querySelector("#steps");
const honestyEl = document.querySelector("#honesty");
const chartEl = document.querySelector("#chart");
const falseEl = document.querySelector("#false-blocks");
const caseBody = document.querySelector("#cases tbody");
const attackSummary = document.querySelector("#attack-summary");
const attacksEl = document.querySelector("#attacks");
const adaptNote = document.querySelector("#adapt-note");
const eventsEl = document.querySelector("#events");

function tag(className, text) {
  const span = document.createElement("span");
  span.className = `tag ${className}`;
  span.textContent = text;
  return span;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

function renderStatus(status) {
  clear(statusEl);
  const lines = [
    `provider: ${status.provider}`,
    `screen: ${status.screen_backend}`,
    `judge: ${status.judge_backend}`,
    `configured spark id: ${status.spark_model}`,
    `configured wonder id: ${status.wonder_model}`,
    `meta key set: ${status.meta_api_key_set}`,
    `prompt guard weights: ${status.prompt_guard_weights_loaded}`,
  ];
  statusEl.textContent = lines.join("\n");
}

function renderRun(run) {
  emailEl.textContent = `${run.email.subject}\nfrom ${run.email.sender}\n\n${run.email.body}`;
  outcomeEl.textContent = run.leaked
    ? "Outbound side effect: the sandbox sent or forwarded data."
    : "No outbound side effect. Sends, forwards, and secret reads did not run.";
  clear(stepsEl);
  for (const step of run.steps) {
    const item = document.createElement("li");
    const decision = step.decision;
    if (!decision) {
      item.append(tag(step.executed ? "allow" : "block", step.executed ? "ran" : "skipped"));
      item.append(document.createTextNode(`${step.tool} — unprotected`));
    } else {
      item.append(tag(decision.action, decision.action));
      item.append(tag(decision.screen.label.toLowerCase(), `pass 1 ${decision.screen.label}`));
      const text = document.createElement("div");
      const pass = decision.pass_fired === 1 ? "pass 1" : decision.pass_fired === 2 ? "pass 2" : "policy";
      text.textContent = `${step.tool} · ${pass} · rule ${decision.rule_id}. ${decision.explanation}`;
      item.append(text);
    }
    stepsEl.append(item);
  }
}

function percent(rate) {
  if (rate === null || rate === undefined) return "—";
  return `${Math.round(rate * 1000) / 10}%`;
}

function bar(label, rate, className) {
  const row = document.createElement("div");
  row.className = "bar-line";
  const name = document.createElement("span");
  name.textContent = label;
  const track = document.createElement("div");
  track.className = "track";
  const fill = document.createElement("div");
  fill.className = `fill ${className || ""}`;
  const width = Math.max(0, Math.min(1, Number(rate) || 0)) * 100;
  fill.style.width = `${width}%`;
  track.append(fill);
  const value = document.createElement("span");
  value.textContent = percent(rate);
  row.append(name, track, value);
  return row;
}

function renderMetrics(report) {
  clear(chartEl);
  clear(falseEl);
  clear(caseBody);
  if (!report.available) {
    honestyEl.textContent = report.honesty || "No harness output yet.";
    return;
  }
  honestyEl.textContent = report.honesty;
  const attacks = report.heldout.attacks;
  for (const language of ["en", "tr"]) {
    const block = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = language === "en"
      ? `English held-out attacks (n=${attacks[language].n})`
      : `Turkish held-out attacks (n=${attacks[language].n})`;
    const bars = document.createElement("div");
    bars.className = "bars";
    bars.append(bar("Screen only", attacks[language].screen_only_stop_rate, "alt"));
    bars.append(bar("Kalkan", attacks[language].kalkan_stop_rate, ""));
    block.append(title, bars);
    chartEl.append(block);
  }
  const benign = report.heldout.benign;
  falseEl.textContent =
    `Benign false blocks — screen only EN ${benign.en.screen_only_false_blocks}/${benign.en.n}, ` +
    `TR ${benign.tr.screen_only_false_blocks}/${benign.tr.n}. ` +
    `Kalkan EN ${benign.en.kalkan_false_blocks}/${benign.en.n}, ` +
    `TR ${benign.tr.kalkan_false_blocks}/${benign.tr.n}.`;
  for (const row of report.cases) {
    const tr = document.createElement("tr");
    if (row.kind === "attack" && row.kalkan !== row.expect) tr.className = "miss";
    for (const value of [row.id, row.kind, row.tool, row.screen_label, row.screen_only, row.kalkan, row.expect]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    caseBody.append(tr);
  }
}

function renderAttacks(report) {
  adaptNote.textContent = report.adaptation_note || "";
  clear(attackSummary);
  clear(attacksEl);
  for (const language of ["en", "tr"]) {
    const stats = report.summary[language];
    const card = document.createElement("p");
    card.textContent =
      `${language.toUpperCase()} train replay: ${stats.stopped}/${stats.n} stopped, ` +
      `${stats.pass1_hits}/${stats.n} flagged by pass 1. Not a held-out rate.`;
    attackSummary.append(card);
  }
  for (const row of report.results) {
    const item = document.createElement("li");
    item.append(tag(row.action, row.action));
    item.append(tag(row.pass1.toLowerCase(), `pass 1 ${row.pass1}`));
    const text = document.createElement("div");
    text.textContent = `${row.language} · ${row.technique} · rule ${row.rule_id}. ${row.text}`;
    item.append(text);
    attacksEl.append(item);
  }
  for (const row of report.adapted_replay || []) {
    const item = document.createElement("li");
    item.append(tag("allow", "replay"));
    const text = document.createElement("div");
    text.textContent =
      `${row.language} session rule ${row.session_rule}: pass 1 ${row.pass1_before} → ${row.pass1_after}.`;
    item.append(text);
    attacksEl.append(item);
  }
}

async function refreshEvents() {
  const payload = await getJson("/api/events");
  clear(eventsEl);
  if (!payload.events.length) {
    const item = document.createElement("li");
    item.textContent = "No decisions yet.";
    eventsEl.append(item);
    return;
  }
  for (const event of payload.events) {
    const item = document.createElement("li");
    item.append(tag(event.action, event.action));
    const text = document.createElement("div");
    text.textContent = `${event.at} · ${event.tool} · rule ${event.rule_id} · ${event.explanation}`;
    item.append(text);
    eventsEl.append(item);
  }
}

async function runDemo(guard) {
  const scenario = document.querySelector("#scenario").value;
  const buttons = document.querySelectorAll("button");
  buttons.forEach((button) => {
    button.disabled = true;
  });
  try {
    const run = await getJson("/api/demo/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({scenario, guard}),
    });
    renderRun(run);
    await refreshEvents();
  } catch (error) {
    outcomeEl.textContent = `Run failed: ${error.message}`;
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

document.querySelector("#run-off").addEventListener("click", () => runDemo("off"));
document.querySelector("#run-screen").addEventListener("click", () => runDemo("screen"));
document.querySelector("#run-kalkan").addEventListener("click", () => runDemo("kalkan"));

document.querySelector("#recompute").addEventListener("click", async () => {
  honestyEl.textContent = "Running the held-out harness…";
  try {
    const report = await getJson("/api/eval/run", {method: "POST"});
    renderMetrics(report);
  } catch (error) {
    honestyEl.textContent = `Harness failed: ${error.message}`;
  }
});

document.querySelector("#attack").addEventListener("click", async () => {
  adaptNote.textContent = "Generating from train seeds…";
  try {
    const report = await getJson("/api/attacker/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({languages: ["en", "tr"]}),
    });
    renderAttacks(report);
  } catch (error) {
    adaptNote.textContent = `Attacker failed: ${error.message}`;
  }
});

async function boot() {
  try {
    renderStatus(await getJson("/api/status"));
    renderMetrics(await getJson("/api/metrics"));
    await refreshEvents();
  } catch (error) {
    statusEl.textContent = `Status failed: ${error.message}`;
  }
}

boot();
