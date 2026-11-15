"""MoDi Journal：取り込んだ記事の状態を、スプレッドシートに書き戻す"""
import json, os
import requests

if os.environ.get('GAS_URL') and os.path.exists('imported.json'):
    rows = json.load(open('imported.json'))
    if rows:
        r = requests.post(os.environ['GAS_URL'],
                          data=json.dumps({'token': os.environ['GAS_TOKEN'], 'type': 'journal', 'rows': rows}),
                          timeout=60)
        print('書き戻し：', len(rows), '本', r.status_code)
