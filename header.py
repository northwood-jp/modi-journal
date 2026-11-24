"""コラムのトップ画像（1200×630、仕様書きタグ風）を作る"""
import random
from PIL import Image, ImageDraw, ImageFont

import os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts') + '/'   # リポジトリに入れたフォントを使う
SERIF, SANS = D + 'NotoSerifJP-Bold.otf', D + 'NotoSansJP-Bold.otf'
f = lambda p, s: ImageFont.truetype(p, s, index=0)


def fit(d, text, path, size, maxw):
    while size > 20 and d.textlength(text, font=f(path, size)) > maxw:
        size -= 2
    return f(path, size)


def make(no, title_lines, sub, fn):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), (62, 66, 44))
    d = ImageDraw.Draw(im)
    random.seed(no)
    for _ in range(16000):
        x, y = random.randrange(W), random.randrange(H)
        c = random.randint(-8, 8)
        d.point((x, y), fill=(62 + c, 66 + c, 44 + c))
    tx, ty, tw, th = 110, 60, 980, 510
    d.rectangle([tx + 10, ty + 10, tx + tw + 10, ty + th + 10], fill=(40, 42, 28))
    d.rectangle([tx, ty, tx + tw, ty + th], fill=(236, 230, 214))
    d.rectangle([tx + 16, ty + 16, tx + tw - 16, ty + th - 16], outline=(40, 40, 32), width=3)
    d.text((tx + 50, ty + 44), 'MoDi COLUMN  No.%02d' % no, font=f(SANS, 30), fill=(60, 60, 50))
    d.text((tx + tw - 50, ty + 44), 'ARCHIVE', font=f(SANS, 30), fill=(60, 60, 50), anchor='ra')
    d.line([tx + 50, ty + 96, tx + tw - 50, ty + 96], fill=(40, 40, 32), width=2)
    n = len(title_lines)
    y = ty + (190 if n == 1 else 150)
    for ln in title_lines:
        ft = fit(d, ln, SERIF, 72 if n == 1 else 60, tw - 120)
        d.text((W // 2, y), ln, font=ft, fill=(25, 25, 20), anchor='ma')
        y += ft.size + 14
    if sub:
        d.text((W // 2, y + 20), sub, font=fit(d, sub, SANS, 30, tw - 120), fill=(80, 80, 70), anchor='ma')
    d.line([tx + 50, ty + th - 92, tx + tw - 50, ty + th - 92], fill=(40, 40, 32), width=2)
    d.text((W // 2, ty + th - 70), 'MILITARY ARCHIVE CURATION STORE  ―  memento mori & carpe diem.',
           font=f(SANS, 22), fill=(60, 60, 50), anchor='ma')
    im.save(fn)
