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
            return out.crop(out.getbbox())
    except Exception as e:
        print('rembgが使えないので色で抜きます:', e)
    return cutout_color(im)

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
    """切り抜いた3点を、決めたバランスで並べる（下のものから順に置く）"""
    L = LAYOUT.get(kind, LAYOUT['jacket'])
    cv = backdrop().convert('RGBA')
    place(cv, bottom, *L['bottom'][:1], L['bottom'][1:3], L['bottom'][3], SHADOW_FLAT)
    place(cv, outer, *L['outer'][:1], L['outer'][1:3], L['outer'][3], SHADOW_FLAT)
    place(cv, shoes, *L['shoes'][:1], L['shoes'][1:3], L['shoes'][3], SHADOW_TALL)
    return cv.convert('RGB')
