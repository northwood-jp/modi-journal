"""コーデ候補シートとやり取りして、①候補画像を作る ②採用されたものを公開する"""
import io, json, os, re, time, requests
from PIL import Image
import coord_lib

GAS_URL, TOKEN = os.environ['GAS_URL'], os.environ['GAS_TOKEN']
REPO_RAW = 'https://raw.githubusercontent.com/northwood-jp/modi-journal/main/'
SITE = 'https://journal.northwood-jp.com/'

def gas_get():
    r = requests.get(GAS_URL, params={'mode': 'coords', 'token': TOKEN}, timeout=60)
    return r.json()

def gas_post(body):
    body['token'] = TOKEN
    r = requests.post(GAS_URL, data=json.dumps(body), headers={'Content-Type': 'application/json'}, timeout=60)
    print('シートに知らせました:', r.text[:100])

def fetch(url):
    big = re.sub(r'/(x|l|m|s)\.jpg$', '/x.jpg', url)   # もしもの画像は x が一番大きい
    for u in [big, url]:
        try:
            r = requests.get(u, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
            if r.ok and len(r.content) > 2000:
                return Image.open(io.BytesIO(r.content)).convert('RGB')
        except Exception as e:
            print('画像が取れませんでした:', u, e)
    raise RuntimeError('画像が取れません: ' + url)

# 種類ごとの「ちょうどいい縦横比」（高さ÷幅）。ここから外れる写真は、着用写真などの可能性が高い
SHAPE = {'outer': (0.8, 1.6), 'bottom': (1.5, 2.8), 'shoes': (0.5, 1.25)}

def best_cutout(url, part):
    """商品画像1〜6を順に試して、いちばん「商品だけの写真」らしいものを選ぶ。
    URLが /1/ 以外（手で指定した画像）のときは、その画像だけを使う"""
    urls = [url]
    if '/1/' in url and part != 'outer':     # アウターは1枚目（正面）を使う。後ろ姿を拾わないように
        urls = [url.replace('/1/', '/%d/' % n) for n in range(1, 7)]
    lo, hi = SHAPE[part]
    best, best_score = None, -1e9
    for n, u in enumerate(urls):
        try:
            im = coord_lib.cutout(fetch(u))
        except Exception as e:
            continue
        ratio = im.height / max(1, im.width)
        score = -max(0, lo - ratio, ratio - hi) * 10 - n * 1.5   # 別の写真に替えるのは、形がよほど合わないときだけ   # 形が合うほど高く、前の画像ほど少し優先
        print('  %s 画像%d 縦横比%.2f 点数%.2f' % (part, n + 1, ratio, score))
        if score > best_score:
            best, best_score = im, score
        if score > -0.01 and n == 0:
            break      # 1枚目がちょうどいい形なら、それで決まり
    if best is None:
        raise RuntimeError('使える画像がありません: ' + url)
    return best

def short(name):
    """商品名から、リンクに出す短い名前を作る"""
    drop = r'^(放出|レプリカ|デッドストック.*|未使用|新品|ミリタリー.*|軍モノ|軍パン|メンズ|レディース|.*相当|.*サイズ|[0-9].*|X*S|X*L|M|F|【.*|〔.*|\(.*)$'
    name = re.sub(r'[（(【〔\[].*?[）)】〕\]]', ' ', name)   # かっこの中は外す
    words = [w for w in re.split(r'[\s　]+', name) if w and not re.match(drop, w) and w not in ('靴', 'シューズ', 'レプリカ')]
    return ' '.join(words[:4])

def prepare_raw(c):
    """候補の3商品について、商品画像1〜6を取ってきて切り抜き、raw/商品ID/番号.png に保存する。
    組み立ては Claude が写真を見ながら行う（写真のばらつきが大きく、決まりだけでは整わないため）"""
    made = False
    for part in ('outer', 'bottom', 'shoes'):
        pid, url = c[part + 'Id'], c[part + 'Img']
        d = 'raw/%s' % pid
        if os.path.exists(d) and os.listdir(d):
            continue
        os.makedirs(d, exist_ok=True)
        urls = [url.replace('/1/', '/%d/' % n) for n in range(1, 7)] if '/1/' in url else [url]
        for n, u in enumerate(urls, 1):
            try:
                im = fetch(u)
            except Exception:
                continue
            im.save('%s/%d.jpg' % (d, n), quality=90)
            try:
                coord_lib.cutout(im).save('%s/%d.png' % (d, n))
            except Exception as e:
                print('切り抜けませんでした:', u, e)
            made = True
        print('写真を用意しました:', pid)
    return made

def main():
    d = gas_get()
    changed = adopted = False

    # ① 画像待ちの候補 → 写真を用意する（組み立ては Claude）
    for c in d.get('todo', []):
        try:
            changed = prepare_raw(c) or changed
        except Exception as e:
            print('写真を用意できませんでした（行%s）:' % c['row'], e)

    # ② 採用された候補 → coords.json に足して公開
    path = 'static/coords.json'
    data = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'coords': []}
    for c in d.get('adopt', []):
        src = c.get('image', '').replace(REPO_RAW, '')
        if not os.path.exists(src):
            print('候補画像が見つかりません:', src); continue
        no = '%03d' % (max([int(x['id']) for x in data['coords']] + [0]) + 1)
        Image.open(src).save('static/%s.jpg' % no, quality=85)
        data['coords'].append({'id': no, 'title': c['title'], 'comment': c.get('comment', ''),
            'image': SITE + 'coords/%s.jpg' % no,
            'items': [{'id': c['outerId'], 'name': short(c['outerName'])},
                      {'id': c['bottomId'], 'name': short(c['bottomName'])},
                      {'id': c['shoesId'], 'name': short(c['shoesName'])}]})
        c['no'] = no
        changed = adopted = True
        print('公開に追加しました:', no, c['title'])
    if adopted:
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 変更を保存してから、シートに知らせる
    if changed:
        os.system('git config user.name "modi-bot" && git config user.email "modi-bot@users.noreply.github.com"')
        os.system('git add raw candidates static && git commit -m "コーデ画像を更新 [skip ci]" && git push')
    for c in d.get('adopt', []):
        if c.get('no'):
            gas_post({'type': 'coords_pub', 'row': c['row'], 'no': c['no']})
    open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a').write('adopted=%s\n' % ('yes' if adopted else 'no'))

if __name__ == '__main__':
    main()
