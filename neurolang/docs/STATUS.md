# NeuroLang — Current Status

> **For any new session:** read this file first. It tells you exactly where we are and what's next. Then work on "Next up" without re-deriving context. **Update this file at the end of every session.**

---

## Last updated: 2026-04-28

## Current phase: 1.9 — Email stdlib (IMAP/SMTP shipped)

## Just shipped (most recent first)
1. **`email` stdlib — IMAP/SMTP backend (Phase 1.9).**
   - `neurolang.stdlib.email.{send, read, search, mark}` — four neuros built on Python stdlib `imaplib` + `smtplib` + `email` (zero new deps). Filename `email_neuros.py` mirrors `memory_neuros.py` precedent to avoid shadowing Python's stdlib `email` package; re-exported in `stdlib/__init__.py` so the public catalog name stays `neurolang.stdlib.email.<fn>`.
   - **`send(to, subject, body, *, cc, bcc, html)`** — real `EmailMessage` MIME, BCC via SMTP envelope only, returns confirmation dict.
   - **`read(folder, *, n, unread_only)`** — `BytesParser(policy=policy.default)` auto-decodes RFC2047 subjects; multipart/alternative prefers text/plain; HTML-only falls back to a stdlib `html.parser`-based stripper (drops script/style content, returns visible text).
   - **`search(query, *, folder, n)`** — passes IMAP SEARCH syntax verbatim; docstring shows three concrete examples for planner consumption.
   - **`mark(uid, flag, *, folder)`** — `_FLAG_MAP` dict maps `seen/unseen/flagged/unflagged/deleted` to correct `+FLAGS`/`-FLAGS` STORE ops.
   - **Domain auto-detect** — `_DOMAIN_DEFAULTS` covers gmail/outlook/hotmail/yahoo. Unknown domain w/o explicit hosts raises with helpful message.
   - **`EmailError(operation, cause)`** wraps imaplib/smtplib/OSError; per-call `try/finally` closes connections cleanly.
   - **Gmail-API backend reserved as v1.1** via `EMAIL_BACKEND=gmail` env (currently `NotImplementedError`).
   - 25 new tests in `tests/stdlib/test_email.py` — patches `imaplib.IMAP4_SSL` + `smtplib.SMTP_SSL` w/ `MagicMock`, canned RFC822 via real `EmailMessage`. 172/172 total, ~0.67s offline.
   - Live demo `examples/email_demo.py` (skip-on-missing-creds pattern).
   - REPL `STDLIB_NAMESPACES` extended with `("email", email_neuros)`.
   - Spec at `docs/superpowers/specs/2026-04-28-email-stdlib-design.md`.
2. **`max_tokens` differentiation per call kind (commit a41826c).**
   - `_KIND_MAX_TOKENS` dict in `_providers.py`: compile/plan → 2048, decompile → 512, reason → 2048, reason.deep → 4096.
   - `_llm_call_via_openai_sdk` and `_llm_call_anthropic` look up `_KIND_MAX_TOKENS.get(kind, 2048)`.
   - `reason.py:_call_llm` gains `kind: str = "reason"` kwarg. `deep_research(depth="deep")` routes `kind="reason.deep"` → 4096 tokens, eliminating mid-sentence truncation.
   - `PROVIDER_KINDS` extended with `"reason"` and `"reason.deep"`.
   - 10 new tests in `tests/test_providers.py`. 147/147 passing.
