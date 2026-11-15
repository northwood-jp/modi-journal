"""MoDi Journal：スプレッドシートの「Journal下書き」から、OKになった記事を取ってきて posts/ に書く"""
import json, os
import requests

GAS_URL = os.environ.get('GAS_URL', '')
GAS_TOKEN = os.environ.get('GAS_TOKEN', '')


def main():
    if not GAS_URL:
        print('GAS_URL がないので、取り込みは飛ばします')
        return
    r = requests.get(GAS_URL, params={'mode': 'journal', 'token': GAS_TOKEN}, timeout=60)
    drafts = r.json().get('drafts', [])
    print('取り込む記事：', len(drafts), '本')
    done = []
    for d in drafts:
        slug = d['slug']
        lines = ['---',
                 'title: ' + d['title'],
                 'date: ' + d['date'],
                 'no: ' + str(d.get('no', '')),
                 'heading: ' + (d.get('heading') or ''),
                 'subtitle: ' + (d.get('subtitle') or ''),
                 'items: ' + (d.get('items') or ''),
                 'sources: ' + (d.get('sources') or ''),
                 '---',
                 d['body'].strip(), '']
        os.makedirs('posts', exist_ok=True)
        open(os.path.join('posts', slug + '.md'), 'w', encoding='utf-8').write('\n'.join(lines))
        done.append({'row': d['row'], 'date': d['date']})
        print('取り込み：', slug)
    json.dump(done, open('imported.json', 'w'), ensure_ascii=False)


if __name__ == '__main__':
    main()
