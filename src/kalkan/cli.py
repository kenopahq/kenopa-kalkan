"""Command line: serve, eval, demo."""

from __future__ import annotations

import argparse
import json
import sys

from kalkan.agent.naive import run_agent
from kalkan.agent.scenarios import SCENARIOS
from kalkan.eval.harness import dump_report, evaluate, load_cases, reports_equal, write_report
from kalkan.runtime import build_runtime


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="kalkan")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the proxy, sandbox agent, and dashboard.")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    evaluate_cmd = sub.add_parser("eval", help="Score the held-out split and write the chart file.")
    evaluate_cmd.add_argument("--out", default="evals/results/latest.json")
    evaluate_cmd.add_argument("--check", default=None, help="Exit 1 if this file differs from a fresh run.")

    demo = sub.add_parser("demo", help="Run one sandbox scenario.")
    demo.add_argument("--scenario", default="tr-invoice")
    demo.add_argument("--guard", default="kalkan", choices=["off", "screen", "kalkan"])

    args = parser.parse_args(argv)
    if args.command == "serve":
        _serve(args.host, args.port)
    elif args.command == "eval":
        _eval(args.out, args.check)
    elif args.command == "demo":
        _demo(args.scenario, args.guard)


def _serve(host: str | None, port: int | None) -> None:
    import uvicorn

    from kalkan.proxy.app import create_app

    runtime = build_runtime()
    app = create_app(runtime)
    uvicorn.run(
        app,
        host=host or runtime.settings.host,
        port=port or runtime.settings.port,
        log_level="info",
    )


def _eval(out: str, check: str | None) -> None:
    runtime = build_runtime()
    cases = load_cases(runtime.settings.root)
    report = evaluate(cases, runtime.firewall, runtime.policy)
    if check:
        from pathlib import Path

        path = Path(check)
        if not reports_equal(path, report):
            print(f"eval file {path} does not match a fresh harness run", file=sys.stderr)
            raise SystemExit(1)
        print(f"eval file matches the harness ({path})")
        return
    from pathlib import Path

    destination = Path(out)
    if not destination.is_absolute():
        destination = runtime.settings.root / destination
    write_report(destination, report)
    attacks = report["heldout"]["attacks"]
    print(dump_report({"mode": report["mode"], "honesty": report["honesty"], "attacks": attacks}))


def _demo(scenario_id: str, guard: str) -> None:
    runtime = build_runtime()
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
    print(json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
