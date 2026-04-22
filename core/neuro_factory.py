import json, types, pathlib, sys, textwrap, asyncio, fnmatch, io, contextlib, functools
from dataclasses import dataclass, field
from typing import Optional

from core.base_neuro import BaseNeuro
from core.base_brain import BaseBrain
from core import model_library
from core.flows.flow_neuro import FlowNeuro as _FlowNeuro
from core.flows.dag_flow import DagFlow as _DagFlow
from core.flows.sequential_flow import SequentialFlow as _SequentialFlow
from core.flows.parallel_flow import ParallelFlow as _ParallelFlow
from core.instance_pool import InstancePool
from core.kinds import parse_kind

_BUILTIN_FLOWS = {
    "dag_flow":        (_DagFlow,        "Interprets a JSON DAG at runtime."),
    "sequential_flow": (_SequentialFlow, "Runs declared children in order."),
    "parallel_flow":   (_ParallelFlow,   "Fans out declared children concurrently."),
}

# Kind-based synthesis registry: keyed BOTH by legacy alias and canonical
# dotted form, so conf.json can use either. See core/kinds.py for the
# taxonomy spec. Extended beyond skill.flow.* to include prompt.* and
# future namespaces.
from core.prompt_neuro import PromptBlock as _PromptBlock
from core.prompt_neuro import PromptComposer as _PromptComposer
from core.context_neuro import ContextSlice as _ContextSlice
from core.context_neuro import ContextAssembler as _ContextAssembler
from core.instruction_neuro import InstructionRule as _InstructionRule
from core.instruction_neuro import InstructionTone as _InstructionTone
from core.instruction_neuro import InstructionPolicy as _InstructionPolicy
from core.model_neuro import ModelLLM as _ModelLLM
from core.model_neuro import ModelEmbedding as _ModelEmbedding
from core.model_neuro import ModelReranker as _ModelReranker
from core.inference_neuro import Inference as _Inference
from core.agent_neuro import AgentNeuro as _AgentNeuro
from core.tool_loop_neuro import ToolLoop as _ToolLoop

_FLOW_KIND_REGISTRY = {
    # skill.flow.* — composition
    "sequential_flow":         _SequentialFlow,
    "parallel_flow":           _ParallelFlow,
    "dag_flow":                _DagFlow,
    "skill.flow.sequential":   _SequentialFlow,
    "skill.flow.parallel":     _ParallelFlow,
    "skill.flow.dag":          _DagFlow,

    # prompt.* — prompt assembly
    "prompt.block":            _PromptBlock,
    "prompt.composer":         _PromptComposer,

    # context.* — window assembly
    "context.slice":           _ContextSlice,
    "context.assembler":       _ContextAssembler,
    "context.profile":         _ContextAssembler,    # profile = named assembler

    # instruction.* — policies / tone
    "instruction.rule":        _InstructionRule,
    "instruction.tone":        _InstructionTone,
    "instruction.policy":      _InstructionPolicy,

    # model.* — frontier model wrappers
    "model.llm":               _ModelLLM,
    "model.embedding":         _ModelEmbedding,
    "model.reranker":          _ModelReranker,
    "model.inference":         _Inference,

    # agent — session runners / named configuration bundles
    "agent":                   _AgentNeuro,

    # skill.tool_loop — multi-round tool-calling loop (LLM invokes neuros as tools)
    "skill.tool_loop":         _ToolLoop,
}


# ---------- registry entry types -------------------------------------

@dataclass
class ClassEntry:
    """Entry for class-form neuros (BaseNeuro subclass). Instances are
    produced by InstancePool per scope_key."""
    name: str
    cls: type
    conf: dict
    is_class: bool = True
    conf_path: Optional[pathlib.Path] = None

    @property
    def scope(self) -> str:
        return getattr(self.cls, "scope", None) or self.conf.get("scope", "session")

    @property
    def desc(self) -> str:
        return self.conf.get("description", "")

    @property
    def folder(self):
        return self.conf_path.parent if self.conf_path else None


@dataclass
class _LegacyFnEntry:
    """Entry for legacy fn-form neuros. Wraps a BaseNeuro instance
    constructed with the legacy positional ctor (preserves LLM injection,
    stdout capture, thinking extraction)."""
    name: str
    neuro: BaseNeuro
    conf: dict
    is_class: bool = False
    conf_path: Optional[pathlib.Path] = None

    @property
    def scope(self) -> str:
        return self.conf.get("scope", "call")

    @property
    def desc(self) -> str:
        return self.conf.get("description", self.neuro.desc)

    @property
    def folder(self):
        return self.conf_path.parent if self.conf_path else None


