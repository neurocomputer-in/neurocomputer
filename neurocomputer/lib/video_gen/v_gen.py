# lib/video_gen/main.py
"""
Create a complete video (images + voice-over) from a text prompt, in modular “neuros” 
that can plug into Neo.

Classes
-------
1. ScriptWriter       – LLM-powered narrative generator
2. ScriptSectioniser  – splits the script into timed blocks (drops empty chunks)
3. ImagePromptMaker   – adds art-direction to each block
4. ImageCreator       – generates PNGs via OpenAI Images
5. TTSMaker           – produces an MP3 per block (OpenAI TTS or fallback gTTS)
6. VideoAssembler     – stitches everything into an MP4 via MoviePy sub-modules
7. InfinityVideoPipeline   – convenience façade that wires them together

All file paths are Ubuntu-friendly. Requires Python 3.10+ and these packages:
    pip install openai moviepy imageio[ffmpeg] pillow tqdm gTTS python-dotenv

Set OPENAI_API_KEY in your environment before running.
"""

import os
import uuid
import json
import base64
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Ensure PIL.Image.ANTIALIAS exists on newer Pillow versions
from PIL import Image as _PIL_Image
if not hasattr(_PIL_Image, "ANTIALIAS"):
    _PIL_Image.ANTIALIAS = _PIL_Image.LANCZOS

from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

# ────────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ────────────────────────────────────────────────────────────────────────────────

# Default output directory: ~/videos
_DEF_OUT = Path.home() / "videos"
_DEF_OUT.mkdir(exist_ok=True)

# Load environment variables (e.g. OPENAI_API_KEY) from a .env at repo root
repo_root = Path(__file__).resolve().parents[2]   # ../../ → ~/projects/Neo
env_path = repo_root / ".env"
load_dotenv(dotenv_path=env_path)
print("→ Loading .env from", env_path)
print("→ OPENAI_API_KEY is", os.getenv("OPENAI_API_KEY"))

client = OpenAI()  # Reads API key from environment


def _uuid_fname(ext: str) -> str:
    return f"{uuid.uuid4().hex}.{ext}"


# ────────────────────────────────────────────────────────────────────────────────
# 1.  ScriptWriter
# ────────────────────────────────────────────────────────────────────────────────

class ScriptWriter:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        self.model = model
        self.temp = temperature

    def generate_script(self, prompt: str, duration: int = 60) -> str:
        system_prompt = (
            "You are a concise video script writer. Return plain text with a blank line every 2–3 sentences "
            "so that it can be split into multiple chunks."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Write a narrative for a video of ~{} seconds. "
                    "No timestamps, no markup.\n\nTopic: {}".format(duration, prompt)
                ),
            },
        ]
        rsp = client.chat.completions.create(
            model=self.model, temperature=self.temp, messages=messages
        )
        return rsp.choices[0].message.content.strip()


# ────────────────────────────────────────────────────────────────────────────────
# 2.  ScriptSectioniser (sentence-based splitter, drops empty chunks)
# ────────────────────────────────────────────────────────────────────────────────

import re

