"""BASEにある古い小さい画像と、600pxにした新しい画像の対応を調べて upscale/plan.json に書く"""
import io, json, urllib.request
from PIL import Image
import numpy as np
UA = {'User-Agent': 'Mozilla/5.0'}
cache = {}
def get(url):
    if url in cache: return cache[url]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            im = Image.open(io.BytesIO(r.read())).convert('RGB')
    except Exception:
        im = None
    cache[url] = im; return im
def sig(im):
    return np.asarray(im.convert('L').resize((32, 32), Image.BILINEAR), dtype=float)
res = json.load(open('upscale/result_all.json'))
items = json.load(open('upscale/map_in.json'))
plan, report = [], []
for it in items:
    small_src = [u for u in it['src'] if u.endswith('/l.jpg') and res.get(u, {}).get('file')]
    sigs = [(u, sig(get(u))) for u in small_src if get(u) is not None]
    p = []
    for b in it['base']:
        im = get(b['url'])
        if im is None or im.width >= 600: continue
        s = sig(im)
        best = min(sigs, key=lambda x: float(((x[1] - s) ** 2).mean()), default=None)
        if best is None: continue
        err = float(((best[1] - s) ** 2).mean())
        if err > 150: report.append((it['id'], b['id'], round(err))); continue
        p.append({'old': b['id'], 'file': res[best[0]]['file'], 'err': round(err, 1)})
    plan.append({'row': it['row'], 'id': it['id'], 'plan': p})
    print(it['id'], len(it['base']), '枚中', len(p), '枚を差し替え')
json.dump(plan, open('upscale/plan.json', 'w'), indent=0)
print('合計', sum(len(x['plan']) for x in plan), '枚／一致しなかったもの', report)
