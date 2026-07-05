"""
Local LLM client for clinical-text field extraction.

Narrative clinical text is processed by a LOCALLY HOSTED open-weight model (Qwen, via
Apple MLX): extraction runs entirely on-device, so the pipeline can process clinical
text without it leaving the secure environment — no network calls, no API keys, no cost.

Callers get a uniform LLMResult and do not need to know which model produced the output.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# On-premise open-weight model (override with the LOCAL_LLM_MODEL env var).
LOCAL_DEFAULT_MODEL = os.environ.get("LOCAL_LLM_MODEL", "mlx-community/Qwen2.5-3B-Instruct-4bit")


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    elapsed_sec: float
    raw: dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    pass


# ---------------------------------------------------------------------------
# Local (on-premise) open-weight model backend.
# Runs fully on-device via Apple MLX; no network call, no data egress.
# ---------------------------------------------------------------------------

_local_model = None
_local_tok = None
_local_lock = threading.Lock()
# A single on-device model shares one GPU; serialize generation across pipeline threads
# (MLX generate is not safe to call concurrently on the same model instance).
_local_gen_lock = threading.Lock()


def _load_local(model: str):
    global _local_model, _local_tok
    with _local_lock:
        if _local_model is None:
            from mlx_lm import load as _mlx_load
            _local_model, _local_tok = _mlx_load(model)
    return _local_model, _local_tok


def local_generate(
    prompt: str,
    *,
    model: str = LOCAL_DEFAULT_MODEL,
    response_json_schema: Optional[dict] = None,
    temperature: float = 0.0,
    max_output_tokens: int = 4096,
    system: Optional[str] = None,
) -> LLMResult:
    """Generate with a locally hosted open-weight model (MLX). No network, no data egress.

    cost_usd is always 0.0 (local compute).
    """
    from mlx_lm import generate as _mlx_generate

    m, tok = _load_local(model)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    user = prompt
    if response_json_schema is not None:
        user += ("\n\nReturn ONLY a single JSON object conforming to this schema:\n"
                 + json.dumps(response_json_schema))
    msgs.append({"role": "user", "content": user})
    text = tok.apply_chat_template(msgs, add_generation_prompt=True)

    t0 = time.time()
    with _local_gen_lock:  # serialize GPU access across threads
        if temperature and temperature > 0:
            from mlx_lm.sample_utils import make_sampler
            out = _mlx_generate(m, tok, prompt=text, max_tokens=max_output_tokens,
                                sampler=make_sampler(temp=temperature), verbose=False)
        else:  # deterministic greedy decode (temperature == 0)
            out = _mlx_generate(m, tok, prompt=text, max_tokens=max_output_tokens, verbose=False)
    elapsed = time.time() - t0

    try:
        tin, tout = len(tok.encode(text)), len(tok.encode(out))
    except Exception:
        tin = tout = 0
    return LLMResult(text=out, model=model, tokens_in=tin, tokens_out=tout,
                     cost_usd=0.0, elapsed_sec=elapsed, raw={})


# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

def parse_json_lenient(text: str) -> Any:
    """Parse JSON from an LLM response, tolerating fenced code blocks."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[: -3]
        s = s.strip()
    return json.loads(s)
