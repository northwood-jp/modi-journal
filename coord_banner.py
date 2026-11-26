"""MoDiトップのスライドショーに入れる「Dr.MoDiのコーディネート提案」のバナー（1200×630）を作る"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, 'fonts') + '/'
OLIVE, CREAM, INK = (62, 66, 44), (246, 242, 232), (34, 34, 34)


def make(coord_img, icon_img, no, title, out):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), OLIVE)
    d = ImageDraw.Draw(im)
    # 左：最新のコーデ画像（縦4:5）を、上下いっぱいに
    c = Image.open(coord_img).convert('RGB')
    ch = H - 60
    cw = int(c.width * ch / c.height)
    c = c.resize((cw, ch), Image.LANCZOS)
    im.paste(c, (60, 30))
    # 右：クリーム色のカード
    x0 = 60 + cw + 50
    d.rectangle([x0, 30, W - 60, H - 30], fill=CREAM)
    serif = lambda s: ImageFont.truetype(F + 'NotoSerifJP-Bold.otf', s)
    sans = lambda s: ImageFont.truetype(F + 'NotoSansJP-Bold.otf', s)
    cx = x0 + 44
    # 見出しの左にDr.MoDiのアイコン（線の上に立たせる）
    tx = cx
    if os.path.exists(icon_img):
        ic = Image.open(icon_img).convert('RGBA')
        ih = 92
        ic = ic.resize((int(ic.width * ih / ic.height), ih), Image.LANCZOS)
        im.paste(ic, (cx, 126 - ih), ic)
        tx = cx + ic.width + 16
    d.text((tx, 112), 'styling recommendations', font=serif(26), fill=OLIVE, anchor='ls')
    d.line([cx, 128, W - 104, 128], fill=OLIVE, width=2)
    # 見出しの3行は行間を詰めて、ひとつの塊に見せる
    d.text((cx, 152), 'Dr.MoDiの', font=sans(40), fill=INK)
    d.text((cx, 200), 'コーディネート提案', font=sans(40), fill=INK)
    d.text((cx, 252), '更新しました', font=sans(30), fill=OLIVE)
    d.text((cx, 330), 'NEW  No.%s' % no, font=sans(22), fill=OLIVE)
    # タイトル：カードの幅で折り返す（最大2行）
    tf = serif(24)
    maxw = W - 104 - cx
    lines, cur = [], ''
    for ch_ in title:
        if d.textlength(cur + ch_, font=tf) > maxw:
            lines.append(cur); cur = ch_
        else:
            cur += ch_
    lines.append(cur)
    d.multiline_text((cx, 366), '\n'.join(lines[:2]), font=tf, fill=INK, spacing=10)
    # いちばん下の誘い文句は、オリーブの帯に白抜き文字で目立たせる
    cta, cf = 'MoDiのアイテムだけで組んだ着こなし術 →', sans(18)
    tw = d.textlength(cta, font=cf)
    by = H - 96
    d.rectangle([cx, by, cx + tw + 32, by + 44], fill=OLIVE)
    d.text((cx + 16, by + 22), cta, font=cf, fill=CREAM, anchor='lm')
    im.save(out, quality=88)
