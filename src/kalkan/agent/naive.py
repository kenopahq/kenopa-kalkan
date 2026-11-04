"""A tool-using agent that treats instructions in mail as orders.

This is the vulnerable half of the demo. It is deterministic on purpose so the
story does not depend on a model call. It is not Muse Spark.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from kalkan.agent.sandbox import Email, Sandbox
from kalkan.firewall import Firewall, screen_only_action, screened_text
from kalkan.models import Decision, ToolCall
from kalkan.policy import Policy
from kalkan.text import find_emails

_FILE_CUE = re.compile(
    r"(files|documents|attachments|dosya|ekleri|klasör|klasor|\.env|secret)",
    re.IGNORECASE,
)
_MOVE_CUE = re.compile(
    r"(forward|exfiltrate|relay|ilet|yolla|aktar|gönder|gonder|gitsin|bırak|birak)",
    re.IGNORECASE,
)


class Scenario(BaseModel):
    id: str
    language: str
    email_id: str
    user_intent: str
    safe_draft: str
    doc_query: str = "payment"


class AgentStep(BaseModel):
    tool: str
    arguments: dict
    executed: bool
    observation: str
    decision: Decision | None = None


class AgentRun(BaseModel):
    scenario: str
    guard: str
    leaked: bool
    user_intent: str
    steps: list[AgentStep] = Field(default_factory=list)


def proposes_exfil(text: str) -> str | None:
    """Last email address in a body that also asks for files to be moved."""
    if not _FILE_CUE.search(text) or not _MOVE_CUE.search(text):
        return None
    emails = find_emails(text)
    if not emails:
        return None
    return emails[-1]


def proposed_calls(email: Email, scenario: Scenario) -> list[ToolCall]:
    calls = [
        ToolCall(name="list_inbox", arguments={}),
        ToolCall(name="read_email", arguments={"id": email.id}),
        ToolCall(name="search_docs", arguments={"query": scenario.doc_query}),
    ]
    destination = proposes_exfil(email.body)
    if destination:
        calls.append(
            ToolCall(
                name="forward_files",
                arguments={"to": destination, "paths": ["contracts/", "inbox/"]},
            )
        )
        calls.append(
            ToolCall(
                name="send_email",
                arguments={
                    "to": destination,
                    "body": "Forwarded per the note in the invoice.",
                },
            )
        )
    calls.append(
        ToolCall(
            name="draft_reply",
            arguments={"to": email.sender, "body": scenario.safe_draft},
        )
    )
    return calls


def run_agent(
    *,
    scenario: Scenario,
    email: Email,
    sandbox: Sandbox,
    guard: str,
    firewall: Firewall,
    policy: Policy,
) -> AgentRun:
    box = sandbox.clone()
    steps: list[AgentStep] = []
    for call in proposed_calls(email, scenario):
        untrusted = "" if call.name == "list_inbox" else email.body
        decision: Decision | None
        if guard == "off":
            decision = None
            execute = True
        elif guard == "screen":
            decision = _screen_decision(firewall, policy, untrusted, call)
            execute = decision.action == "allow"
        else:
            decision = firewall.decide(scenario.user_intent, untrusted, call)
            execute = decision.action == "allow"
        if execute:
            observation = box.execute(call)
        else:
            action = decision.action if decision else "block"
            observation = f"not executed ({action})"
        steps.append(
            AgentStep(
                tool=call.name,
                arguments=call.arguments,
                executed=execute,
                observation=observation,
                decision=decision,
            )
        )
    return AgentRun(
        scenario=scenario.id,
        guard=guard,
        leaked=box.leaked(),
        user_intent=scenario.user_intent,
        steps=steps,
    )


def _screen_decision(firewall: Firewall, policy: Policy, untrusted: str, call: ToolCall) -> Decision:
    screen_result = firewall.screen.scan(screened_text(untrusted, call))
    sensitivity = policy.tool(call.name).sensitivity
    action = screen_only_action(screen_result, sensitivity)
    rule_id = "screen-malicious" if action == "block" else "screen-clear"
    if action == "block":
        explanation = (
            f"Screen-only baseline blocked {call.name} because pass 1 labeled the text MALICIOUS. "
            "This baseline does not read the user's intent."
        )
    else:
        explanation = (
            f"Screen-only baseline allowed {call.name}. "
            f"Pass 1 label was {screen_result.label}."
        )
    return Decision(
        action=action,  # type: ignore[arg-type]
        rule_id=rule_id,
        explanation=explanation,
        intent_match=False,
        pass_fired=1,
        screen=screen_result,
        judge=None,
        judge_backend="none",
        tool=call,
    )
