"""Bidirectional NL ↔ NeuroLang compiler.

`compile_source(prompt)`     — natural language → executable Python (a Flow)
`decompile_summary(flow_or_source)` — NeuroLang Python → natural-language summary

The compiler is an LLM call constrained by the registered neuro catalog.
Every compilation is cached at ~/.neurolang/cache/ keyed by
hash(prompt, model, library_version). Round-trip through the cache is
the unit/counit data of the NL ↔ formal adjunction.
"""
from __future__ import annotations

import ast
import hashlib
import os
import textwrap
from typing import Any, Callable, Optional

from . import __version__
from .cache import CompilerCache
from .registry import default_registry
from ._providers import _PROVIDERS, _render_catalog  # re-exported for back-compat
from dataclasses import dataclass, field
from .suggest import suggest_alternatives


@dataclass
class ValidationFindings:
    """Result of validate_source(). Attribute access; backward-compat
    via __getitem__ for any legacy callers using dict syntax."""
    imports: list[str] = field(default_factory=list)
    has_neurolang_import: bool = False
    declares_flow: bool = False
    unknown_refs: list[str] = field(default_factory=list)
    suggestions: dict[str, list[str]] = field(default_factory=dict)

    def __getitem__(self, key):  # pragma: no cover — legacy path
        return getattr(self, key)


# ---------------------------------------------------------------------------
# Forward compiler — NL → NeuroLang Python
#
# Note: `_render_catalog` and `_PROVIDERS` (with their `_llm_call_*` helpers)
# now live in `neurolang/_providers.py`. They are re-imported at the top of
# this module so `from neurolang.compile import _PROVIDERS, _render_catalog`
# keeps working for any external/test code; the canonical location is the
# `_providers` module.
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the NeuroLang compiler. You translate the user's natural-language
intent into Python source code that uses the NeuroLang library.

KEY MENTAL MODEL — read this twice:
A neuro (e.g. `reason.summarize`) is a CALLABLE FLOW NODE, not a function you
invoke at module level. When you write `flow = reason.summarize`, you are
binding the neuro itself (the value) to `flow`. The runtime will later call
it with input via `flow.run(<input>)`. The `|` operator pipes the OUTPUT of
the left neuro into the INPUT of the right neuro. You NEVER write the input
arguments yourself in the flow expression — the runtime supplies them.

OUTPUT RULES (strict):
1. Output ONLY Python source code. No markdown fences, no commentary, no
   leading/trailing prose.
2. Always start with imports from `neurolang` and `neurolang.stdlib` as
   needed. Import `neuro` from `neurolang` whenever you define a helper.
3. Compose flows using the `|` operator (sequential), `&` (parallel-AND),
   `+` (parallel-OR). Never use Python `and`/`or` for flow composition.
4. Use ONLY neuros from the catalog below. Do not invent new ones.
5. The final expression must be `flow = <expression>` where `<expression>`
   is built by COMPOSING catalog neuros (and optional helpers) using the
   flow operators. A single neuro alone is a valid flow:
       flow = reason.summarize        # ← OK: references the neuro by name
6. NEVER call a catalog neuro at module level. These are wrong:
       flow = reason.summarize("...")            # ← WRONG: calls it now
       flow = reason.summarize(text="x")          # ← WRONG: calls it now
       flow = reason.summarize | reason.classify  # ← OK if both take/return str
   The flow expression must be VALUES being composed, not call results.
7. If you need to pre-bind kwargs to a neuro (e.g. `max_words=80`), wrap it
   in a small `@neuro` helper that captures the kwargs and forwards the
   first positional arg. See EXAMPLE 3.
8. If the user's intent requires a small adapter (e.g. picking the first
   element from a list, or formatting a value), declare a local `@neuro`
   helper above the `flow = ...` line.
9. Do not add a `__main__` block — the runtime executes `flow` directly.

CATALOG:
"""


_FEW_SHOT = """\

EXAMPLE 1 (multi-step pipeline)
User: "search for the best Python tutorials and summarize the top result"
Output:
from neurolang import neuro, Flow
from neurolang.stdlib import web, reason

@neuro(effect="tool")
def first_url(results: list[dict]) -> str:
    return web.scrape(results[0]["url"]) if results else ""

