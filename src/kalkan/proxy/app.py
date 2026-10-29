"""HTTP proxy, sandbox agent, and dashboard API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from kalkan.agent.naive import run_agent
from kalkan.agent.scenarios import SCENARIOS
from kalkan.attacker.loop import run_attacker, train_seeds
from kalkan.eval.harness import dump_report, evaluate, load_cases
from kalkan.models import ToolCall
from kalkan.runtime import Runtime, build_runtime


class DemoRequest(BaseModel):
    scenario: str = "tr-invoice"
    guard: str = "kalkan"


class AttackRequest(BaseModel):
    languages: list[str] = Field(default_factory=lambda: ["en", "tr"])


class InterceptRequest(BaseModel):
    user_intent: str
    untrusted: str = ""
    proposed_tool_calls: list[ToolCall]


class ChatRequest(BaseModel):
    model: str = "kalkan-sandbox"
    messages: list[dict] = Field(default_factory=list)
    guard: str | None = None


def create_app(runtime: Runtime | None = None) -> FastAPI:
    runtime = runtime or build_runtime()
    app = FastAPI(title="Kalkan", version="0.1.0")
    app.state.runtime = runtime
    dashboard = runtime.settings.root / "dashboard"
    if dashboard.is_dir():
        app.mount("/static", StaticFiles(directory=dashboard), name="static")

    @app.get("/")
    def index():
        page = dashboard / "index.html"
        if not page.is_file():
            raise HTTPException(status_code=404, detail="Dashboard is not installed.")
        return FileResponse(page)

    @app.get("/favicon.ico")
    def favicon():
        icon = dashboard / "favicon.svg"
        if not icon.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(icon, media_type="image/svg+xml")

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/status")
    def status():
        return runtime.status()

    @app.get("/api/policy")
    def policy():
        return runtime.policy.public_dict()

    @app.get("/api/events")
    def events():
        return {"events": runtime.events.recent()}

    @app.get("/api/metrics")
    def metrics():
        path = _metrics_file(runtime)
        if path is None:
            return {
                "available": False,
                "honesty": "No harness output yet. Run `kalkan eval` or POST /api/eval/run.",
            }
        report = json.loads(path.read_text(encoding="utf-8"))
        report["available"] = True
        report["source"] = _metrics_label(runtime, path)
        return report

    @app.post("/api/eval/run")
    def eval_run():
        cases = load_cases(runtime.settings.root)
        report = evaluate(cases, runtime.firewall, runtime.policy)
        destination = runtime.settings.data_dir / "latest.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_report(report), encoding="utf-8")
        report["available"] = True
        report["source"] = "data/latest.json"
        return report

    @app.post("/api/demo/run")
    def demo(body: DemoRequest):
        if body.guard not in {"off", "screen", "kalkan"}:
            raise HTTPException(status_code=400, detail="guard must be off, screen, or kalkan.")
        scenario = SCENARIOS.get(body.scenario)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Unknown scenario.")
        email = next((item for item in runtime.sandbox.inbox if item.id == scenario.email_id), None)
        if email is None:
            raise HTTPException(status_code=500, detail="Scenario email is missing from the sandbox.")
        run = run_agent(
            scenario=scenario,
            email=email,
            sandbox=runtime.sandbox,
            guard=body.guard,
            firewall=runtime.firewall,
            policy=runtime.policy,
        )
        _record_run(runtime, run)
        payload = run.model_dump(mode="json")
        payload["mode"] = runtime.status()
        payload["email"] = {
            "id": email.id,
            "sender": email.sender,
            "subject": email.subject,
            "body": email.body,
            "language": email.language,
        }
        return payload

    @app.post("/api/attacker/run")
    def attacker(body: AttackRequest):
        languages = [language for language in body.languages if language in {"en", "tr"}]
        if not languages:
            raise HTTPException(status_code=400, detail="languages must include en, tr, or both.")
        cases = load_cases(runtime.settings.root)
        seeds = train_seeds(cases)
        report = run_attacker(
            runtime.provider,
            runtime.firewall,
            seeds,
            languages,
            runtime.settings.wonder_model,
        )
        report["heldout_used"] = False
        report["seed_split"] = "train"
        return report

    @app.post("/v1/intercept")
    def intercept(body: InterceptRequest):
        decisions = []
        allowed = []
        held = []
        for call in body.proposed_tool_calls:
            decision = runtime.firewall.decide(body.user_intent, body.untrusted, call)
            item = decision.model_dump(mode="json")
            decisions.append(item)
            if decision.action == "allow":
                allowed.append(call.model_dump(mode="json"))
            elif decision.action == "confirm":
                held.append(call.model_dump(mode="json"))
            _record_decision(runtime, "intercept", decision)
        return {"decisions": decisions, "allowed_tool_calls": allowed, "held_for_confirmation": held}

    @app.post("/v1/chat/completions")
    def chat(body: ChatRequest):
        scenario_id = "tr-invoice"
        blob = json.dumps(body.messages, ensure_ascii=False).lower()
        if "en-invoice" in blob or "english" in blob:
            scenario_id = "en-invoice"
        guard = body.guard or ("off" if "guard off" in blob else "kalkan")
        if guard not in {"off", "screen", "kalkan"}:
            guard = "kalkan"
        scenario = SCENARIOS[scenario_id]
        email = next(item for item in runtime.sandbox.inbox if item.id == scenario.email_id)
        run = run_agent(
            scenario=scenario,
            email=email,
            sandbox=runtime.sandbox,
            guard=guard,
            firewall=runtime.firewall,
            policy=runtime.policy,
        )
        _record_run(runtime, run)
        content = _summary(run)
        return {
            "id": "chatcmpl-kalkan",
            "object": "chat.completion",
            "model": "kalkan-sandbox",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "kalkan": run.model_dump(mode="json"),
        }

    return app


def _metrics_label(runtime: Runtime, path: Path) -> str:
    if path.parent == runtime.settings.data_dir:
        return "data/latest.json"
    return "evals/results/latest.json"


def _metrics_file(runtime: Runtime) -> Path | None:
    fresh = runtime.settings.data_dir / "latest.json"
    if fresh.is_file():
        return fresh
    committed = runtime.settings.root / "evals" / "results" / "latest.json"
    if committed.is_file():
        return committed
    return None


def _record_run(runtime: Runtime, run) -> None:
    for step in run.steps:
        if step.decision is not None:
            _record_decision(runtime, run.scenario, step.decision, guard=run.guard)


def _record_decision(runtime: Runtime, source: str, decision, guard: str | None = None) -> None:
    runtime.events.add(
        {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source,
            "guard": guard,
            "tool": decision.tool.name,
            "action": decision.action,
            "rule_id": decision.rule_id,
            "pass_fired": decision.pass_fired,
            "screen_label": decision.screen.label,
            "screen_rules": decision.screen.matched_rule_ids,
            "screen_backend": decision.screen.backend,
            "judge_backend": decision.judge_backend,
            "explanation": decision.explanation,
        }
    )


def _summary(run) -> str:
    blocked = [
        f"{step.tool} blocked ({step.decision.rule_id})"
        for step in run.steps
        if step.decision is not None and step.decision.action == "block"
    ]
    if run.leaked:
        return "The sandbox agent forwarded or sent data. Kalkan was off or did not hold the call."
    if blocked:
        return "Kalkan held the sandbox agent. " + "; ".join(blocked) + "."
    return "The sandbox agent finished without an outbound side effect."
