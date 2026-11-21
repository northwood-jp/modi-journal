"""小さい商品画像（300px）を600pxにする。
まず同じ写真の大きい版（x.jpg）を探し、無ければAI（EDSR）で2倍に引き伸ばす。
結果は upscale/out/ に、見くらべ用の画像は upscale/compare/ に置く。"""
import io, json, os, urllib.request
from PIL import Image, ImageDraw
import numpy as np

OUT, CMP = 'upscale/out', 'upscale/compare'
os.makedirs(OUT, exist_ok=True); os.makedirs(CMP, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0'}

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            return Image.open(io.BytesIO(r.read())).convert('RGB')
    except Exception:
        return None

sr = None
try:
    import cv2
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel('EDSR_x2.pb'); sr.setModel('edsr', 2)
except Exception as e:
    sr = None
    print('AIモデルを使えないので、通常の拡大にします:', e)

def upscale(im):
    if sr is not None:
        arr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        return Image.fromarray(cv2.cvtColor(sr.upsample(arr), cv2.COLOR_BGR2RGB))
    return im.resize((im.width * 2, im.height * 2), Image.LANCZOS)

urls = json.load(open('upscale/targets.json'))['urls']
SHARD, SHARDS = int(os.environ.get('SHARD', 0)), int(os.environ.get('SHARDS', 1))
urls = urls[SHARD::SHARDS]   # 何台かに分けて同時に処理する
result = {}
pairs = []
for n, u in enumerate(urls, 1):
    parts = u.split('/')
    name = parts[-3] + '_' + parts[-2] + '.jpg'
    big = get(u[:-5] + 'x.jpg')
    if big is not None and big.width >= 600:
        big.save(os.path.join(OUT, name), quality=92)
        result[u] = {'file': name, 'method': 'x.jpg', 'size': big.size}
        print(n, 'x.jpgあり', name, big.size); continue
    small = get(u)
    if small is None:
        result[u] = {'file': '', 'method': '取得失敗'}; print(n, '取得失敗', u); continue
    if small.width >= 600:
        small.save(os.path.join(OUT, name), quality=92)
        result[u] = {'file': name, 'method': 'もとから大きい', 'size': small.size}; continue
    up = upscale(small)
    if up.width < 600:
        up = up.resize((600, round(up.height * 600 / up.width)), Image.LANCZOS)
    up.save(os.path.join(OUT, name), quality=92)
    result[u] = {'file': name, 'method': 'AI拡大' if sr is not None else '通常拡大', 'from': small.size, 'size': up.size}
    pairs.append((name, small, up))
    print(n, result[u]['method'], name, small.size, '->', up.size)

json.dump(result, open('upscale/result_%d.json' % SHARD, 'w'), ensure_ascii=False, indent=1)

# 見くらべ用：左＝元の画像をそのまま拡大／右＝AI拡大。1枚に6組ずつ
for k in range(0, len(pairs), 6):
    chunk = pairs[k:k + 6]
    sheet = Image.new('RGB', (1220, 610 * len(chunk)), 'white')
    d = ImageDraw.Draw(sheet)
    for j, (name, small, up) in enumerate(chunk):
        a = small.resize(up.size, Image.BICUBIC).resize((600, 600))
        b = up.resize((600, 600))
        sheet.paste(a, (0, 610 * j)); sheet.paste(b, (620, 610 * j))
        d.text((8, 610 * j + 8), name + '  before', fill='red'); d.text((628, 610 * j + 8), 'after (AI)', fill='red')
    sheet.save(os.path.join(CMP, '%d_%02d.jpg' % (SHARD, k // 6 + 1)), quality=80)
print('完了：', {m: sum(1 for r in result.values() if r['method'] == m) for m in set(r['method'] for r in result.values())})
