import pathlib
import textwrap
import pytest
from core.prompt_neuro import PromptBlock, PromptComposer
from core.neuro_factory import NeuroFactory


async def test_prompt_block_renders_template():
    b = PromptBlock()
    b.template = "Hello, {{name}}! Your task: {{task}}."
    out = await b.run({}, name="Neuro", task="think")
    assert out == {"text": "Hello, Neuro! Your task: think."}


async def test_prompt_block_no_template_returns_empty():
    b = PromptBlock()
    assert await b.run({}) == {"text": ""}


async def test_prompt_composer_joins_children():
    class Identity(PromptBlock):
        template = "You are Neuro."
    class Tone(PromptBlock):
        template = "Be concise."

    c = PromptComposer()
    c.children = ["identity", "tone"]
    c.separator = "\n\n"
    c.identity = Identity()
    c.tone = Tone()

    out = await c.run({})
    assert out == {"text": "You are Neuro.\n\nBe concise."}


async def test_prompt_composer_skips_empty_children():
    class Empty(PromptBlock):
        template = ""
    class Full(PromptBlock):
        template = "visible"

    c = PromptComposer()
    c.children = ["empty", "full"]
    c.empty = Empty()
    c.full = Full()

    out = await c.run({})
    assert out == {"text": "visible"}


async def test_factory_synthesizes_prompt_composer_from_conf(tmp_path):
    """Pure-conf prompt.composer neuro (no code.py) works end-to-end."""
    root = tmp_path / "neuros"

    # Two prompt.block neuros authored as class-form code.py.
    (root / "block_identity").mkdir(parents=True)
    (root / "block_identity" / "conf.json").write_text(
        '{"name":"block_identity","description":"","kind":"prompt.block","inputs":[],"outputs":[]}'
    )
    (root / "block_identity" / "code.py").write_text(textwrap.dedent("""
        from core.prompt_neuro import PromptBlock
        class BlockIdentity(PromptBlock):
            template = "I am {{agent}}, a helpful assistant."
    """))

    (root / "block_tone").mkdir(parents=True)
    (root / "block_tone" / "conf.json").write_text(
        '{"name":"block_tone","description":"","kind":"prompt.block","inputs":[],"outputs":[]}'
    )
    (root / "block_tone" / "code.py").write_text(textwrap.dedent("""
        from core.prompt_neuro import PromptBlock
        class BlockTone(PromptBlock):
            template = "Tone: concise."
    """))

    # Pure-conf composer: no code.py, just kind + children + uses.
    (root / "reply_prompt").mkdir(parents=True)
    (root / "reply_prompt" / "conf.json").write_text(
        '{"name":"reply_prompt","description":"","kind":"prompt.composer",'
        '"children":["block_identity","block_tone"],'
        '"uses":["block_identity","block_tone"],"inputs":[],"outputs":[]}'
    )

    f = NeuroFactory(dir=str(root))
    out = await f.run("reply_prompt", {"__cid": "t"}, agent="Neuro")
    assert out["text"] == "I am Neuro, a helpful assistant.\n\nTone: concise."


async def test_describe_shows_prompt_kind(tmp_path):
    root = tmp_path / "neuros"
    (root / "p").mkdir(parents=True)
    (root / "p" / "conf.json").write_text(
        '{"name":"p","description":"","kind":"prompt.block","inputs":[],"outputs":[]}'
    )
    (root / "p" / "code.py").write_text(textwrap.dedent("""
        from core.prompt_neuro import PromptBlock
        class P(PromptBlock):
            template = "hi"
    """))

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["p"]["kind"] == "prompt.block"
    assert rich["p"]["kind_namespace"] == "prompt"
