"""MoDi Journal：posts/ の記事から、サイト一式（_site/）を作る"""
import datetime, html, json, os, re, shutil, sys
import urllib.request

SITE = 'https://journal.northwood-jp.com'
SHOP = 'https://modi.northwood-jp.com'
JST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(JST).date()
OUT = '_site'


def esc(s):
    return html.escape(str(s), quote=True)


def read_post(path):
    """先頭の --- と --- の間に設定、その下に本文"""
    text = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    meta, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    meta['slug'] = os.path.splitext(os.path.basename(path))[0]
    meta['body'] = body.strip()
    meta['date_obj'] = datetime.date.fromisoformat(meta.get('date', '2000-01-01'))
    meta['items'] = [x.strip() for x in meta.get('items', '').split(',') if x.strip()]
    return meta


_CARD = {}


def product(item_id):
    """商品ページから、写真・商品名・価格を取ってくる（失敗したらNone）"""
    if item_id in _CARD:
        return _CARD[item_id]
    info = None
    try:
        req = urllib.request.Request(SHOP + '/items/' + item_id, headers={'User-Agent': 'Mozilla/5.0'})
        page = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
        meta = lambda p: (re.search(r'<meta[^>]+property="' + re.escape(p) + r'"[^>]+content="([^"]*)"', page) or [None, ''])[1]
        title = html.unescape(meta('og:title')).split(' | ')[0]
        img = meta('og:image')
        price = meta('product:price:amount')
        if not price:
            pm = re.search(r'"price"\s*:\s*"?([\d.]+)', page)
            price = pm.group(1) if pm else ''
        if title and img:
            info = {'title': title, 'img': img, 'price': price, 'url': SHOP + '/items/' + item_id}
    except Exception as e:
        print('商品の取得に失敗:', item_id, e)
    _CARD[item_id] = info
    return info


def card_html(item_id):
    p = product(item_id)
    if not p:
        return '<p><a href="%s/items/%s">商品を見る →</a></p>' % (SHOP, esc(item_id))
    price = ('<span class="p">¥{:,}</span>'.format(int(float(p['price'])))) if p['price'] else ''
    return ('<a class="card" href="%s"><img src="%s" alt="%s" loading="lazy">'
            '<span class="ct"><span class="t">%s</span>%s<span class="b">商品を見る →</span></span></a>'
            % (esc(p['url']), esc(p['img']), esc(p['title']), esc(p['title']), price))


def body_html(body):
    """本文：空行で段落、「## 」で見出し、「- 」で箇条書き、商品のURLだけの行は商品カードに"""
    out = []
    for block in re.split(r'\n\s*\n', body):
        block = block.strip()
        if not block:
            continue
        m = re.fullmatch(r'https?://modi\.northwood-jp\.com/items/(\d+)', block)
        if m:
            out.append(card_html(m.group(1)))
        elif block.startswith('## '):
            out.append('<h2>%s</h2>' % esc(block[3:]))
        elif all(l.startswith('- ') for l in block.splitlines()):
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % esc(l[2:]) for l in block.splitlines()))
        else:
            out.append('<p>%s</p>' % '<br>'.join(esc(l) for l in block.splitlines()))
    return '\n'.join(out)


def layout(title, desc, content, url, image=None):
    og = ('<meta property="og:image" content="%s">' % esc(image)) if image else ''
    return '''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><meta name="description" content="%s">
<meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:url" content="%s">%s
<meta property="og:type" content="article"><meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="%s"><link rel="alternate" type="application/rss+xml" href="/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&family=Noto+Serif+JP:wght@700&display=swap" rel="stylesheet">
<link rel="icon" href="/favicon.ico"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/style.css"></head>
<body><header class="top"><a class="logo" href="/">MoDi <span>JOURNAL</span></a>
<nav><a href="/coords/">COORDINATE</a><a href="%s">ONLINE STORE</a></nav></header>
<main>%s</main>
<footer><p>MILITARY ARCHIVE CURATION STORE ― memento mori &amp; carpe diem.</p>
<p><a href="%s">MoDi ONLINE STORE</a> ・ MoDi is operated by <a href="https://northwood-jp.com">NORTHWOOD</a></p></footer>
</body></html>''' % (esc(title), esc(desc), esc(title), esc(desc), esc(url), og, esc(url), SHOP, content, SHOP)


