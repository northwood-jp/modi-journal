"""MoDiトップのスライドショーに入れる「Dr.MoDiのコーディネート提案」のバナー（1200×630）を作る"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, 'fonts') + '/'
OLIVE, CREAM, INK = (62, 66, 44), (246, 242, 232), (34, 34, 34)


def make(coord_img, icon_img, no, title, out):
    W, H = 1200, 630
    M = 40          # 外側の余白（上下左右とも同じ）
    P = 48          # カードの内側の余白（上下左右とも同じ）
    im = Image.new('RGB', (W, H), OLIVE)
    d = ImageDraw.Draw(im)
    # 左：最新のコーデ画像（縦4:5）を、上下の余白いっぱいに
    c = Image.open(coord_img).convert('RGB')
    ch = H - 2 * M
    cw = int(c.width * ch / c.height)
    c = c.resize((cw, ch), Image.LANCZOS)
    im.paste(c, (M, M))
    # 右：クリーム色のカード
    x0, y0, x1, y1 = M + cw + M, M, W - M, H - M
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    serif = lambda s: ImageFont.truetype(F + 'NotoSerifJP-Bold.otf', s)
    sans = lambda s: ImageFont.truetype(F + 'NotoSansJP-Bold.otf', s)
    L, R, T, B = x0 + P, x1 - P, y0 + P, y1 - P     # 文字を置いてよい範囲
    # 見出し：Dr.MoDiのアイコン＋styling recommendations、下に線
    ih, tx = 84, L
    if os.path.exists(icon_img):
        ic = Image.open(icon_img).convert('RGBA')
        ic = ic.resize((int(ic.width * ih / ic.height), ih), Image.LANCZOS)
        im.paste(ic, (L, T), ic)
        tx = L + ic.width + 16
    line_y = T + ih + 4
    d.text((tx, line_y - 14), 'styling recommendations', font=serif(26), fill=OLIVE, anchor='ls')
    d.line([L, line_y, R, line_y], fill=OLIVE, width=2)
    # 見出しの3行は行間を詰めて、ひとつの塊に見せる（ベースラインで揃える）
    y = line_y + 64
    d.text((L, y), 'Dr.MoDiの', font=sans(40), fill=INK, anchor='ls'); y += 50
    d.text((L, y), 'コーディネート提案', font=sans(40), fill=INK, anchor='ls'); y += 44
    d.text((L, y), '更新しました', font=sans(30), fill=OLIVE, anchor='ls'); y += 62
    y_new = y
    # タイトル：基本は32ptで1行。長いときは1行に収まるまで小さくし、24ptでも入らなければ2行に
    size = 32
    while size > 24 and d.textlength(title, font=serif(size)) > R - L:
        size -= 2
    tf = serif(size)
    lines, cur = [], ''
    for ch_ in title:
        if d.textlength(cur + ch_, font=tf) > R - L:
            lines.append(cur); cur = ch_
        else:
            cur += ch_
    lines.append(cur)
    lines = lines[:2]
    # 2行になって下の帯に近づきすぎるときは、NEWとタイトルをまとめて上へずらす
    last = y_new + 48 + (len(lines) - 1) * (size + 10)
    y_new -= max(0, last - (B - 44 - 36))
    d.text((L, y_new), 'NEW  No.%s' % no, font=sans(22), fill=OLIVE, anchor='ls')
    y = y_new + 48
    for ln in lines:
        d.text((L, y), ln, font=tf, fill=INK, anchor='ls'); y += size + 10
    # いちばん下の誘い文句は、オリーブの帯に白抜き文字で目立たせる（カードの下の余白にそろえる）
    cta, cf = 'MoDiのアイテムだけで組んだ着こなし術 →', sans(18)
    tw = d.textlength(cta, font=cf)
    d.rectangle([L, B - 44, L + tw + 32, B], fill=OLIVE)
    d.text((L + 16, B - 22), cta, font=cf, fill=CREAM, anchor='lm')
    im.save(out, quality=88)
