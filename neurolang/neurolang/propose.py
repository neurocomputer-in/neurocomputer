"""NL → ProposedPlan: the planner one rung above `compile_source`.

Single LLM call. The model is asked to return JSON with three keys:
    neuros:      list[str]   — registered neuro names it would use
    composition: str         — the proposed `flow = ...` Python source
    missing:     list[dict]  — capabilities the catalog can't satisfy,
                               each `{"intent": "<short phrase>"}`

We then look each named neuro up in the registry, pull cost + latency from
its Budget, and call suggest.suggest_alternatives() for each missing intent.
The result is a JSON-serializable ProposedPlan.

Caching uses the same CompilerCache as compile_source(), with a "propose:" prefix
on the prompt so the keys don't collide.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import __version__
from .cache import CompilerCache
from ._providers import _render_catalog, _PROVIDERS
from .discover import find_project_root
from .registry import default_registry
from .suggest import suggest_alternatives


# ---- Public dataclasses ----------------------------------------------------

@dataclass(frozen=True)
class NeuroChoice:
    name: str
    effects: list[str]
    cost_estimate_usd: float
    latency_estimate_ms: int


@dataclass(frozen=True)
class MissingCapability:
    intent: str
    suggestions: list[str]


@dataclass(frozen=True)
class ProposedPlan:
    prompt: str
    composition_source: str
    neuros: list[NeuroChoice]
    missing: list[MissingCapability]
    cost_estimate_usd: float
    latency_estimate_ms: int
    project_root: Optional[Path]


class ProposeError(Exception):
    """Raised on invalid LLM JSON or unparseable proposal."""


# ---- The proposal system prompt -------------------------------------------

# The system prompt's wording is no longer load-bearing — test fakes dispatch
# via the explicit `kind` kwarg, not substring sniffing.
_PLAN_SYSTEM_PROMPT = """\
You are the NeuroLang planner. Given the user's natural-language intent
and the catalog of available neuros, propose a flow.

OUTPUT RULES (strict):
1. Output ONLY a single JSON object. No markdown fences, no commentary.
2. The object MUST have exactly these keys:
     "neuros":      [<registered neuro names you would use>],
     "composition": "<the proposed `flow = ...` Python source, one line>",
     "missing":     [{"intent": "<short phrase>"}, ...]
3. Use ONLY neuros that appear in the catalog. Put unmet needs in `missing`.
4. The composition string must compose only those neuros using `|`, `&`, `+`.
5. Reference each neuro by its full registered name in `neuros`; in
   `composition`, use the short usable form (e.g., `web.search`).
6. If the catalog cannot satisfy ANY part of the intent, return:
     {"neuros": [], "composition": "", "missing": [{"intent": "..."}]}

CATALOG:
"""


_PLAN_FEW_SHOT = """\

EXAMPLE
User: "search for python tutorials and summarize the top result"
Catalog has: web.search (tool), reason.summarize (llm)
Output:
{"neuros": ["web.search", "reason.summarize"],
 "composition": "flow = web.search | reason.summarize",
 "missing": []}
