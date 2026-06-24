"""
make_cta_overlay.py
Generates a green-screen animated SUBSCRIBE overlay (assets/overlays/subscribe_cta.mp4) branded
with a channel name. video_factory chroma-keys the green at render time. Parametric so the
channel name can be changed in one command (a placeholder until a Premiere version is dropped in).

Usage:  python tools/make_cta_overlay.py "MM Storybook"
        python tools/make_cta_overlay.py "FactZap" subscribe_cta_factzap   # custom out basename
"""
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

CORE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CORE)
FONT = os.path.join(ROOT, "assets", "Font", "Burbank.ttf")
OUT = os.path.join(ROOT, "assets", "overlays", "subscribe_cta.mp4")

W, H = 1080, 1920
DUR = 4.0
GREEN = (0, 255, 0)


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()


def outlined(draw, xy, text, fnt, fill, outline="black", ow=6, anchor="mm"):
    x, y = xy
    for dx in range(-ow, ow + 1):
        for dy in range(-ow, ow + 1):
            if dx * dx + dy * dy <= ow * ow:
                draw.text((x + dx, y + dy), text, font=fnt, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=fnt, fill=fill, anchor=anchor)


def build_card(channel):
    """A transparent RGBA card: channel name + red SUBSCRIBE button + bell-ish + finger tap."""
    cw, ch = 980, 520
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Channel name (top)
    outlined(d, (cw // 2, 70), channel.upper(), font(86), "white", ow=7)

    # Red rounded SUBSCRIBE button
    bx0, by0, bx1, by1 = 90, 170, cw - 90, 350
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=45, fill=(213, 0, 0))
    # little play-triangle glyph on the left of the text
    cy = (by0 + by1) // 2
    d.polygon([(bx0 + 70, cy - 34), (bx0 + 70, cy + 34), (bx0 + 124, cy)], fill="white")
    outlined(d, (cw // 2 + 40, cy), "SUBSCRIBE", font(96), "white", outline=(120, 0, 0), ow=3)

    # "tap" cue under the button
    outlined(d, (cw // 2, 430), "tap here ▶", font(52), (255, 240, 120), ow=4)
    return np.array(img)


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHANNEL_NAME", "MM Storybook")
    # Optional 2nd arg: output basename (without extension), e.g. "subscribe_cta_factzap".
    out_base = sys.argv[2] if len(sys.argv) > 2 else "subscribe_cta"
    out_path = os.path.join(ROOT, "assets", "overlays", f"{out_base}.mp4")
    print(f"Generating subscribe overlay for: {channel} -> {out_base}.mp4")

    bg = ColorClip((W, H), color=GREEN, duration=DUR)
    card = ImageClip(build_card(channel)).set_duration(DUR)
    # Gentle pulse so it grabs attention; centered horizontally, lower third.
    card = card.resize(lambda t: 1.0 + 0.05 * math.sin(2 * math.pi * 1.5 * t))
    card = card.set_position(("center", 1180))

    comp = CompositeVideoClip([bg, card], size=(W, H)).set_duration(DUR)
    comp.write_videofile(out_path, fps=30, codec="libx264", audio=False, preset="medium",
                         logger=None, verbose=False)
    comp.close()
    print(f"✅ Wrote {out_path}")


if __name__ == "__main__":
    main()
