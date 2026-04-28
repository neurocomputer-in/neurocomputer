# Changelog

> Append-only log of shipped features and changes. Most recent at top.
> For the long-term plan, see [`docs/ROADMAP.md`](./docs/ROADMAP.md).
> For the current state of work, see [`docs/STATUS.md`](./docs/STATUS.md).

The format is loosely based on [Keep a Changelog](https://keepachangelog.com).
This project follows [Semantic Versioning](https://semver.org) — pre-1.0 means APIs may break.

---

## [Unreleased]

*(work in progress on the `main` branch — pushed to `git@github.com:neurocomputer-in/neurolang.git`, not yet tagged)*

### Added (Phase 1.9 — `email` stdlib)

- **`neurolang.stdlib.email`** — four neuros backed by Python stdlib
  `imaplib` + `smtplib` (zero new dependencies):
  - `email.send(to, subject, body, *, cc=None, bcc=None, html=False) → dict`
    — builds a real `EmailMessage` (correct MIME), routes BCC via SMTP envelope
    (not headers), returns `{"sent": True, "to": [...], "subject": "..."}`.
  - `email.read(folder="INBOX", *, n=10, unread_only=False) → list[dict]`
    — RFC822 parsing via `email.parser.BytesParser(policy=policy.default)`,
    auto-decodes RFC2047 subjects, prefers `text/plain` from
    `multipart/alternative`, falls back to a stdlib-only HTML stripper
    (`html.parser`) when only HTML available. Each message: `uid`, `from`,
    `to`, `cc`, `subject`, `date` (ISO 8601), `body`, `snippet`, `unread`,
    `flagged`.
  - `email.search(query, *, folder="INBOX", n=20) → list[dict]` — passes
    IMAP SEARCH syntax verbatim (`'FROM "boss@x" SINCE 1-Jan-2026 UNSEEN'`).
    Same dict shape as `read`. Malformed syntax surfaces as `EmailError`.
  - `email.mark(uid, flag, *, folder="INBOX") → bool` — `flag ∈
    {"seen","unseen","flagged","unflagged","deleted"}` mapping to correct
    IMAP STORE `+FLAGS`/`-FLAGS` ops.
- **Domain auto-detect** — `_DOMAIN_DEFAULTS` dict maps `@gmail.com` /
  `@outlook.com` / `@hotmail.com` / `@yahoo.com` to their IMAP+SMTP hosts.
  Unknown domain w/o explicit `EMAIL_IMAP_HOST`/`EMAIL_SMTP_HOST` →
  `RuntimeError` with helpful message. Explicit env always overrides.
- **Config via env** — `EMAIL_ADDR`, `EMAIL_APP_PASSWORD`,
  `EMAIL_IMAP_HOST`/`EMAIL_IMAP_PORT` (default 993), `EMAIL_SMTP_HOST`/
  `EMAIL_SMTP_PORT` (default 465), `EMAIL_BACKEND` (default `imap`;
  `gmail` reserved for v1.1 — currently `NotImplementedError`). Missing
  required env raises at first use, never at import.
- **`EmailError(operation, cause)`** — wraps `imaplib.IMAP4.error`,
  `smtplib.SMTPException`, `OSError` with operation context for clear
  failure traces (`EmailError("send", SMTPAuthenticationError(...))`).
- **Filename `email_neuros.py`** mirrors the existing `memory_neuros.py`
  precedent — avoids shadowing Python's stdlib `email` package.
  `stdlib/__init__.py` re-exports it as `email`; public catalog name
  stays `neurolang.stdlib.email.<fn>`.
- **REPL banner picks it up** — `STDLIB_NAMESPACES` extended with
  `("email", email_neuros)`; banner now reports the email neuros in its
  stdlib count.
- **Tests** — `tests/stdlib/test_email.py` (25 tests) patches
  `imaplib.IMAP4_SSL` and `smtplib.SMTP_SSL` with `MagicMock`; canned
  RFC822 fixtures built via real `EmailMessage`. Full suite 172/172
  passing offline (~0.67s, was 147/147).
- **Live demo** — `examples/email_demo.py` sends a self-test email and
  reads it back; skip-cleanly-on-missing-creds pattern from
  `examples/research_flow.py`.

### Added (Phase 1.8 — `agent.delegate`, recursive composition)

- **`neurolang.stdlib.agent.delegate(task, *, catalog=None, depth=1, model=None) → Neuro`**
  — factory pattern: each call returns a fresh `@neuro(register=False)` closure
  with `task` baked in. Composes naturally with `|` since the returned
  value is a Neuro: `flow = upstream | agent.delegate("summarize")`.
  Inner `_agent` is `async` so `await flow.run_async(input_value)` shares
  the parent's event loop (sync `flow.run()` would deadlock).
- **Catalog scoping** — `catalog=["neurolang.stdlib.reason.*"]` builds a
  fresh `Registry` (via `fnmatch.fnmatchcase`) containing only matching
  neuros, passed to both `propose_plan(registry=...)` and
  `compile_source(registry=...)`. Default `catalog=None` exposes the
  full `default_registry`.
- **Memory inheritance** — agent captures `current_memory()` at call
  time and passes through to `flow.run_async(input_value, memory=parent_memory)`.
  Without this, the inner Plan.run_async would default `memory=None`
  and clobber the parent's ContextVar.
- **Depth budget** — `_delegation_depth: ContextVar[Optional[int]]`.
  `delegate(..., depth=0)` raises `DelegationBudgetExhausted` on call;
  default `depth=1` permits one level of recursion. Negative depth
  rejected at construction time with `ValueError`.
- **Failure modes** — planner returning `missing != []` produces a soft-fail
  string `"[delegate: cannot satisfy task — missing: {intents}]"` (caller
  can pattern-match without wrapping in try/except). `CompileError` inside
  the sub-flow wraps as `DelegationFailed(task, cause)` for clear stack
  traces. Sub-flow runtime errors propagate unchanged.
- **`propose._resolve_neuro_name(name, reg)`** (bonus fix) — resolves
  short LLM-emitted names like `reason.summarize` to the unique full
  registered name `neurolang.stdlib.reason.summarize` via suffix matching.
  Ambiguous suffixes still fail through to `missing`. Found while
  exercising `agent.delegate` against the live LLM, fixes a long-standing
  pre-existing planner bug that produced spurious soft-fails.
- 11 new tests (9 in `tests/stdlib/test_agent.py` + 2 in
  `tests/test_propose.py`). Live demo at `examples/agent_delegate.py`
  runs an outer flow whose middle step plans + compiles its own inner
  flow at runtime against the configured LLM.
- 137/137 tests offline (~0.19s).

### Fixed (`max_tokens` per call kind)

- **`_providers.py:_KIND_MAX_TOKENS`** — maps each call kind to its output token ceiling:
  `compile` 2048, `decompile` 512, `plan` 2048, `reason` 2048, `reason.deep` 4096.
  Both `_llm_call_via_openai_sdk` and `_llm_call_anthropic` look up `_KIND_MAX_TOKENS.get(kind, 2048)`
  instead of hard-coding 2048. Unknown future kinds fall back to 2048.
- **`stdlib/reason.py:_call_llm`** gains `kind: str = "reason"` kwarg.
  `deep_research(depth="deep")` now routes `kind="reason.deep"` → 4096 tokens,
  eliminating mid-sentence truncation for ~1500-word outputs.
- **`PROVIDER_KINDS`** extended to include `"reason"` and `"reason.deep"`.
- 10 new tests in `tests/test_providers.py` (mapping assertions + payload capture
  for compile/decompile/reason.deep/unknown-fallback). 147/147 total.

### Fixed (cache key fingerprinting)

- **`cache.make_key()` gains optional `system_fingerprint=""` kwarg.**
  `compile_source` computes `sha256(_SYSTEM_PROMPT + _FEW_SHOT + catalog_md)[:8]`
  upfront and threads it into the key. Changing the compile prompt or
  registering a new neuro now auto-invalidates stale cache entries —
  no more manual `neurolang cache clear` after prompt edits.
- 4 new tests (different fingerprint → different key, backward-compat
  with empty default, end-to-end prompt-change → cache miss).

### Added (Phase 1.7 — multi-provider LLM registry)

- **`neurolang/_providers.py` — full multi-provider registry mirroring neurocomputer.**
  Five providers: `opencode-zen` (default), `openrouter`, `openai`, `anthropic`, `ollama`.
  Each entry has `env_key`, `base_url`, `default_model`, `headers`, `aliases`, `models` list.
  `DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "opencode-zen")`.
  Default model: `opencode/minimax-m2.5-free`.
- **Auth fallback** — `opencode-zen` reads `~/.local/share/opencode/auth.json` (key `opencode.key`)
  if `OPENCODE_API_KEY` env var unset. `get_api_key(provider)` exported for custom callers.
- **All caller defaults flipped from `model="openai"` to `model=None`** — resolves via
  `normalize_provider(None)` → `DEFAULT_PROVIDER`. Affected: `compile_source`, `decompile_summary`,
  `propose_plan`, all 4 `reason.*` fns (summarize, classify, brainstorm, deep_research).
- **`stdlib/reason.py`** — private `_call_llm(prompt, model=None)` helper routes directly through
  `_PROVIDERS`; per-fn `if model == "openai" / "anthropic"` dispatch chains removed.
  `strict=True` on `normalize_provider` — unknown provider names raise `ValueError`.
- **`stdlib/model.py:llm.openai`** — now provider-aware: accepts `provider=None` kwarg,
  routes through `_PROVIDERS[normalize_provider(provider)]`. Old direct OpenAI SDK call replaced.
- **`cli.py`** — `--model` args on `compile`, `summarize`, `plan` subparsers drop
  `choices=["openai","anthropic"]` and `default="openai"`; accept any configured provider name.
- **`repl.py` banner fix** — `_STDLIB_NAME_PREFIXES` heuristic (which split on first dot →
  `"neurolang"` and never matched) replaced with `_is_stdlib_neuro(name)` checking
  `parts[0]=="neurolang" and parts[1]=="stdlib"`. Banner now correctly shows stdlib neuro count.
- 1 new test (banner regression). 123/123 total, fully offline (~0.20s).

### Added (reason.* stdlib expansion)

- **`neurolang.stdlib.reason.brainstorm(topic, *, n=5, model=None) → str`** —
  divergent-ideation leaf neuro. Single LLM call; output is newline-delimited
  bullets covering `n` distinct, non-overlapping angles on the topic.
- **`neurolang.stdlib.reason.deep_research(question, *, depth="standard"|"deep", model=None) → str`** —
  multi-perspective synthesis leaf neuro. Scaffolded prompt drives sub-question
  identification → per-question summary → synthesis. `depth="deep"` switches
  output target from ~500 to ~1500 words. Closes with a Caveats line about
  parametric-only research limits. Strict `depth` validation raises on typos.
- Tests in new `tests/stdlib/test_reason.py` mock LLM at
  `neurolang.stdlib.model.llm.{openai,anthropic}` directly via `monkeypatch`,
  avoiding the kind-dispatch `_PROVIDERS` infrastructure used by
  `compile_source` / `propose_plan`.
- 10 new tests (4 brainstorm + 6 deep_research). 122/122 total.
- Composite-with-web-grounding `reason.deep_research_grounded` deferred to a
  Phase-2 bundle (will compose `web.search` / `web.scrape` / `reason.summarize`
  internally for fresh-source research).

### Added (REPL)

- **`neurolang repl` — interactive shell.**
  - `neurolang.repl.start_repl(report)` — entry point. Builds a namespace
    pre-loaded with core types, top-level fns, stdlib namespaces, and every
    dot-less neuro from the default registry. Prints a transparency banner
    listing what was loaded and from which discovery paths.
  - `STDLIB_NAMESPACES` tuple is the single source of truth shared by
    namespace assembly and stdlib-count rendering — adding a future stdlib
    namespace becomes a one-place edit.
  - **Meta-commands** (lines starting with `:`): `:help`, `:catalog`,
    `:plan "<NL>"` (binds `last_plan`), `:compile "<NL>"` (binds `flow` —
    the killer NL-coding move; the resulting Flow is immediately runnable
    via `flow.run(...)`), `:exit` / `:quit`. Failures are non-fatal — only
    `SystemExit` propagates.
  - **Async coroutine auto-await** — top-level expressions returning a
    coroutine are resolved via `asyncio.run` and the resolved value is
    displayed instead of `<coroutine object>`. `start_repl` captures and
    restores the prior `sys.displayhook` in `finally` so the wrapper
    doesn't bleed into Jupyter / parent processes.
  - **Tab completion + persistent history** via `readline` + `rlcompleter`
    on Unix; graceful no-op on Windows. History file at
    `~/.neurolang/repl_history`.
  - **CLI**: `neurolang repl [--show-discovery]`. `main()` stashes the
    `DiscoveryReport` on a module-level `_LAST_DISCOVERY_REPORT` so
    `_cmd_repl` can pass it into the banner without rewiring every
    subcommand handler.
  - 26 new tests (24 `test_repl.py` + 2 `test_cli.py`).
  - SystemExit handling in `start_repl` accommodates string codes
    (`sys.exit("bye")`) by printing to stderr and returning 1, per Python
    convention.

### Changed (Phase 1.6 — architectural cleanup, no behavior change)

- **Public function renames** to drop the package-attribute shadow that
  forced internal callers into `importlib.import_module(...)` workarounds:
  - `neurolang.compile` → `neurolang.compile_source`
  - `neurolang.decompile` → `neurolang.decompile_summary`
  - `neurolang.propose` → `neurolang.propose_plan`
  - `neurolang.discover` → `neurolang.discover_neuros`

  Modules unchanged (`compile.py`, `propose.py`, `discover.py`). CLI
  subcommand strings unchanged (`neurolang compile "..."`, `neurolang plan
  "..."`, etc.). Pre-alpha (`0.0.1`) — same-name shadow ceiling never gets
  lower than now, so the rename is done in this window.

- **`neurolang/_providers.py`** (new internal peer module) — extracted
  `_PROVIDERS`, `_render_catalog`, and the `_llm_call_*` helpers from
  `compile.py`. `compile.py` and `propose.py` now both import from a
  peer rather than reaching into each other's privates. `compile.py`
  retains a `from ._providers import _PROVIDERS, _render_catalog`
  re-export for backward access via the old path.

- **Provider callable signature** gains a `kind` kwarg —
  `(prompt, system, *, model, kind, temperature=0.0)`, where `kind` is
  one of `"compile" | "decompile" | "plan"` (exposed as
  `neurolang._providers.PROVIDER_KINDS`). Test fakes branch on `kind`
  instead of sniffing the system prompt for the substring `"planner"`.
  Routine prompt edits no longer risk silently breaking dispatch.

  Custom `llm_fn` callables now also receive `kind=`; existing test
  fakes accept `**kwargs` to ignore it.

### Added
- `ROADMAP.md`, `STATUS.md`, `CHANGELOG.md` — process docs for context preservation across sessions.
- **Phase 1.5 bundle — discover + strict validation + plan.**
  - `neurolang.discover()` — filesystem auto-discovery; eager scan at CLI
    startup of `~/.neurolang/neuros/` + project-marker-detected
    `<project>/neuros/` + explicit `extra_paths`. Idempotent. Errors per
    file collected into `DiscoveryReport`, not raised.
  - `neurolang.compile.validate_source()` — now returns `ValidationFindings`
    dataclass (with backward-compat `__getitem__`); `strict_refs=True`
    walks the `flow = <expr>` rhs and flags any reference not in the
    registry and not locally defined. `compile()` enforces strict mode by
    default and raises `CompileError` with hybrid suggestions.
  - `neurolang.propose(prompt)` → `ProposedPlan` — single LLM call;
    `{neuros, composition, missing}` JSON contract; cost + latency rolled
    up locally from each neuro's `Budget`. `propose:`-prefixed cache keys.
  - `neurolang.suggest.suggest_alternatives()` — hybrid Levenshtein +
    substring suggestions; pure stdlib.
  - **CLI**: `neurolang plan "<prompt>"` — JSON output; TTY-aware
    `--yes` / `--no-confirm` / `--dry-run` flags; `--show-discovery` for
    debugging. `main()` runs `discover()` at every entrypoint.
  - 39 new tests (7 suggest, 10 discover, 7 compile-strict, 8 propose, 7
    cli). 84/84 total, fully offline (~0.14s).
- **NL ↔ NeuroLang compiler.**
  - `neurolang.compile(prompt)` — natural-language → validated NeuroLang Python; returns a runnable `Flow`.
  - `neurolang.decompile(flow_or_source)` — Python → natural-language summary.
  - File-based cache at `~/.neurolang/cache/` keyed by `hash(prompt + model + library_version)`.
  - AST validation: parses, imports neurolang, declares `flow`.
  - Code-fence stripping for sloppy LLM output.
  - Pluggable LLM provider: `openai`, `anthropic`, or custom `llm_fn=`.
- **CLI** (`neurolang` console script):
  - `neurolang compile "<prompt>"` (stdout, file, or `--execute`)
  - `neurolang summarize <file.py>`
  - `neurolang catalog` (markdown of registered neuros)
  - `neurolang cache list/clear`
- 15 new tests for the compiler — all LLM mocked, fully offline.

- **Phase 1 core library.**
  - `Neuro` (typed unit + `@neuro` decorator with `effect` / `budget` / `kind` / `reads` / `writes`).
  - `Flow` (composition tree); operators `|` (sequential), `&` (parallel-AND), `+` (parallel-OR).
  - `Plan` (immutable, hashable, replayable, serializable).
  - `Memory` (Protocol + `LocalMemory`; `Memory.discrete()`).
  - `Effect` (pure / llm / tool / human / time / voice / memory).
  - `Budget` (latency / cost / token bounds; sums through composition).
  - `Recovery`: `with_retry`, `with_fallback`, `with_escalation`.
  - `Registry` (in-process catalog; search, by_kind, by_effect).
  - `runtime/`: `NeuroNet` Protocol + `LocalNeuroNet` (minimal in-process runtime).
  - `render/`: Mermaid output for any flow.
  - `stdlib/` (minimal): `web.search`, `web.scrape`, `reason.summarize`, `reason.classify`, `memory.store`, `memory.recall`, `model.llm.openai`, `model.llm.anthropic`, `voice.transcribe`, `voice.synthesize`.
- 30 tests covering categorical laws (associativity, identity), plan determinism, effect propagation, budget rollup, memory neuros, registry search/catalog, recovery primitives, mermaid rendering.

- **Doc set:**
  - `VISION.md` — original two-layer NL ↔ formal vision.
  - `RESEARCH.md` — categorical foundations, deep theoretical backing.
  - `LANDSCAPE.md` — competitive analysis + honest gaps.
  - `COMPARISON.md` — 3-way structural comparison (NeuroLang vs current vs industry).
  - `OPEN_DECISIONS.md` — implementation decisions to lock.
  - `ARCHITECTURE.md` — three-layer architecture (NL surface / library / runtime).
  - `FRAMEWORK.md` — the trinity (current canonical design).
  - `ROADMAP.md`, `STATUS.md` — process docs.

### Notes
- Repo is at `/home/ubuntu/neurolang/`. Local-only — GitHub remote not yet created.
- `pip install -e .` works; `pip install -e ".[all]"` adds openai+anthropic+requests+bs4.
- 84/84 tests passing (~0.14s offline).

---

## [0.0.1] — 2026-04-26 (initial scaffold, pre-Phase-1)

### Added
- Repo skeleton: `pyproject.toml` (hatchling, MIT, py>=3.10).
- `LICENSE` (MIT).
- `.gitignore` (Python).
- Empty `neurolang/__init__.py` with `__version__ = "0.0.1"`.
- Smoke test verifying the version export.
