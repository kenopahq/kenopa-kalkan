"""Deterministic stand-in for the Muse Spark judge.

Used only by the mock provider. Live mode never calls this module. Decisions
are a reading of policy/default.yaml, not a claim about what Muse Spark would say.
"""

from __future__ import annotations

import json
import re

from kalkan.text import FORWARD_REQUEST, SEND_REQUEST, find_emails, phrase_authorized

_SECRET = re.compile(r"(\.env\b|password|api[_-]?key|\bsecret\b|parola|gizli anahtar)", re.IGNORECASE)
_READ_TOOLS = frozenset({"list_inbox", "read_email", "search_docs", "read_doc"})


def _verdict(action: str, rule_id: str, intent_match: bool, explanation: str) -> dict:
    return {
        "action": action,
        "rule_id": rule_id,
        "explanation": explanation,
        "intent_match": intent_match,
    }


def deterministic_verdict(payload: dict) -> dict:
    intent = str(payload.get("user_intent", ""))
    tool = payload["tool"]["name"]
    args = payload["tool"].get("arguments") or {}
    screen_label = payload["screen"]["label"]
    sensitivity = payload.get("sensitivity", "high")

    if tool == "read_secret":
        return _verdict(
            "block",
            "no-exfil",
            False,
            "Blocked by rule no-exfil. Reading secrets is denied by policy. Untrusted text cannot grant it.",
        )

    if tool in _READ_TOOLS:
        extra = ""
        if screen_label == "MALICIOUS":
            extra = " Pass 1 flagged the content as MALICIOUS. The read is still allowed, and the text stays data."
        return _verdict(
            "allow",
            "allow-read",
            True,
            "Allowed by rule allow-read. The tool only reads sandbox data and fits the user's request." + extra,
        )

    if tool == "forward_files":
        dest = str(args.get("to", ""))
        if phrase_authorized(intent, FORWARD_REQUEST, dest) and dest:
            return _verdict(
                "confirm",
                "confirm-outbound",
                True,
                f"Held by rule confirm-outbound. The user intent names a forward to {dest}. "
                "Policy still requires a person to confirm before files leave the sandbox.",
            )
        if screen_label == "MALICIOUS":
            return _verdict(
                "block",
                "no-instruction-override",
                False,
                "Blocked by rule no-instruction-override. The user did not ask to forward files. "
                "The untrusted content tries to override that, and pass 1 marked it MALICIOUS.",
            )
        return _verdict(
            "block",
            "no-exfil",
            False,
            "Blocked by rule no-exfil. Forwarding files is high-sensitivity and the user intent "
            "does not authorize this destination. Pass 1 did not flag the text. Pass 2 stopped the call.",
        )

    if tool == "send_email":
        dest = str(args.get("to", ""))
        body = str(args.get("body", ""))
        authorized = phrase_authorized(intent, SEND_REQUEST, dest) and bool(dest)
        if authorized and screen_label != "MALICIOUS" and not _SECRET.search(body):
            return _verdict(
                "confirm",
                "confirm-outbound",
                True,
                f"Held by rule confirm-outbound. The user intent asks to send email to {dest}. "
                "Policy still requires a person to confirm outbound mail.",
            )
        if screen_label == "MALICIOUS":
            return _verdict(
                "block",
                "no-instruction-override",
                False,
                "Blocked by rule no-instruction-override. Outbound email is not authorized by the user, "
                "and pass 1 marked the untrusted content MALICIOUS.",
            )
        return _verdict(
            "block",
            "no-exfil",
            False,
            "Blocked by rule no-exfil. The user did not authorize a send to this recipient.",
        )

    if tool == "draft_reply":
        body = str(args.get("body", ""))
        if _SECRET.search(body):
            return _verdict(
                "block",
                "no-exfil",
                False,
                "Blocked by rule no-exfil. The draft contains secret material.",
            )
        for addr in find_emails(body):
            if addr.lower() not in intent.lower():
                return _verdict(
                    "block",
                    "no-exfil",
                    False,
                    f"Blocked by rule no-exfil. The draft introduces {addr}, which the user did not name.",
                )
        return _verdict(
            "allow",
            "allow-read",
            True,
            "Allowed by rule allow-read. The draft stays on task and does not add an external destination or a secret. "
            "Instructions in the untrusted text were not copied into it.",
        )

    if sensitivity in {"high", "critical"}:
        return _verdict(
            "block",
            "no-exfil",
            False,
            "Blocked by rule no-exfil. The tool is high-sensitivity and is not on the allow list.",
        )
    return _verdict(
        "confirm",
        "confirm-outbound",
        False,
        "Held by rule confirm-outbound. The tool is not in the policy allow list.",
    )


def payload_from_messages(messages: list[dict]) -> dict:
    marker = "KALKAN_PAYLOAD "
    for message in messages:
        content = message.get("content") or ""
        index = content.find(marker)
        if index < 0:
            continue
        raw = content[index + len(marker) :]
        # The payload is a single JSON object and may be followed by nothing else.
        return json.loads(raw)
    raise ValueError("Judge or attacker prompt is missing KALKAN_PAYLOAD.")