2. **`agent.delegate` — recursive flow composition (Phase 1.8).**
   - `neurolang.stdlib.agent.delegate(task, *, catalog=None, depth=1, model=None) → Neuro` — factory pattern. Each call returns a fresh `@neuro(register=False)` closure with `task` baked in; the inner neuro is `async` so `await flow.run_async(input_value)` shares the parent's event loop (sync `flow.run()` would deadlock).
   - **Catalog scoping** via `fnmatch` glob list — `catalog=["neurolang.stdlib.reason.*"]` builds a fresh `Registry` containing only matching neuros, passed to both `propose_plan(registry=...)` and `compile_source(registry=...)`.
   - **Memory inheritance** — agent captures `current_memory()` at call time and passes through `flow.run_async(input_value, memory=parent_memory)`; inner Plan.run_async would otherwise default `memory=None` and clobber the parent's ContextVar.
   - **Depth budget** via `_delegation_depth: ContextVar[Optional[int]]`. `delegate(..., depth=0)` raises `DelegationBudgetExhausted` on call. Default `depth=1` — outer flow can delegate, inner sub-flow cannot.
   - **Soft fail** when planner returns `missing != []` — agent returns `f"[delegate: cannot satisfy task — missing: {intents}]"` rather than raising. Compile errors wrap as `DelegationFailed(task, cause)` for clear stack traces.
   - **Bonus fix in `propose.py`** — `_resolve_neuro_name(name, reg)` resolves short-name LLM outputs ('reason.summarize') to unique full registered names ('neurolang.stdlib.reason.summarize') via suffix matching. Ambiguous suffixes still fail through. Found while exercising the live demo; fixes a long-standing pre-existing planner bug.
   - 9 tests in `tests/stdlib/test_agent.py` (happy path, compose-with-pipe, no-pollution, catalog glob, soft-fail, depth=0, depth<0, memory inheritance, compile-failure-wrap) + 2 in `test_propose.py` (short-name resolution, ambiguity guard).
   - Live demo at `examples/agent_delegate.py` — `flow = passthrough | agent.delegate("given input text, produce a two-sentence summary", catalog=["neurolang.stdlib.reason.*"])` produces a real LLM-driven summary at runtime.
   - 137/137 tests passing offline (~0.19s). Live LLM demo verified.
2. **Cache key includes system prompt + catalog fingerprint.**
   - `cache.make_key()` gains `system_fingerprint=""` kwarg; `compile_source` computes `sha256(_SYSTEM_PROMPT + _FEW_SHOT + catalog_md)[:8]` upfront and threads it into the key. Changing the compile prompt or registering a new neuro now auto-invalidates stale cache entries — no more manual `neurolang cache clear` after prompt edits.
   - 4 new tests (different fingerprint → different key, backward-compat, end-to-end prompt-change → cache miss). 126/126 pre-agent.delegate.
3. **Multi-provider LLM registry (Phase 1.7).**
   - `neurolang/_providers.py` rewritten: `PROVIDER_CONFIGS` dict with 5 providers (opencode-zen, openrouter, openai, anthropic, ollama). Default = `opencode-zen` / `opencode/minimax-m2.5-free`. Mirrors neurocomputer pattern.
   - Auth fallback: `opencode-zen` reads `~/.local/share/opencode/auth.json` if `OPENCODE_API_KEY` env unset. `DEFAULT_LLM_PROVIDER` env var overrides.
   - All caller defaults flipped from `model="openai"` to `model=None` (resolves via `normalize_provider` → `DEFAULT_PROVIDER`). Affected: `propose_plan`, `compile_source`, `decompile_summary`, all 4 `reason.*` fns.
   - `stdlib/model.py:llm.openai` upgraded to route through `_PROVIDERS` (provider-aware; `provider=None` kwarg defaults to DEFAULT_PROVIDER).
   - `stdlib/reason.py`: private `_call_llm(prompt, model)` helper routes directly through `_PROVIDERS`; removed per-fn if/elif dispatch chains.
   - `cli.py`: `--model` args drop `choices=["openai","anthropic"]` and `default="openai"`; accept any provider name (default=None).
   - `repl.py` banner fix: `_STDLIB_NAME_PREFIXES` heuristic replaced with `_is_stdlib_neuro(name)` checking `parts[0]=="neurolang" and parts[1]=="stdlib"`. Banner now correctly counts stdlib neuros (was showing "0").
   - 1 new test (banner regression). 123/123 total, fully offline (~0.20s).
2. **`reason.*` stdlib expansion — brainstorm + deep_research.**
   - `reason.brainstorm(topic, *, n=5, model=None) → str` — divergent ideation.
   - `reason.deep_research(question, *, depth="standard"|"deep", model=None) → str` — multi-perspective synthesis.
   - 10 tests. Routes through `_call_llm` → `_PROVIDERS`.