def summary(body, n=110):
    text = re.sub(r'https?://\S+', '', re.sub(r'^## .*$', '', body, flags=re.M))
    text = re.sub(r'\s+', '', text)
    return text[:n] + ('…' if len(text) > n else '')


def main():
    posts = [read_post(os.path.join('posts', f)) for f in sorted(os.listdir('posts')) if f.endswith('.md')]
    posts = [p for p in posts if p['date_obj'] <= TODAY and p.get('status', 'publish') == 'publish']
    posts.sort(key=lambda p: (p['date_obj'], int(p.get('no') or 0)), reverse=True)
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copy('static/style.css', OUT + '/style.css')
    for f in ['favicon.ico', 'apple-touch-icon.png', 'modi-hakase.svg', 'dr-modi-icon.png']:
        if os.path.exists('static/' + f):
            shutil.copy('static/' + f, OUT + '/' + f)
    if os.path.exists('static/coords.json'):
        shutil.copy('static/coords.json', OUT + '/coords.json')
    os.makedirs(OUT + '/coords', exist_ok=True)
    for f in os.listdir('static'):
        if f.endswith('.jpg'):
            shutil.copy('static/' + f, OUT + '/coords/' + f)
    if os.path.exists('CNAME'):
        shutil.copy('CNAME', OUT + '/CNAME')
    os.makedirs(OUT + '/images', exist_ok=True)

    import header
    for p in posts:
        img_name = p['slug'] + '.png'
        src = os.path.join('images', img_name)
        if not os.path.exists(src):
            os.makedirs('images', exist_ok=True)
            header.make(int(p.get('no', 0)), [p.get('heading', p['title'])], p.get('subtitle', ''), src)
        shutil.copy(src, OUT + '/images/' + img_name)
        p['image'] = SITE + '/images/' + img_name
        p['url'] = SITE + '/' + p['slug'] + '/'
        p['desc'] = p.get('description') or summary(p['body'])

        sources = ('<div class="src"><h3>参考にした資料</h3><p>%s</p></div>' % esc(p['sources'])) if p.get('sources') else ''
        others = [q for q in posts if q is not p][:3]
        more = ''.join('<li><a href="/%s/">%s</a></li>' % (q['slug'], esc(q['title'])) for q in others)
        content = '''<article><img class="hero" src="/images/%s" alt="%s">
<p class="meta">MoDi COLUMN No.%s ・ %s</p><h1>%s</h1>
<div class="body">%s</div>%s
<p class="note">※MoDiの商品は、元ネタとなった軍の服のレプリカ・デッドストックで、各ブランドの商品ではありません。</p>
<div class="more"><h3>あわせて読みたい</h3><ul>%s</ul></div></article>''' % (
            img_name, esc(p['title']), esc(p.get('no', '')), p['date_obj'].strftime('%Y.%m.%d'),
            esc(p['title']), body_html(p['body']), sources, more)
        os.makedirs(OUT + '/' + p['slug'], exist_ok=True)
        open(OUT + '/' + p['slug'] + '/index.html', 'w', encoding='utf-8').write(
            layout(p['title'] + ' | MoDi JOURNAL', p['desc'], content, p['url'], p['image']))

    # 一覧ページ
    cards = ''.join('''<a class="post" href="/%s/"><img src="/images/%s.png" alt="%s" loading="lazy">
<span class="pd">No.%s ・ %s</span><span class="pt">%s</span></a>''' % (
        p['slug'], p['slug'], esc(p['title']), esc(p.get('no', '')), p['date_obj'].strftime('%Y.%m.%d'), esc(p['title']))
        for p in posts)
    intro = '<section class="intro"><img class="hakase" src="/modi-hakase.svg" alt="Dr.MoDi" width="150" height="167"><h1>MoDi JOURNAL</h1><p>各国軍の名作を、確かな資料からひもとく読みもの。<br>時代の記録を、Dr.MoDiが一着ずつ丁寧に解説します。</p><p class="tocoord"><a href="/coords/">Dr.MoDiのコーディネート提案を見る →</a></p></section>'
    open(OUT + '/index.html', 'w', encoding='utf-8').write(
        layout('MoDi JOURNAL | ミリタリーの名作をひもとく読みもの', '各国軍の名作ミリタリーウェアの歴史と見分け方を、確かな資料からひもとくMoDiの読みもの。',
               intro + '<div class="grid">%s</div>' % cards, SITE + '/'))

    # Dr.MoDiのコーデ一覧（新しい順）。?item=商品ID で、その商品を使ったコーデだけに絞れる
    if os.path.exists('static/coords.json'):
        cs = json.load(open('static/coords.json', encoding='utf-8'))['coords'][::-1]
        boxes = ''.join('''<div class="coord" id="c%s" data-items="%s"><img src="/coords/%s.jpg" alt="%s" loading="lazy">
<p class="cn">COORDINATE No.%s</p><h2>%s</h2><p class="cc">%s</p><ul>%s</ul></div>''' % (
            c['id'], ','.join(i['id'] for i in c['items']), c['id'], esc(c['title']), c['id'], esc(c['title']), esc(c.get('comment', '')),
            ''.join('<li><a href="%s/items/%s">%s →</a></li>' % (SHOP, i['id'], esc(i['name'])) for i in c['items']))
            for c in cs)
        head = '''<section class="intro"><img class="hakase" src="/dr-modi-icon.png" alt="Dr.MoDi" width="75" height="96" style="width:75px">
<h1>COORDINATE</h1><p>Dr.MoDiのコーディネート提案。<br>MoDiのアイテムだけで組んだ、%d通りの着こなしです。</p>
<p class="filter" id="filter" hidden>このアイテムを使ったコーデを表示しています ― <a href="/coords/">すべて見る</a></p></section>''' % len(cs)
        script = '''<script>(function(){var m=location.search.match(/item=(\\d+)/);if(!m)return;var n=0,name='';
document.querySelectorAll('.coord').forEach(function(e){if((','+e.dataset.items+',').indexOf(','+m[1]+',')<0){e.style.display='none';return;}n++;
if(!name){var a=e.querySelector('a[href$="/items/'+m[1]+'"]');if(a)name=a.textContent.replace(' →','');}});
if(!n){document.querySelectorAll('.coord').forEach(function(e){e.style.display='';});return;}
var f=document.getElementById('filter');f.hidden=false;f.firstChild.textContent=(name?'「'+name+'」':'このアイテム')+'を使ったコーデ（'+n+'件）を表示しています ― ';
var back=document.createElement('p');back.className='toall';back.innerHTML='<a href="/coords/">Dr.MoDiのコーディネート一覧へ →</a>';
document.querySelector('.coords').insertAdjacentElement('afterend',back);})();</script>'''
        open(OUT + '/coords/index.html', 'w', encoding='utf-8').write(
            layout('Dr.MoDiのコーディネート提案 | MoDi JOURNAL', 'ミリタリーのデッドストックとレプリカだけで組んだ、Dr.MoDiのコーディネート提案。',
                   head + '<div class="coords">%s</div>' % boxes + script, SITE + '/coords/', SITE + '/coords/' + cs[0]['id'] + '.jpg'))

    # トップのスライドショーとInstagram用の一覧（新しい順）
    feed = [{'title': p['title'], 'url': p['url'], 'image': p['image'], 'date': p['date_obj'].isoformat(),
             'no': p.get('no', ''), 'slug': p['slug'], 'summary': p['desc'], 'items': p['items']} for p in posts]
    json.dump({'posts': feed}, open(OUT + '/feed.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # RSSとサイトマップ
    items = ''.join('<item><title>%s</title><link>%s</link><guid>%s</guid><pubDate>%s</pubDate><description>%s</description></item>' % (
        esc(p['title']), p['url'], p['url'], datetime.datetime.combine(p['date_obj'], datetime.time(7, tzinfo=JST)).strftime('%a, %d %b %Y %H:%M:%S +0900'), esc(p['desc']))
        for p in posts)
    open(OUT + '/rss.xml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>MoDi JOURNAL</title><link>%s/</link><description>MoDiの読みもの</description>%s</channel></rss>' % (SITE, items))
    urls = ''.join('<url><loc>%s</loc><lastmod>%s</lastmod></url>' % (p['url'], p['date_obj'].isoformat()) for p in posts)
    open(OUT + '/sitemap.xml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>%s/</loc></url>%s</urlset>' % (SITE, urls))
    open(OUT + '/robots.txt', 'w').write('User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' % SITE)
    print('公開した記事：', len(posts), '本')


if __name__ == '__main__':
    main()
