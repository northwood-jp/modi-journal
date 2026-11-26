"""raw_fetch.txt の「商品ID 画像URL」ごとに、写真1〜6を raw/商品ID/ に取ってくる（コーデ組み立て用）"""
import traceback
import os
os.environ.setdefault("GAS_URL", ""); os.environ.setdefault("GAS_TOKEN", "")
import coords
for line in open('raw_fetch.txt'):
    p = line.split()
    if len(p) != 2:
        continue
    try:
        coords.prepare_raw({'hatId': p[0], 'hatImg': p[1]})
    except Exception:
        traceback.print_exc()