class ScriptSectioniser:
    def sectionise(
        self, script: str, duration: int = 60, chunk_sec: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Split the script into roughly equal‐time sections (~chunk_sec seconds per section)
        by first splitting on sentence boundaries. Discard any empty chunks and re‐index.
        Returns a list of dicts: {"idx": int, "text": str, "start": int, "end": int}.
        """
        # 1) Split on sentence endings (., !, or ?) followed by whitespace
        sentences = [
            s.strip()
            for s in re.split(r'(?<=[\.!?])\s+', script)
            if s.strip()
        ]
        # 2) Determine how many chunks we’d like
        n_chunks = max(1, duration // chunk_sec)
        # 3) Round-robin assign sentences to each chunk index
        raw_chunks = [" ".join(sentences[i::n_chunks]) for i in range(n_chunks)]
        # 4) Filter out any chunk whose text is empty
        filtered = [chunk for chunk in raw_chunks if chunk.strip()]
        # 5) Build final list with new idx, start, end
        result: List[Dict[str, Any]] = []
        for new_idx, chunk_text in enumerate(filtered):
            start_time = new_idx * chunk_sec
            end_time = (new_idx + 1) * chunk_sec
            result.append(
                {
                    "idx": new_idx,
                    "text": chunk_text,
                    "start": start_time,
                    "end": end_time,
                }
            )
        return result


# ────────────────────────────────────────────────────────────────────────────────
# 3.  ImagePromptMaker
# ────────────────────────────────────────────────────────────────────────────────

class ImagePromptMaker:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4, max_retries: int = 2):
        self.model = model
        self.temp = temperature
        self.max_retries = max_retries

    def generate_prompts(
        self, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Given [{"idx":…, "text":…}, …], ask the LLM to return
        [{"idx":…, "image_prompt":…}, …] describing how to illustrate each block.
        This will retry up to `max_retries` times if the JSON parse fails.
        """
        sys_msg = (
            "You are an art-director. For each JSON item {idx,text}, "
            "return exactly a JSON array of objects, each containing "
            "{idx, image_prompt}. NOTHING ELSE. Respond with JSON array only."
        )

        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            messages = [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": json.dumps(sections, ensure_ascii=False)},
            ]
            rsp = client.chat.completions.create(
                model=self.model, temperature=self.temp, messages=messages
            )
            raw = rsp.choices[0].message.content.strip()
            print(f"\n[ImagePromptMaker] Attempt {attempt}, raw LLM response:\n{raw}\n")

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and all(
                    isinstance(item, dict) and "idx" in item and "image_prompt" in item
                    for item in parsed
                ):
                    return parsed
                else:
                    raise ValueError("Parsed JSON did not match expected schema.")
            except Exception as e:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"Failed to parse valid JSON after {self.max_retries} attempts. "
                        f"Last error: {e}\nLast raw response:\n{raw}"
                    )
                print(f"[ImagePromptMaker] JSON parse failed: {e}. Retrying...\n")
                continue


# ────────────────────────────────────────────────────────────────────────────────
# 4.  ImageCreator
# ────────────────────────────────────────────────────────────────────────────────

