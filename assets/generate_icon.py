"""
Gera o icone/logo do Guaxinim (mascote do app) proceduralmente com Pillow.
Rode uma vez: python assets/generate_icon.py
Produz: icon.ico (multi-resolucao) e logo.png (para usar dentro da GUI).
"""

import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

BG_TRANSPARENT = (0, 0, 0, 0)
ACCENT = (53, 201, 154, 255)       # verde-agua (mesma cor do app)
ACCENT_DARK = (39, 156, 120, 255)
FACE = (222, 226, 230, 255)        # cinza claro do rosto
FACE_SHADOW = (196, 202, 208, 255)
MASK = (46, 52, 58, 255)           # mascara escura dos olhos
EAR_OUTER = (70, 78, 86, 255)
EAR_INNER = (232, 236, 239, 255)
EYE_WHITE = (255, 255, 255, 255)
EYE_PUPIL = (24, 27, 30, 255)
NOSE = (28, 31, 34, 255)
BUBBLE = (255, 255, 255, 90)


def draw_raccoon(size: int) -> Image.Image:
    """Desenha o guaxinim mascote num canvas quadrado, com fundo circular de cor."""
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), BG_TRANSPARENT)
    d = ImageDraw.Draw(img)

    pad = int(s * 0.04)
    d.ellipse([pad, pad, s - pad, s - pad], fill=ACCENT)
    d.ellipse([pad, pad, s - pad, s - pad], outline=ACCENT_DARK, width=int(s * 0.012))

    cx, cy = s / 2, s * 0.56
    head_r = s * 0.30

    ear_r = s * 0.115
    ear_offset_x = head_r * 0.72
    ear_offset_y = head_r * 0.78
    for sign in (-1, 1):
        ex, ey = cx + sign * ear_offset_x, cy - ear_offset_y
        d.ellipse([ex - ear_r, ey - ear_r, ex + ear_r, ey + ear_r], fill=EAR_OUTER)
        inner_r = ear_r * 0.55
        d.ellipse([ex - inner_r, ey - inner_r * 0.9, ex + inner_r, ey + inner_r * 1.0],
                  fill=EAR_INNER)

    d.ellipse([cx - head_r, cy - head_r, cx + head_r, cy + head_r], fill=FACE)

    mask_w = head_r * 1.62
    mask_h = head_r * 0.62
    mask_y = cy - head_r * 0.12
    d.ellipse([cx - mask_w / 2, mask_y - mask_h / 2, cx + mask_w / 2, mask_y + mask_h / 2],
              fill=MASK)

    eye_r = head_r * 0.20
    eye_off_x = head_r * 0.42
    eye_y = mask_y
    for sign in (-1, 1):
        ex = cx + sign * eye_off_x
        d.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=EYE_WHITE)
        pr = eye_r * 0.55
        px = ex + sign * eye_r * 0.12
        d.ellipse([px - pr, eye_y - pr, px + pr, eye_y + pr], fill=EYE_PUPIL)
        hr = pr * 0.32
        d.ellipse([px - hr * 2, eye_y - hr * 2.2, px - hr * 0.3, eye_y - hr * 0.5],
                  fill=EYE_WHITE)

    snout_w = head_r * 0.58
    snout_h = head_r * 0.5
    snout_y = cy + head_r * 0.30
    d.ellipse([cx - snout_w / 2, snout_y - snout_h / 2, cx + snout_w / 2, snout_y + snout_h / 2],
              fill=FACE_SHADOW)

    nose_r = head_r * 0.14
    nose_y = snout_y - snout_h * 0.12
    d.ellipse([cx - nose_r, nose_y - nose_r * 0.8, cx + nose_r, nose_y + nose_r * 0.8], fill=NOSE)

    mouth_y = nose_y + nose_r
    d.arc([cx - nose_r * 1.6, mouth_y - nose_r, cx, mouth_y + nose_r * 1.4], start=20, end=160,
          fill=NOSE, width=int(s * 0.01))
    d.arc([cx, mouth_y - nose_r, cx + nose_r * 1.6, mouth_y + nose_r * 1.4], start=20, end=160,
          fill=NOSE, width=int(s * 0.01))

    import random
    random.seed(7)
    for _ in range(6):
        bx = cx + random.uniform(-head_r * 1.5, head_r * 1.5)
        by = cy - head_r * 1.7 + random.uniform(-head_r * 0.3, head_r * 0.3)
        br = random.uniform(s * 0.012, s * 0.03)
        if 0 < bx < s and 0 < by < s:
            d.ellipse([bx - br, by - br, bx + br, by + br], fill=BUBBLE)

    img = img.filter(ImageFilter.SMOOTH_MORE)
    return img.resize((size, size), Image.LANCZOS)


def main():
    logo = draw_raccoon(512)
    logo.save(os.path.join(HERE, "logo.png"))

    icon_sizes = [16, 24, 32, 48, 64, 128, 256]
    icon_images = [draw_raccoon(sz) for sz in icon_sizes]
    icon_images[-1].save(
        os.path.join(HERE, "icon.ico"),
        format="ICO",
        sizes=[(sz, sz) for sz in icon_sizes],
        append_images=icon_images[:-1],
    )
    print("Gerado: logo.png e icon.ico em", HERE)


if __name__ == "__main__":
    main()