2. **`neurolang repl` — interactive shell.**
   - `neurolang/repl.py` — `NeuroLangConsole` extending `code.InteractiveConsole`. Pre-loaded namespace: core types + top-level fns + stdlib namespaces (`web`, `reason`, `model`, `voice`, `memory_neuros`) + every dot-less neuro from `default_registry`. Transparency banner shows loaded counts and discovery paths. `STDLIB_NAMESPACES` tuple is the single source of truth shared by namespace assembly and stdlib-count rendering.
   - Meta-commands: `:help`, `:catalog`, `:plan "<NL>"` (binds `last_plan`), `:compile "<NL>"` (binds `flow` — the killer NL-coding move; resulting Flow is immediately runnable), `:exit` / `:quit`. Failures non-fatal; only `SystemExit` propagates.
   - Async-aware `sys.displayhook` auto-resolves coroutines via `asyncio.run`; `start_repl` captures + restores the prior hook in `finally` so the wrapper doesn't bleed into Jupyter / parent processes.
   - Tab completion + persistent history at `~/.neurolang/repl_history` via `readline` + `rlcompleter` on Unix; graceful no-op on Windows. Best-effort error handling.
   - CLI: `neurolang repl [--show-discovery]`. `main()` stashes the `DiscoveryReport` on a module-level `_LAST_DISCOVERY_REPORT` so `_cmd_repl` can pass it into the banner without rewiring every subcommand handler.
   - 26 new tests (24 in `test_repl.py`, 2 in `test_cli.py`). All 112 tests offline, ~0.16s.
3. **Phase 1.6 architectural cleanup** — three follow-ups raised by the Phase 1.5 final review, all closed:
   - Public function renames (`compile`→`compile_source`, `decompile`→`decompile_summary`, `propose`→`propose_plan`, `discover`→`discover_neuros`) drop the package-attribute shadow; CLI's `importlib.import_module(...)` workarounds deleted.
   - `neurolang/_providers.py` peer module — `_PROVIDERS`, `_render_catalog`, `_llm_call_*` extracted from `compile.py`; `propose.py` and `cli.py` import from the peer instead of reaching into each other's privates.
   - Provider callables gain a `kind="compile"|"decompile"|"plan"` kwarg; test fakes dispatch on `kind` instead of sniffing the system prompt for `"planner"`.
   - 84/84 still green — pure refactor, no behavior change.
4. **Phase 1.5 bundle — discover + strict validation + plan command.**
   - `neurolang/discover.py` — eager FS scan at CLI startup; loads
     `~/.neurolang/neuros/` + project-marker-detected `<project>/neuros/`
     + explicit `extra_paths`. Idempotent. Bad files don't abort.
   - `neurolang/compile.py` — `validate_source()` returns `ValidationFindings`
     dataclass; `strict_refs=True` walks `flow = <expr>` rhs and flags any
     reference not in the registry and not locally defined. `compile_source()`
     hardcodes strict on; raises `CompileError` with hybrid suggestions on
     unknown refs.
   - `neurolang/propose.py` — `propose_plan(prompt) → ProposedPlan` via one LLM
     call. Cost rolled up locally from each neuro's `Budget`. Cache shares
     `CompilerCache` with a `propose:` prefix. JSON-serializable dataclass.
   - `neurolang/suggest.py` — hybrid Levenshtein + substring suggestion
     utility used by both strict validation and propose's missing-capability
     handling.
   - `neurolang/cli.py` — new `plan` subcommand with `--dry-run` / `--yes` /
     `--show-discovery` / `-o` / `--execute` / `--no-cache`. JSON output (pretty-printed).
     Auto-runs `discover_neuros()` at every CLI invocation. TTY-aware confirmation.
   - 39 new tests (suggest 7, discover 10, compile-strict 7, propose 8, cli 7).
   All 84 tests offline, ~0.14s.
5. **NL ↔ Python compiler** with file cache + CLI (compile / summarize / catalog / cache). Pluggable LLM (openai / anthropic / custom `llm_fn`). 15 tests, all mocked, offline. Three commits on `main`.
6. **Phase 1 core library** — Neuro / Flow / Plan / Memory / Effect / Budget / Recovery / Registry / NeuroNet Protocol + LocalNeuroNet / Mermaid rendering / minimal stdlib (web, reason, memory, model, voice). 30 tests passing.

## Working on now
*(empty — between tasks)*

## Next up

