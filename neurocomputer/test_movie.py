# test_moviepy.py
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

print("✓ moviepy.editor imported successfully!")

# (Optional) create a tiny 1-second silent video to prove it can write files:
from pathlib import Path

# create a 320×180 blue frame for 1 second
img = ImageClip(color=(0, 128, 255), size=(320, 180)).set_duration(1.0)
# loop that frame 3× to make a 3-second clip
video = concatenate_videoclips([img, img, img])
out = Path.cwd() / "moviepy_sanity.mp4"
video.write_videofile(
    str(out),
    fps=24,
    codec="libx264",
    audio=False,
    verbose=False,
    progress_bar=False
)
print(f"✓ Wrote a small file to: {out}")