# ---------- factory ---------------------------------------------------

class NeuroFactory:
    """
    * loads every neuros/<n>/conf.json
    * detects fn-form (module-level `async def run`) vs class-form
      (subclass of BaseNeuro) and stores a matching entry
    * hot-reloads on conf.json mtime change; drops pooled class instances
    * injects a ready-made BaseBrain into the fn-neuro state as state["__llm"]
    """
    def __init__(self, dir="neuros"):
        self.dir = pathlib.Path(dir)
        self.reg: dict = {}
        self.patterns: dict = {}
        self.pool = InstancePool(self)
        self._load_all()
        self._register_builtins()
        try:
            asyncio.get_event_loop().create_task(self._watch())
        except RuntimeError:
            pass

    # ---------- loading ----------------------------------------------

    def _safe_exec(self, src: str, mod_name: str):
        mod = types.ModuleType(mod_name)
        exec(compile(textwrap.dedent(src), mod_name, "exec"), mod.__dict__, mod.__dict__)
        sys.modules[mod_name] = mod
        return mod

    def _load_all(self):
        for p in self.dir.rglob("conf.json"):
            self._load(p)

    async def _watch(self):
        stamp = {p: p.stat().st_mtime for p in self.dir.rglob("conf.json")}
        while True:
            await asyncio.sleep(1)
            for p in self.dir.rglob("conf.json"):
                try:
                    m = p.stat().st_mtime
                    if m != stamp.get(p):
                        print(f"[factory] reload {p}")
                        self._load(p)
                        stamp[p] = m
                except Exception:
                    pass

    def _register_builtins(self):
        for name, (cls, desc) in _BUILTIN_FLOWS.items():
            if name in self.reg:
                continue
            conf = {
                "name": name, "description": desc,
                "scope": "singleton", "uses": [], "children": [],
                "inputs": [], "outputs": [],
            }
            self.reg[name] = ClassEntry(name=name, cls=cls, conf=conf)

    # ---------- class detection -------------------------------------

    def _pick_main_class(self, module, conf_name):
        """Identify the neuro class within `module`, returning None for
        pure fn-form modules."""
        if module is None:
            return None

        main = getattr(module, "__main_neuro__", None)
        if isinstance(main, str) and main in module.__dict__:
            cls = module.__dict__[main]
            if isinstance(cls, type) and issubclass(cls, BaseNeuro):
                return cls

        camel = "".join(p.title() for p in conf_name.split("_"))
        exact = module.__dict__.get(camel)
        if isinstance(exact, type) and issubclass(exact, BaseNeuro):
            if exact.__module__ == module.__name__:
                return exact

        candidates = [
            v for v in module.__dict__.values()
            if isinstance(v, type)
               and issubclass(v, BaseNeuro)
               and v is not BaseNeuro
               and v is not _FlowNeuro
               and v.__module__ == module.__name__
               and not v.__name__.startswith("_")
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) == 0:
            return None
        raise RuntimeError(
            f"ambiguous main class for neuro {conf_name!r}: "
            f"{[c.__name__ for c in candidates]}. "
            "Add `__main_neuro__ = 'YourClass'` to code.py."
        )

    @staticmethod
    def _synthesize_flow_class(conf):
        base = _FLOW_KIND_REGISTRY[conf["kind"]]
        attrs = {
            "uses":     conf.get("uses", []),
            "children": conf.get("children", []),
            "scope":    conf.get("scope", "session"),
        }
        # Kind-specific pure-conf passthroughs.
        if "dag" in conf:
            attrs["dag"] = conf["dag"]                    # skill.flow.dag
        if "separator" in conf:
            attrs["separator"] = conf["separator"]        # prompt.composer
        if "merge_key" in conf:
            attrs["merge_key"] = conf["merge_key"]        # skill.flow.parallel
        if "template" in conf:
            attrs["template"] = conf["template"]          # prompt.block
        if "slices_spec" in conf:
            attrs["slices_spec"] = conf["slices_spec"]    # context.assembler
        if "token_budget" in conf:
            attrs["token_budget"] = conf["token_budget"]  # context.assembler
        if "priority" in conf:
            attrs["priority"] = conf["priority"]          # instruction.rule
        if "filter_category" in conf:
            attrs["filter_category"] = conf["filter_category"]  # instruction.policy
        if "min_priority" in conf:
            attrs["min_priority"] = conf["min_priority"]  # instruction.policy
        if "voice" in conf:
            attrs["voice"] = conf["voice"]                # instruction.tone
        # `category` is dual-purpose: IDE library tree AND instruction.rule's
        # own category attr. Pass it through for instruction.* kinds so
        # class attribute reflects conf value (IDE still reads it from conf).
        kind_str = conf.get("kind", "")
        if "category" in conf and kind_str.startswith("instruction"):
            attrs["category"] = conf["category"]
        # model.* — class-attribute passthrough
        if kind_str.startswith("model"):
            for k in ("provider", "default_model", "temperature",
                      "default_provider", "default_fallback",
                      "modality_providers"):
                if k in conf:
                    attrs[k] = conf[k]
        # agent — class-attribute passthrough
        if kind_str == "agent" or kind_str.startswith("agent."):
            for k in ("profile", "default_workflow", "memory_scope",
                      "policy_override"):
                if k in conf:
                    attrs[k] = conf[k]
        # skill.tool_loop — class-attribute passthrough
        if kind_str == "skill.tool_loop":
            if "max_rounds" in conf:
                attrs["max_rounds"] = conf["max_rounds"]
        return type(f"_ConfFlow_{conf['name']}", (base,), attrs)

    # ---------- per-file load ---------------------------------------

    def _load(self, path: pathlib.Path):
        folder = path.parent
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[factory] skipping invalid JSON in {path}")
            return
        except UnicodeDecodeError:
            print(f"[factory] skipping file with encoding issues in {path}")
            return

        # Optional sidecar — layout.json (IDE rendering hint).
        layout_path = folder / "layout.json"
        if layout_path.exists():
            try:
                spec["layout"] = json.loads(layout_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        code_path = folder / "code.py"
        module = None
        if code_path.exists():
            try:
                module = self._safe_exec(code_path.read_text(encoding="utf-8"),
                                         f"neuro_{spec['name']}")
            except Exception as e:
                print(f"[factory] failed to exec {code_path}: {e}")
                return

        # Class path
        try:
            cls = self._pick_main_class(module, spec["name"])
        except RuntimeError as e:
            print(f"[factory] {e}")
            return

        if cls is not None:
            self.reg[spec["name"]] = ClassEntry(
                name=spec["name"], cls=cls, conf=spec, conf_path=path,
            )
            self._schedule_invalidate(spec["name"])
            return

        # Pure-conf flow synthesis (no code.py, but declared kind)
        if module is None and spec.get("kind") in _FLOW_KIND_REGISTRY:
            synth_cls = self._synthesize_flow_class(spec)
            self.reg[spec["name"]] = ClassEntry(
                name=spec["name"], cls=synth_cls, conf=spec, conf_path=path,
            )
            self._schedule_invalidate(spec["name"])
            return

        # Legacy fn path — preserve current _runner behavior exactly.
        if module is not None and hasattr(module, "run"):
            self.reg[spec["name"]] = _LegacyFnEntry(
                name=spec["name"],
                neuro=self._build_legacy_fn_neuro(spec, module, folder),
                conf=spec,
                conf_path=path,
            )
            return

        print(f"[factory] WARN: {spec.get('name','?')} has no class and no module-level run; skipped")

    def _schedule_invalidate(self, name):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.pool.invalidate(name))
        except RuntimeError:
            pass

    def _build_legacy_fn_neuro(self, spec, module, folder):
        """Replicates the legacy _runner exactly: LLM injection, stdout
        capture, thinking extraction. Preserves 100% fn-neuro behavior."""
        prompt_path = folder / "prompt.txt"
        prompt_txt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None

        role = spec.get("role")
        model = spec.get("model", "gpt-4o-mini")
        temp = spec.get("temperature", 0.7)

        async def _runner(state, **kw):
            state_sel = state.get("__llm_selection_type")
            state_prov = state.get("__llm_provider")
            state_model = state.get("__llm_model")
            if state_sel == "raw" and state_prov and state_model:
                provider = state_prov
                selected_model = state_model
                effective_model = state_model
            else:
                resolved_role = model_library.resolve_role(role) if role else None
                if resolved_role:
                    provider = resolved_role["provider"]
                    selected_model = resolved_role["model"]
                    effective_model = selected_model
                else:
                    provider = state_prov
                    selected_model = state_model or model
                    effective_model = model
            if effective_model and str(effective_model).lower() not in ("none", "null", ""):
                try:
                    state["__llm"] = BaseBrain(selected_model, temp, provider=provider)
                except (ValueError, KeyError, EnvironmentError):
                    state["__llm"] = None
            state["__prompt"] = prompt_txt

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = await module.run(state, **kw)

            logs = buf.getvalue()
            if not isinstance(res, dict):
                res = {}
            if logs:
                res["__logs"] = logs

            llm = state.get("__llm")
            if llm and hasattr(llm, "last_thinking") and llm.last_thinking:
                res["__thinking"] = llm.last_thinking

            return res

        return BaseNeuro(
            spec["name"], _runner,
            spec.get("inputs", []), spec.get("outputs", []),
            spec.get("description", ""),
        )

    # ---------- public helpers --------------------------------------

    async def run(self, name: str, state: dict, **kw):
        stream_cb = kw.pop("stream_callback", None)
        if stream_cb:
            state["__stream_cb"] = stream_cb

        if name not in self.reg:
            raise KeyError(
                f"Neuro {name!r} not found. "
                f"Available: {', '.join(sorted(self.reg))}"
            )

        state.setdefault("__factory", self)
        entry = self.reg[name]

        if getattr(entry, "is_class", False):
            state["__caller_neuro"] = name
            instance = await self.pool.get(entry, state)
            out = await instance.run(state, **kw)
        else:
            out = await entry.neuro.run(state, **kw)

        if not isinstance(out, dict):
            out = {}
        return out

    # ---------- profile filtering -----------------------------------

    def set_pattern(self, cid: str, patterns):
        if isinstance(patterns, str):
            patterns = [patterns]
        self.patterns[cid] = patterns or ["*"]

    def _filter(self, cid, names):
        if cid is None or cid not in self.patterns:
            return names
        pats = self.patterns[cid]
        return [n for n in names if any(fnmatch.fnmatch(n, p) for p in pats)]

    def catalogue(self, cid=None, group=None):
        names = list(self.reg.keys())
        names = self._filter(cid, names)
        if group == "dev":
            names = [n for n in names if n.startswith("dev_")]
        return names

    # ---------- describe --------------------------------------------

    def describe(self, cid=None, group=None):
        out = []
        for n in self.catalogue(cid, group):
            entry = self.reg[n]
            conf = entry.conf
            is_class = getattr(entry, "is_class", False)

            # Prefer explicit kind from conf; fall back to derived leaf/flow.
            raw_kind = conf.get("kind")
            if raw_kind:
                kind_obj = parse_kind(raw_kind)
                kind_full = kind_obj.full
                kind_namespace = kind_obj.namespace
            elif is_class and issubclass(entry.cls, _FlowNeuro):
                kind_full = "skill.flow"
                kind_namespace = "skill"
            else:
                kind_full = "skill.leaf"
                kind_namespace = "skill"

            out.append({
                "name":           n,
                "desc":           entry.desc,
                "description":    entry.desc,
                "category":       conf.get("category"),
                "icon":           conf.get("icon"),
                "color":          conf.get("color"),
                "summary_md":     conf.get("summary_md"),
                "long_md":        conf.get("long_md"),
                "layout":         conf.get("layout"),
                "kind":           kind_full,
                "kind_namespace": kind_namespace,
                "scope":          entry.scope,
                "uses":           conf.get("uses", []),
                "children":       conf.get("children", []),
                "inputs":         _normalize_ports(conf.get("inputs", [])),
                "outputs":        _normalize_ports(conf.get("outputs", [])),
            })
        return out


def _normalize_ports(ports):
    out = []
    for p in ports or []:
        if isinstance(p, str):
            out.append({"name": p, "type": "any",
                        "description": "", "optional": False})
        elif isinstance(p, dict):
            entry = {
                "name":        p.get("name", ""),
                "type":        p.get("type", "any"),
                "description": p.get("description", ""),
                "optional":    bool(p.get("optional", False)),
            }
            if "default" in p:
                entry["default"] = p["default"]
            if "example" in p:
                entry["example"] = p["example"]
            out.append(entry)
    return out