### Then (in order)
1. ~~**Email stdlib**~~ — DONE 2026-04-28 (Phase 1.9, see "Just shipped" #1).
2. **Calendar stdlib** — `calendar.read` / `calendar.create` via Google Calendar API.
3. **Voice stdlib** — `voice.call` via LiveKit/Twilio adapter.
4. **First end-to-end live demo** — record `neurolang repl` + `:compile "research microplastics impact"` against a real LLM with a custom user neuro loaded from `~/.neurolang/neuros/`.
5. ~~**GitHub remote creation**~~ — DONE 2026-04-26.

### Email stdlib v1.1 candidates (not blocking)
- `email.reply(uid, body)` w/ auto In-Reply-To / References threading
- Attachments (`send(..., attachments=[...])`, `read(..., include_attachments=True)`)
- Gmail API backend (slot pre-wired via `EMAIL_BACKEND=gmail` env)
- IDLE / push notifications

### Architectural follow-ups (raised by the Phase 1.5 final review)

All three closed in Phase 1.6 (see "Just shipped" #2):

1. ~~**Package-attribute shadowing**~~ — DONE. Function exports renamed (option a); `importlib.import_module(...)` workarounds deleted.
2. ~~**Promote `_PROVIDERS` + `_render_catalog` to a peer module**~~ — DONE. `neurolang/_providers.py` extracted; `propose.py` + `cli.py` import from the peer.
3. ~~**Replace the `"planner" in system` dispatch**~~ — DONE. Provider callables now take an explicit `kind="compile"|"decompile"|"plan"` kwarg; `PROVIDER_KINDS` exposed from `_providers`.

### Architectural follow-ups (raised by the REPL final review — address opportunistically)

Not blockers; flag them when the relevant area is being touched.

0. **Promote `_make_smart_provider` to `tests/conftest.py`.** Now duplicated across `tests/test_cli.py`, `tests/test_repl.py`, and `tests/stdlib/test_agent.py` (4+ sites with `_make_smart_provider` or inline equivalent). Centralize as the agent-test version is the most fleshed-out (handles plan, compile, missing).
1. **Promote smart-provider fake to `tests/conftest.py`.** The `def smart_provider(prompt, system, *, model, kind): if kind == "plan": ... elif kind == "compile": ...` pattern is duplicated across `tests/test_cli.py` and `tests/test_repl.py` (3 sites). A `make_smart_provider(plan=..., source=...)` factory in `tests/conftest.py` would dedupe and serve future kind-aware fakes.
2. **Refactor `_LAST_DISCOVERY_REPORT` global → `args._discovery_report`.** Single consumer today (`_cmd_repl`). The moment a 2nd subcommand needs the report, set it on the parsed `args` namespace inside `main()` immediately after `discover_neuros()` instead of carrying a module-level global.
3. **Add a lifecycle docstring to `start_repl`.** Note that user code mutating `sys.displayhook` during the session is responsible for its own cleanup; `start_repl` only restores its own snapshot.
4. **`_handle_meta` if/elif → dict dispatch** when meta-command count grows past 5 (e.g., when `:save`, `:load`, `:run` land).

## Open questions for the user
- *(none active)*

## Environmental notes
- **GitHub remote live** — `git@github.com:neurocomputer-in/neurolang.git` (private). `main` is pushed and tracking. Push via SSH (HTTPS not authenticated on this host).
- **VSCode plugin deferred.** Per your direction, skipping for now.
- **Tests run offline** via `python -m pytest tests/ -q`. All 172 currently passing in ~0.67s.
- **Demo runs** — `python examples/research_flow.py` (skips actual LLM/HTTP calls if optional deps missing).
- `pip install -e .` works; `pip install -e ".[all]"` adds openai+anthropic+requests+bs4.

## Quick reference

```
Repo:     /home/ubuntu/neurolang/  (origin: github.com:neurocomputer-in/neurolang.git)
Default:  opencode-zen / opencode/minimax-m2.5-free (auth via ~/.local/share/opencode/auth.json)
Branch:   main
Commits:  ~52 (Phase 1.9: email stdlib + spec + prior ~50)
Tests:    172/172 passing (~0.67s offline)
Stdlib:   web, reason (summarize/classify/brainstorm/deep_research), memory_neuros, model, voice, agent.delegate, email (send/read/search/mark) (17 neuros + 1 factory)
Providers: opencode-zen (default), openrouter, openai, anthropic, ollama
CLI:      neurolang {compile, summarize, catalog, cache, plan, repl}
API:      compile_source, decompile_summary, propose_plan, discover_neuros (renamed in Phase 1.6)
```
