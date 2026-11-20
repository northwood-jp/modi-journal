"""コーディネート画像を作る部品（切り抜き・背景・影・配置）。001・002で決めたバランスを使う。"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

W, H = 1080, 1350
BG_SLATE = ((160, 175, 188), (104, 119, 133))                          # スレートブルー（中）
SHADOW_FLAT = ((2, 0.40, 11, 15), (9, 0.14, 16, 22), (3, 0.25, 2, 3))   # 平置きの服
SHADOW_TALL = ((2, 0.42, 18, 24), (10, 0.16, 26, 34), (3, 0.25, 2, 3))  # 靴など高さのある物
# (幅px, 中心x, 中心y, 角度)  001（短丈アウター）と002（長めのコート）でケンさんOKのバランス
LAYOUT = {
    'jacket': {'outer': (530, 578, 440, 0), 'bottom': (385, 556, 920, 0), 'shoes': (240, 300, 1100, -12)},
    'coat':   {'outer': (530, 570, 430, 0), 'bottom': (360, 556, 935, 0), 'shoes': (245, 300, 1100, -8)},
}

_session = None
def cutout(im):
    """背景を抜く。rembg（高精度）が使えればそれを使い、だめなら色で抜く"""
    global _session
    try:
        from rembg import remove, new_session
        if _session is None:
            _session = new_session('isnet-general-use')
        out = remove(im.convert('RGB'), session=_session)
        a = np.asarray(out.split()[3])
        if (a > 128).mean() > 0.05:
            return keep_main(out)
    except Exception as e:
        print('rembgが使えないので色で抜きます:', e)
    return cutout_color(im)

def keep_main(out):
    """商品だけを残す：近くにあるかたまり同士（ブーツの左右など）はひとまとめにして、
    いちばん大きいまとまりだけを残す。離れた2枚目の写真や文字は消す"""
    a = np.asarray(out.split()[3]).copy()
    fg = a > 100
    gap = max(3, int(out.width * 0.012))
    near = ndi.binary_dilation(fg, iterations=gap)      # 少し太らせて、近いもの同士をつなげる
    lab, n = ndi.label(near)
    if n:
        sizes = ndi.sum(fg, lab, range(1, n + 1))
        main = np.argmax(sizes) + 1
        a[lab != main] = 0          # まとまりの外は、うっすら残った影やノイズも含めて全部消す
    a[a < 40] = 0
    out = out.copy(); out.putalpha(Image.fromarray(a))
    return out.crop(out.getbbox())

def cutout_color(im):
    a = np.asarray(im.convert('RGB')).astype(int)
    mx, mn = a.max(2), a.min(2)
    white = (mn > 190) & (mx - mn < 15)
    lab, n = ndi.label(~white)
    if not n:
        return im.convert('RGBA')
    sizes = ndi.sum(~white, lab, range(1, n + 1))
    fg = lab == (np.argmax(sizes) + 1)
    fg = ndi.binary_fill_holes(fg)
    fg = ndi.binary_opening(fg, iterations=2)
    fg = ndi.binary_erosion(fg, iterations=2)
    alpha = Image.fromarray((fg * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.0))
    out = im.convert('RGBA'); out.putalpha(alpha)
    return out.crop(out.getbbox())

def backdrop(c_center=BG_SLATE[0], c_edge=BG_SLATE[1]):
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W * 0.5) / W) ** 2 + ((y - H * 0.38) / H) ** 2) / 0.75
    r = np.clip(r, 0, 1)[..., None] ** 1.4
    img = np.array(c_center) * (1 - r) + np.array(c_edge) * r
    noise = np.random.default_rng(1).normal(0, 1.2, (H, W, 1))
    return Image.fromarray(np.clip(img + noise, 0, 255).astype('uint8'), 'RGB')

def place(canvas, item, width, center, angle, layers):
    r = width / item.width
    it = item.resize((int(item.width * r), int(item.height * r)), Image.LANCZOS).rotate(angle, expand=True, resample=Image.BICUBIC)
    pad = 60
    x, y = int(center[0] - it.width / 2), int(center[1] - it.height / 2)
    a = it.split()[3]
    big = Image.new('L', (it.width + pad * 2, it.height + pad * 2), 0); big.paste(a, (pad, pad))
    for blur, op, dx, dy in layers:
        m = big.filter(ImageFilter.GaussianBlur(blur)).point(lambda v, op=op: int(v * op))
        sh = Image.new('RGBA', big.size, (24, 32, 44, 0)); sh.putalpha(m)
        canvas.alpha_composite(sh, (x - pad + dx, y - pad + dy))
    canvas.alpha_composite(it, (x, y))

def compose(outer, bottom, shoes, kind='jacket'):
    """切り抜いた3点を、001・002のバランスで並べる。
    決まった座標ではなく「服どうしの位置関係」で置く：
      ・ボトムは丈（高さ）をそろえる。横に広い写真は幅で抑える
      ・アウターは幅をそろえるが、ボトムに対して大きすぎるときは、001・002の比率まで縮める
      ・ボトムの上端をアウターのすその中に深く入れ、真ん中をそろえる
      ・全体を画面の上下まん中に置き、靴はボトムのすその左に"""
    cv = backdrop().convert('RGBA')
    coat = (kind == 'coat')
    def fit(im, w=None, h=None):
        return (w, int(im.height * w / im.width)) if w else (int(im.width * h / im.height), h)
    # ボトム
    bw, bh = fit(bottom, h=700 if not coat else 640)
    if bw > 460:
        bw, bh = fit(bottom, w=460)
    # アウター（001・002で決めた「アウターの丈÷ボトムの丈」を上限にする）
    ow, oh = fit(outer, w=530 if not coat else 500)
    ratio_max = 0.80 if not coat else 1.00
    if oh > bh * ratio_max:
        ow, oh = fit(outer, h=int(bh * ratio_max))
    overlap = int(oh * (0.16 if not coat else 0.10))
    total = oh + bh - overlap
    otop = max(40, (H - total) // 2)
    btop = otop + oh - overlap
    cx = 565
    # 靴
    sw = 245
    sh_ = int(shoes.height * sw / shoes.width)
    sx = max(150, cx - bw // 2 - sw // 2 + 40)
    sy = min(H - sh_ // 2 - 30, btop + bh - sh_ // 2 - 30)
    place(cv, bottom, bw, (cx, btop + bh // 2), 0, SHADOW_FLAT)
    place(cv, outer, ow, (cx, otop + oh // 2), 0, SHADOW_FLAT)
    place(cv, shoes, sw, (sx, sy), -10, SHADOW_TALL)
    return cv.convert('RGB')