class ImageCreator:
    def __init__(self, size: str = "1024x1024", out_dir: Path | str | None = None):
        self.size = size
        self.dir = Path(out_dir or tempfile.mkdtemp(prefix="neo_imgs_"))
        self.dir.mkdir(exist_ok=True)

    def generate_images(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        For each {"idx":…, "image_prompt":…}, call OpenAI Images API with response_format="b64_json".
        Save each PNG locally and return [{"idx":…, "path": "/abs/path/to/png"}].
        """
        paths: List[Dict[str, Any]] = []
        for item in tqdm(prompts, desc="Generating Images"):
            rsp = client.images.generate(
                prompt=item["image_prompt"],
                n=1,
                size=self.size,
                response_format="b64_json"
            )
            b64 = rsp.data[0].b64_json
            if b64 is None:
                raise RuntimeError(
                    f"OpenAI returned no b64_json for idx={item['idx']}. Full response:\n{rsp}\n"
                )
            fp = self.dir / _uuid_fname("png")
            with fp.open("wb") as f:
                f.write(base64.b64decode(b64))
            paths.append({"idx": item["idx"], "path": str(fp)})
        return paths


# ────────────────────────────────────────────────────────────────────────────────
# 5.  TTSMaker (skips empty text sections)
# ────────────────────────────────────────────────────────────────────────────────

class TTSMaker:
    def __init__(self, voice: str = "alloy", out_dir: Path | str | None = None):
        self.voice = voice
        self.dir = Path(out_dir or tempfile.mkdtemp(prefix="neo_audio_"))
        self.dir.mkdir(exist_ok=True)

    def generate_audio(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        For each {"idx":…, "text":…}, attempt OpenAI TTS; on failure, fallback to gTTS.
        Skip any section whose text is empty.
        Returns [{"idx":…, "path":…}].
        """
        paths: List[Dict[str, Any]] = []
        for s in tqdm(sections, desc="Generating Audio"):
            text = s.get("text", "").strip()
            if not text:
                print(f"[TTSMaker] Skipping empty text for idx={s['idx']}")
                continue

            try:
                rsp = client.audio.speech.create(
                    model="tts-1", voice=self.voice, input=text
                )
                fp = self.dir / _uuid_fname("mp3")
                rsp.stream_to_file(str(fp))
            except Exception:
                from gtts import gTTS
                tts = gTTS(text=text, lang="en")
                fp = self.dir / _uuid_fname("mp3")
                tts.save(str(fp))

            paths.append({"idx": s["idx"], "path": str(fp)})
        return paths


# ────────────────────────────────────────────────────────────────────────────────
# 6.  VideoAssembler
# ────────────────────────────────────────────────────────────────────────────────

class VideoAssembler:
    def assemble(
        self,
        image_paths: List[Dict[str, Any]],
        audio_paths: List[Dict[str, Any]],
        slug: str | None = None,
        out_dir: Path | str = _DEF_OUT,
        fps: int = 60,
    ) -> Path:
        """
        Given lists of {"idx", "path"} for images and audio, stitch them into
        a single MP4. Each image is shown for exactly the duration of its corresponding audio clip.
        Uses MoviePy sub-modules (not moviepy.editor) to avoid import errors.
        """
        # Late imports of exactly what we need:
        try:
            from moviepy.video.VideoClip import ImageClip
            from moviepy.audio.io.AudioFileClip import AudioFileClip
            from moviepy.video.compositing.concatenate import concatenate_videoclips
            from moviepy.video.fx.resize import resize          # ← for zoom
        except ImportError as e:
            raise ModuleNotFoundError(
                "Could not import MoviePy sub-modules. Ensure you ran:\n"
                "    pip install moviepy imageio[ffmpeg]\n"
                "in the same virtualenv."
            ) from e

        slug = slug or uuid.uuid4().hex[:8]
        out_dir = Path(out_dir) / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        image_paths.sort(key=lambda x: x["idx"])
        audio_paths.sort(key=lambda x: x["idx"])

        clips = []
        for img_info, aud_info in zip(image_paths, audio_paths):
            audio_clip = AudioFileClip(aud_info["path"])

            # --- Ken-Burns zoom (±15%) with smoothstep easing -------------------------------
            def zoom(t, total=audio_clip.duration, amount=0.15, direction=1):
                """Scale factor over time t (0→total) with smoothstep easing."""
                # direction = 1 → zoom-in, -1 → zoom-out (alternate by idx)
                # Smoothstep easing for more natural acceleration/deceleration
                frac = t / total
                smooth_frac = frac * frac * (3 - 2 * frac)  # Smoothstep function
                return 1 + direction * amount * smooth_frac

            z_dir = 1 if img_info["idx"] % 2 == 0 else -1  # alternate in / out

            img_clip = (
                ImageClip(img_info["path"])
                .set_duration(audio_clip.duration)
                .fx(resize, lambda t: zoom(t, direction=z_dir))
                .set_audio(audio_clip)
            )
            clips.append(img_clip)

        final = concatenate_videoclips(clips, method="compose")
        video_path = out_dir / "final.mp4"

        # Make sure `ffmpeg` is in your PATH
        final.write_videofile(
            str(video_path), fps=fps, codec="libx264", audio_codec="aac"
        )
        return video_path


# ────────────────────────────────────────────────────────────────────────────────
# 7.  InfinityVideoPipeline – orchestration sugar
# ────────────────────────────────────────────────────────────────────────────────

class InfinityVideoPipeline:
    """High-level convenience: one call does the entire flow end-to-end."""

    def __init__(self):
        self.writer = ScriptWriter()
        self.cutter = ScriptSectioniser()
        self.prompt_maker = ImagePromptMaker()
        self.img_gen = ImageCreator()
        self.tts = TTSMaker()
        self.assembler = VideoAssembler()

    def run(self, prompt: str, duration: int = 60, slug: str | None = None) -> Path:
        print("➤ Generating script…")
        script = self.writer.generate_script(prompt, duration)

        print("➤ Splitting into sections…")
        sections = self.cutter.sectionise(script, duration)

        print("➤ Crafting image prompts…")
        img_prompts = self.prompt_maker.generate_prompts(sections)

        print("➤ Generating images…")
        img_paths = self.img_gen.generate_images(img_prompts)

        print("➤ Generating audio…")
        aud_paths = self.tts.generate_audio(sections)

        print("➤ Assembling final video… (this may take a while)")
        video_path = self.assembler.assemble(img_paths, aud_paths, slug)
        print(f"✅ Done → {video_path}\n")
        return video_path


# ────────────────────────────────────────────────────────────────────────────────
# 8.  CLI entry point (optional)
# ────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Make a narrated video from text")
    parser.add_argument("prompt", help="Topic or prompt for the video")
    parser.add_argument("--sec", type=int, default=60, help="Approx duration (s)")
    parser.add_argument("--slug", default=None, help="Folder slug for output")
    args = parser.parse_args()

    pipeline = InfinityVideoPipeline()
    pipeline.run(args.prompt, args.sec, args.slug)