flow = web.search | first_url | reason.summarize


EXAMPLE 2 (with side effect)
User: "fetch a URL and store the summary in memory under the key 'page_summary'"
Output:
from neurolang import neuro, Flow
from neurolang.stdlib import web, reason, memory_neuros

@neuro(effect="memory")
def remember(value: str) -> str:
    return memory_neuros.store(value, key="page_summary")

flow = web.scrape | reason.summarize | remember


EXAMPLE 3 (single neuro — runtime supplies input)
User: "summarize a paragraph in one sentence"
Output:
from neurolang import neuro, Flow
from neurolang.stdlib import reason

@neuro(effect="llm")
def summarize_one_sentence(text: str) -> str:
    return reason.summarize(text, max_words=25)

flow = summarize_one_sentence

# At runtime: flow.run("Climate change is altering ocean currents...")


EXAMPLE 4 (idiomatic single-neuro flow, no kwargs)
User: "classify some text"
Output:
from neurolang import Flow
from neurolang.stdlib import reason

flow = reason.classify

# At runtime: flow.run("I love this!", labels=["positive", "negative"])


EXAMPLE 5 (anti-pattern reminder — DO NOT DO THIS)
User: "summarize a paragraph"
WRONG output (the LLM called the neuro at module level, returning a string):
    flow = reason.summarize("")            # ← bug: flow is now an empty str
    flow = reason.summarize(text="x", max_words=25)  # ← same bug
CORRECT output:
    flow = reason.summarize                # ← references the neuro
"""


# ---------------------------------------------------------------------------
# Validation — parse + walk the AST to ensure only registered neuros are used
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    """Some models still emit ```python fences. Strip them."""
    t = text.strip()
    if t.startswith("```"):
        # remove first fence line
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # remove trailing fence
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip()


def validate_source(
    source: str,
    *,
    registry=None,
    strict_refs: bool = False,
) -> ValidationFindings:
    """Parse source and confirm it imports from neurolang + uses real neuros.

    With strict_refs=True, also walks the `flow = <expr>` rhs and flags any
    reference that is neither registered in `registry` nor locally defined.
    """
    reg = registry or default_registry
    tree = ast.parse(source)

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)

    has_neurolang_import = any(
        i == "neurolang" or i.startswith("neurolang.") for i in imports
    )

    flow_assign: ast.Assign | None = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "flow" for t in n.targets
        ):
            flow_assign = n
            break
    declares_flow = flow_assign is not None

    findings = ValidationFindings(
        imports=imports,
        has_neurolang_import=has_neurolang_import,
        declares_flow=declares_flow,
    )

    if strict_refs and flow_assign is not None:
        local_defs = _collect_local_defs(tree, until_lineno=flow_assign.lineno)
        unknown, suggestions = _classify_flow_refs(
            flow_assign.value, local_defs, reg,
        )
        findings.unknown_refs = unknown
        findings.suggestions = suggestions

    return findings


