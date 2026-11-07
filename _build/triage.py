# -*- coding: utf-8 -*-
"""出逐格审查图：6 列 × 6 行，每格带大编号，供人工判定相关性。"""
import json
import os

from PIL import Image, ImageDraw, ImageFile, ImageFont

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_build', 'triage')
os.makedirs(OUT, exist_ok=True)

COLS, ROWS, CELL = 6, 6, 262
PER = COLS * ROWS


def font(size):
    for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/arialbd.ttf'):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def sheet(items, title, dst):
    rows = (len(items) + COLS - 1) // COLS
    W, H = COLS * CELL + 16, rows * (CELL + 16) + 50
    im = Image.new('RGB', (W, H), (18, 19, 22))
    d = ImageDraw.Draw(im)
    d.text((10, 12), title, fill=(120, 210, 255), font=font(20))
    for i, (num, path) in enumerate(items):
        r, c = divmod(i, COLS)
        x, y = 8 + c * CELL, 44 + r * (CELL + 16)
        try:
            t = Image.open(path)
            t = t.convert('RGB')
            t.thumbnail((CELL - 6, CELL - 6), Image.LANCZOS)
            im.paste(t, (x + (CELL - t.width) // 2, y + (CELL - t.height) // 2))
        except Exception:
            pass
        d.rectangle([x, y, x + CELL, y + CELL], outline=(58, 62, 70))
        d.rectangle([x, y, x + 30, y + 18], fill=(0, 0, 0))
        d.text((x + 4, y + 1), str(num), fill=(255, 220, 60), font=font(15))
    im.save(dst, optimize=True)
    print(' ', os.path.basename(dst), '%dx%d' % (W, H), len(items), '格')


def main():
    m = json.load(open(os.path.join(ROOT, '清单', '图片清单.json'), encoding='utf-8'))
    for grp in ('02_生成稿_1328x1776', '03_大幅', '04_其他'):
        items = [x for x in m if x['组'] == grp]
        for page in range(0, len(items), PER):
            chunk = items[page:page + PER]
            lst = []
            for x in chunk:
                n = int(x['文件'].split('_')[0])
                p = os.path.join(ROOT, '总览', 'thumb', os.path.splitext(x['文件'])[0] + '.jpg')
                if not os.path.exists(p):
                    p = os.path.join(ROOT, '元宝缓存', grp, x['文件'])
                lst.append((n, p))
            sheet(lst, '%s  第 %d 页' % (grp, page // PER + 1),
                  os.path.join(OUT, '%s_%d.png' % (grp[:2], page // PER + 1)))


if __name__ == '__main__':
    main()
