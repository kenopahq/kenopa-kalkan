"""Llama Prompt Guard 2 86M, loaded only when the operator asks for it.

The weights are gated on Hugging Face and are not downloaded from tests or
from the default server start. Windowing is pure Python so it can be tested
without torch.
"""

from __future__ import annotations

from kalkan.models import ScreenResult

# Leave room for special tokens inside the 512-token window.
WINDOW_SIZE = 480
WINDOW_STRIDE = 240
CONTEXT = 512


class PromptGuardError(RuntimeError):
    pass


def iter_token_windows(token_count: int, size: int = WINDOW_SIZE, stride: int = WINDOW_STRIDE) -> list[tuple[int, int]]:
    """Spans covering a token sequence, each short enough for Prompt Guard 2."""
    if token_count <= CONTEXT:
        return [(0, token_count)]
    spans: list[tuple[int, int]] = []
    start = 0
    while start < token_count:
        end = min(token_count, start + size)
        spans.append((start, end))
        if end == token_count:
            break
        start += stride
    return spans


class PromptGuardScreen:
    """Classifier over Llama Prompt Guard 2.

    `model` and `tokenizer` are injected so tests can run the windowing path
    without downloading weights. `from_pretrained` is the production loader.
    """

    def __init__(self, model, tokenizer, model_id: str):
        self.model = model
        self.tokenizer = tokenizer
        self.model_id = model_id
        self.backend = "llama-prompt-guard-2-86m"
        labels = getattr(getattr(model, "config", None), "id2label", None) or {0: "BENIGN", 1: "MALICIOUS"}
        self.id2label = {int(idx): str(label) for idx, label in labels.items()}

    @classmethod
    def from_pretrained(cls, model_id: str) -> PromptGuardScreen:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise PromptGuardError(
                "transformers is not installed. Install with pip install -e '.[prompt-guard]'."
            ) from exc
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForSequenceClassification.from_pretrained(model_id)
        except Exception as exc:
            raise PromptGuardError(
                f"Could not load {model_id}. Accept the Llama licence on Hugging Face "
                "and set HF_TOKEN, or keep KALKAN_SCREEN=heuristic."
            ) from exc
        model.eval()
        return cls(model, tokenizer, model_id)

    def _windows(self, text: str) -> list[str]:
        encoded = self.tokenizer(text, add_special_tokens=False)
        ids = encoded["input_ids"]
        spans = iter_token_windows(len(ids))
        chunks: list[str] = []
        for start, end in spans:
            piece = ids[start:end]
            decode = getattr(self.tokenizer, "decode", None)
            if decode is None:
                chunks.append(" ".join(str(token) for token in piece))
            else:
                chunks.append(decode(piece))
        return chunks or [text]

    def _classify(self, text: str) -> tuple[str, float]:
        import torch

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=CONTEXT)
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        index = int(torch.argmax(probs).item())
        label = self.id2label.get(index, "BENIGN")
        malicious_index = next(
            (idx for idx, name in self.id2label.items() if "MALICIOUS" in name.upper()),
            None,
        )
        if malicious_index is None:
            score = float(probs[index]) if "MALICIOUS" in label.upper() else 0.0
        else:
            score = float(probs[malicious_index])
        normalized = "MALICIOUS" if "MALICIOUS" in label.upper() else "BENIGN"
        return normalized, score

    def scan(self, text: str) -> ScreenResult:
        if not text.strip():
            return ScreenResult(
                label="BENIGN",
                score=0.0,
                backend=self.backend,
                backend_note=self.model_id,
            )
        best_label = "BENIGN"
        best_score = 0.0
        for chunk in self._windows(text):
            label, score = self._classify(chunk)
            if label == "MALICIOUS" and score >= best_score:
                best_label = "MALICIOUS"
                best_score = score
            elif best_label == "BENIGN":
                best_score = max(best_score, score)
        return ScreenResult(
            label=best_label,  # type: ignore[arg-type]
            score=round(best_score, 4),
            backend=self.backend,
            matched_rule_ids=["prompt-guard-2"] if best_label == "MALICIOUS" else [],
            backend_note=self.model_id,
        )
