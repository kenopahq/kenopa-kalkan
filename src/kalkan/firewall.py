"""Two-pass decision: screen the text, then judge the tool call."""

from __future__ import annotations

import json

from kalkan.judge.spark import JudgeParseError, JudgeRequest, SparkJudge
from kalkan.models import Decision, JudgeVerdict, ScreenResult, ToolCall
from kalkan.policy import Policy
from kalkan.screen.base import Screen


def screened_text(untrusted: str, tool: ToolCall) -> str:
    arguments = json.dumps(tool.arguments, ensure_ascii=False, sort_keys=True)
    return f"{untrusted}\n{arguments}"


class Firewall:
    def __init__(self, screen: Screen, judge: SparkJudge, policy: Policy):
        self.screen = screen
        self.judge = judge
        self.policy = policy

    def decide(self, user_intent: str, untrusted: str, tool: ToolCall) -> Decision:
        screen_result = self.screen.scan(screened_text(untrusted, tool))
        meta = self.policy.tool(tool.name)
        request = JudgeRequest(
            user_intent=user_intent,
            untrusted=untrusted,
            tool=tool,
            sensitivity=meta.sensitivity,
            screen=screen_result,
        )
        try:
            verdict = self.judge.judge(request)
        except (JudgeParseError, ValueError, RuntimeError) as exc:
            return self._fail_closed(tool, screen_result, meta.sensitivity, str(exc))
        return self._from_verdict(tool, screen_result, verdict)

    def _from_verdict(self, tool: ToolCall, screen_result: ScreenResult, verdict: JudgeVerdict) -> Decision:
        action = verdict.action
        rule_id = verdict.rule_id
        explanation = verdict.explanation
        overridden = False
        pass_fired: int | str = 2
        if tool.name in self.policy.hard_deny and action != "block":
            action = "block"
            rule_id = "no-exfil"
            explanation = (
                "Policy hard-deny overrode the judge. read_secret cannot run. " + verdict.explanation
            )
            overridden = True
            pass_fired = "policy"
        return Decision(
            action=action,
            rule_id=rule_id,
            explanation=explanation,
            intent_match=verdict.intent_match,
            pass_fired=pass_fired,  # type: ignore[arg-type]
            screen=screen_result,
            judge=verdict,
            judge_backend=self.judge.backend,
            overridden_by_policy=overridden,
            tool=tool,
        )

    def _fail_closed(self, tool: ToolCall, screen_result: ScreenResult, sensitivity: str, reason: str) -> Decision:
        if sensitivity == "low":
            action = "allow"
        elif sensitivity == "medium":
            action = "confirm"
        else:
            action = "block"
        explanation = (
            f"The intent judge was unavailable ({reason}). "
            f"Kalkan failed closed for sensitivity {sensitivity}. Rule judge-unavailable."
        )
        verdict = JudgeVerdict(
            action=action,
            rule_id="judge-unavailable",
            explanation=explanation,
            intent_match=False,
        )
        return Decision(
            action=action,
            rule_id="judge-unavailable",
            explanation=explanation,
            intent_match=False,
            pass_fired=2,
            screen=screen_result,
            judge=verdict,
            judge_backend=self.judge.backend,
            overridden_by_policy=False,
            tool=tool,
        )


def screen_only_action(screen_result: ScreenResult, sensitivity: str) -> str:
    """Baseline that never sees the user's intent. Used by the eval harness."""
    if screen_result.label == "MALICIOUS" and sensitivity in {"medium", "high", "critical"}:
        return "block"
    return "allow"