def _collect_local_defs(tree: ast.Module, *, until_lineno: int) -> set[str]:
    """All names defined locally in the source above `until_lineno`.

    Includes Imports / ImportFroms (with `as` aliasing), assignments, function
    defs, async function defs, and class defs. We don't try to resolve nested
    scopes — flat module scope is enough for the LLM-generated source we
    validate (which is always one module-level `flow = <expr>` after a few
    imports / one-liner @neuro defs).
    """
    names: set[str] = set()
    for n in tree.body:
        if n.lineno >= until_lineno:
            break
        if isinstance(n, ast.Import):
            for a in n.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                names.add(a.asname or a.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(n.name)
    return names


def _resolve_attr_chain(node: ast.AST) -> str | None:
    """Resolve `Attribute(Attribute(Name('a'), 'b'), 'c')` → 'a.b.c'.
    Returns None if the chain bottoms out in something other than a Name
    (e.g., a function call result)."""
    parts: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _head_of_ref(ref: str) -> str:
    """First dotted segment, e.g. 'a.b.c' → 'a'."""
    return ref.split(".", 1)[0]


def _classify_flow_refs(
    flow_expr: ast.expr,
    local_defs: set[str],
    registry,
) -> tuple[list[str], dict[str, list[str]]]:
    """Walk the flow expression; classify each top-level Name/Attribute.

    Returns (unknown_refs, suggestions).

    Only TOP-LEVEL Name/Attribute nodes are checked — inner nodes that are
    part of a larger chain (e.g., the inner `a.b` inside `a.b.c`, or the
    `web` in `web.search`) are skipped via a parent map. This avoids
    falsely flagging `a.b` as unknown when `a.b.c` is the actual
    registered name.

    A ref is OK if its full dotted name is in the registry OR its head
    is in local_defs. Otherwise it goes into unknown_refs (with suggestions).
    """
    unknown: list[str] = []
    suggestions: dict[str, list[str]] = {}
    seen: set[str] = set()
    registry_names = {n.name for n in registry}

    # Build a parent map so we can ask "is this node nested inside an Attribute?"
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(flow_expr):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    for node in ast.walk(flow_expr):
        # Top-level only: its parent must NOT be an Attribute. The root
        # of `flow_expr` has no parent in the map; treat that as top-level.
        parent = parents.get(id(node))
        if isinstance(parent, ast.Attribute):
            continue

        if isinstance(node, ast.Attribute):
            ref = _resolve_attr_chain(node)
            if ref is None:
                continue  # e.g., a method call on a non-Name base
        elif isinstance(node, ast.Name):
            ref = node.id
        else:
            continue

        if ref in seen:
            continue
        seen.add(ref)

        if ref in registry_names:
            continue
        if _head_of_ref(ref) in local_defs:
            continue

        unknown.append(ref)
        suggestions[ref] = suggest_alternatives(ref, registry)

    return unknown, suggestions


# ---------------------------------------------------------------------------
# Forward: compile_source()
# ---------------------------------------------------------------------------

def compile_source(
    prompt: str,
    *,
    model: Optional[str] = None,
    output: str = "flow",         # "flow" | "source" | "both"
    use_cache: bool = True,
    cache: Optional[CompilerCache] = None,
    llm_fn: Optional[Callable[..., str]] = None,
    registry=None,
) -> Any:
    """Compile a natural-language prompt into NeuroLang Python.

    Parameters
    ----------
    prompt : str
        The natural-language description of the flow to build.
    model : str
        "openai" | "anthropic" — or pass `llm_fn` to override entirely.
    output : str
        "flow"   → execute the generated source and return the `flow` object.
        "source" → return the generated Python source as a string.
        "both"   → return (flow, source).
    use_cache : bool
        If True, cache hits skip the LLM call.
    llm_fn : callable, optional
        A custom LLM callable: `llm_fn(prompt, system, model=...) -> str`.
    """
    cache = cache or CompilerCache()
    reg = registry or default_registry
    lib_version = __version__
    from ._providers import normalize_provider
    provider = normalize_provider(model)
    catalog_md = _render_catalog(reg)
    system_fingerprint = hashlib.sha256(
        (_SYSTEM_PROMPT + _FEW_SHOT + catalog_md).encode()
    ).hexdigest()[:8]
    cache_key = cache.make_key(
        prompt, model=provider, library_version=lib_version,
        system_fingerprint=system_fingerprint,
    )

    # 1. Cache lookup
    source: Optional[str] = None
    if use_cache:
        hit = cache.get_forward(cache_key)
        if hit is not None:
            source = open(hit.source_path).read()

    # 2. Compile via LLM
    if source is None:
        system = _SYSTEM_PROMPT + catalog_md + _FEW_SHOT

        if llm_fn is not None:
            raw = llm_fn(prompt, system, model=provider, kind="compile")
        else:
            if provider not in _PROVIDERS:
                raise ValueError(
                    f"Unknown model: {provider!r}. Use one of {list(_PROVIDERS)} or pass llm_fn=..."
                )
            fn, default_model_name = _PROVIDERS[provider]
            raw = fn(prompt, system, model=default_model_name, kind="compile")

        source = _strip_code_fences(raw)

        # 3. Validate (strict mode for compile — fail fast on unknown refs)
        try:
            findings = validate_source(source, registry=reg, strict_refs=True)
        except SyntaxError as e:
            raise CompileError(
                f"LLM produced invalid Python: {e}\n\nSOURCE:\n{source}"
            ) from e
        if not findings.has_neurolang_import:
            raise CompileError(
                "Generated code does not import from neurolang. Re-run.\n\nSOURCE:\n" + source
            )
        if not findings.declares_flow:
            raise CompileError(
                "Generated code does not declare a `flow` variable.\n\nSOURCE:\n" + source
            )
        if findings.unknown_refs:
            lines = ["Generated source references unknown neuros.\n"]
            for ref in findings.unknown_refs:
                hints = findings.suggestions.get(ref, [])
                if hints:
                    lines.append(f"Unknown:  {ref}\n  Did you mean? {', '.join(hints)}")
                else:
                    lines.append(f"Unknown:  {ref}\n  No close matches in registry.")
            lines.append("\nSource:\n" + source)
            raise CompileError("\n".join(lines))

        # 4. Cache forward
        if use_cache:
            cache.put_forward(
                key=cache_key, prompt=prompt, model=provider,
                library_version=lib_version, source=source,
            )

    # 5. Return
    if output == "source":
        return source
    flow = _exec_flow(source)
    if output == "both":
        return flow, source
    return flow


def _exec_flow(source: str) -> Any:
    """Execute generated source in an isolated namespace and return `flow`."""
    ns: dict = {}
    exec(compile_python(source, "<neurolang.compiled>", "exec"), ns)
    if "flow" not in ns:
        raise CompileError("Compiled source did not produce a `flow` variable.")
    return ns["flow"]


# Avoid shadowing builtins.compile inside this module
compile_python = __builtins__["compile"] if isinstance(__builtins__, dict) else __builtins__.compile


class CompileError(Exception):
    """Raised when NL→NeuroLang compilation fails or produces invalid output."""


# ---------------------------------------------------------------------------
# Reverse: decompile_summary() — Python source → NL summary
# ---------------------------------------------------------------------------

_DECOMPILE_SYSTEM = """\
You are the NeuroLang summarizer. Given Python source code that uses
NeuroLang primitives, produce a single concise paragraph (1-3 sentences)
describing what the flow does, in plain natural language.

OUTPUT RULES:
- One short paragraph only. No bullet points, no code, no markdown.
- Mention the key actions (search, scrape, summarize, etc.) and their order.
- If memory or effects are involved, mention them briefly.
"""


def decompile_summary(
    flow_or_source: Any,
    *,
    model: Optional[str] = None,
    cache: Optional[CompilerCache] = None,
    use_cache: bool = True,
    llm_fn: Optional[Callable[..., str]] = None,
) -> str:
    """Produce a natural-language summary of a NeuroLang Flow or source."""
    cache = cache or CompilerCache()
    from ._providers import normalize_provider
    provider = normalize_provider(model)

    if isinstance(flow_or_source, str):
        source = flow_or_source
    else:
        # It's a Flow object — produce a structural representation
        from .flow import Flow
        if not isinstance(flow_or_source, Flow):
            raise TypeError(f"decompile_summary() expected str or Flow, got {type(flow_or_source).__name__}")
        source = _flow_to_pseudo_source(flow_or_source)

    cache_key = cache.make_key("decompile:" + source, model=provider, library_version=__version__)
    if use_cache:
        cached_summary = cache.get_summary(cache_key)
        if cached_summary:
            return cached_summary

    if llm_fn is not None:
        summary = llm_fn(source, _DECOMPILE_SYSTEM, model=provider, kind="decompile")
    else:
        if provider not in _PROVIDERS:
            raise ValueError(f"Unknown model: {provider!r}")
        fn, default_model_name = _PROVIDERS[provider]
        summary = fn(source, _DECOMPILE_SYSTEM, model=default_model_name, kind="decompile")

    summary = summary.strip()
    if use_cache:
        cache.put_forward(
            key=cache_key, prompt="decompile:" + source[:200], model=provider,
            library_version=__version__, source=source,
        )
        cache.put_summary(cache_key, summary)
    return summary


def _flow_to_pseudo_source(flow) -> str:
    """Render a Flow as a snippet of pseudo-Python (for the summarizer)."""
    names = [n.name for n in flow.neuros()]
    return f"flow = {' | '.join(names)}\n# effects: {sorted(flow.effect_signature())}"