"""


# ---- The proposer ---------------------------------------------------------

def _get_or_call_llm(
    prompt: str,
    *,
    model: str,
    llm_fn: Optional[Callable[..., str]],
    cache: CompilerCache,
    use_cache: bool,
    catalog_md_renderer,
) -> str:
    """Cache lookup + LLM call. Returns the raw payload JSON string."""
    cache_key = cache.make_key(
        f"propose:{prompt}", model=model, library_version=__version__,
    )
    if use_cache:
        hit = cache.get_forward(cache_key)
        if hit is not None:
            return Path(hit.source_path).read_text()

    catalog_md = catalog_md_renderer()
    system = _PLAN_SYSTEM_PROMPT + catalog_md + _PLAN_FEW_SHOT

    if llm_fn is not None:
        raw = llm_fn(prompt, system, model=model, kind="plan")
    else:
        if model not in _PROVIDERS:
            raise ValueError(
                f"Unknown model: {model!r}. Use one of {list(_PROVIDERS)} or pass llm_fn=..."
            )
        fn, default_model_name = _PROVIDERS[model]
        raw = fn(prompt, system, model=default_model_name, kind="plan")

    payload_json = raw.strip()
    if use_cache:
        cache.put_forward(
            key=cache_key,
            prompt=f"propose:{prompt}",
            model=model,
            library_version=__version__,
            source=payload_json,
        )
    return payload_json


def _parse_and_validate(payload_json: str) -> dict:
    """JSON parse + shape validate. Raises ProposeError on either failure."""
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        raise ProposeError(
            f"Planner returned non-JSON: {e}\n\nRAW:\n{payload_json}"
        ) from e
    if not isinstance(payload, dict) \
            or not isinstance(payload.get("neuros"), list) \
            or not isinstance(payload.get("composition"), str) \
            or not isinstance(payload.get("missing"), list):
        raise ProposeError(
            f"Planner JSON has invalid shape — expected "
            f"{{neuros: list, composition: str, missing: list}}.\n\nRAW:\n{payload_json}"
        )
    return payload


def _resolve_neuro_name(name: str, reg) -> Optional[str]:
    """Resolve an LLM-emitted neuro name to a registered full name.

    Tries: (1) exact match, (2) unique-suffix match. Returns None if neither
    succeeds. Handles the common LLM pattern of emitting short names like
    `reason.summarize` when the registry stores `neurolang.stdlib.reason.summarize`.
    """
    if reg.get(name) is not None:
        return name
    candidates = [n.name for n in reg if n.name.endswith("." + name) or n.name == name]
    return candidates[0] if len(candidates) == 1 else None


def propose_plan(
    prompt: str,
    *,
    model: Optional[str] = None,
    llm_fn: Optional[Callable[..., str]] = None,
    registry=None,
    cache: Optional[CompilerCache] = None,
    use_cache: bool = True,
) -> ProposedPlan:
    """Propose a flow for `prompt` against the registered catalog.

    One LLM call. Cost rolled up locally from each neuro's Budget metadata.
    """
    reg = registry or default_registry
    cache = cache or CompilerCache()
    from ._providers import normalize_provider
    provider = normalize_provider(model)

    payload_json = _get_or_call_llm(
        prompt,
        model=provider,
        llm_fn=llm_fn,
        cache=cache,
        use_cache=use_cache,
        catalog_md_renderer=lambda: _render_catalog(reg),
    )
    payload = _parse_and_validate(payload_json)

    # Look up each named neuro and roll up cost + latency
    neuros: list[NeuroChoice] = []
    cost_total = 0.0
    latency_total = 0
    for name in payload["neuros"]:
        resolved = _resolve_neuro_name(name, reg)
        n = reg.get(resolved) if resolved else None
        if n is None:
            # The LLM named a neuro that doesn't exist — this is a soft
            # failure: include it in `missing` instead of raising. The
            # composition string will reference it; strict-refs validation
            # will catch it later when compile_source() runs.
            payload["missing"].append({"intent": f"unknown neuro: {name}"})
            continue
        cost = float(n.budget.cost_usd or 0.0)
        latency = int(n.budget.latency_ms or 0)
        neuros.append(
            NeuroChoice(
                name=n.name,
                effects=sorted(e.value for e in n.effects),
                cost_estimate_usd=cost,
                latency_estimate_ms=latency,
            )
        )
        cost_total += cost
        # NOTE: assumes sequential (`|`) composition; parallel (`&`/`+`) flows
        # would max-not-sum, so this over-estimates for non-sequential plans.
        latency_total += latency

    missing = [
        MissingCapability(
            intent=str(m.get("intent", "")),
            suggestions=suggest_alternatives(str(m.get("intent", "")), reg),
        )
        for m in payload["missing"]
    ]

    return ProposedPlan(
        prompt=prompt,
        composition_source=str(payload["composition"]),
        neuros=neuros,
        missing=missing,
        cost_estimate_usd=cost_total,
        latency_estimate_ms=latency_total,
        project_root=find_project_root(),
    )
