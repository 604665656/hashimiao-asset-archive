# -*- coding: utf-8 -*-
"""第 2 轮增量合并：把新一轮元宝缓存里的 42 张唯一新图并入档案。

前置：
  yuanbao-asset-rescue/recover.py 提取缓存 -> _index.json
  与档案现有 sha1 做差集 -> _fresh.json（42 条）

分拣依据（2026-11-07 逐格目视核对 全览_1.png / 全览_2.png）：
  42 张全部属于本项目这一轮，无别的对话混入。
  其中编号 2/3/8/10/11 是界面与网页实测截图（过程记录，非美术素材），
  单独放 本轮新增/02_界面与过程记录；其余 37 张放 01_角色设定与三视图。

跑法：python _build/merge_round2.py --fresh <_fresh.json 所在目录>
      加 --dry-run 只预览不落盘。
"""
import argparse
import csv
import json
import os
import shutil

from PIL import Image, ImageDraw, ImageFile, ImageFont

import gallery

ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_JSON = os.path.join(ROOT, '清单', '图片清单.json')
MANIFEST_CSV = os.path.join(ROOT, '清单', '图片清单.csv')
THUMB_DIR = os.path.join(ROOT, '总览', 'thumb')
THUMB_MAX = 420

UI_SHOTS = {2, 3, 8, 10, 11}  # 1-based 编号，对应全览图格号
ROUND = '第2轮·13卷八向新文件'
FIELDS = ['组', '文件', '原缓存ID', '宽', '高', '模式', '字节', '绿占比',
          'sha1', '完整性', '来源', '归属', '轮次', '路径']


def font(size):
    for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def integrity(p):
    if os.path.splitext(p)[1].lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return '非图片'
    try:
        im = Image.open(p)
        im.load()
        return '完整'
    except Exception as e:
        import re
        m = re.search(r'truncated \((\d+) bytes', str(e))
        return '截断(缺%s字节)' % m.group(1) if m else '损坏'


def thumb(src, name):
    os.makedirs(THUMB_DIR, exist_ok=True)
    try:
        im = Image.open(src)
        im = im.convert('RGBA') if im.mode in ('RGBA', 'P', 'LA') else im.convert('RGB')
        if im.mode == 'RGBA':
            bg = Image.new('RGB', im.size, (238, 238, 238))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        im.save(os.path.join(THUMB_DIR, os.path.splitext(name)[0] + '.jpg'), 'JPEG', quality=84)
        return True
    except Exception as e:
        print('  缩略失败', name, e)
        return False


def sheet(rows, title, note, out):
    if not rows:
        return
    cols, cell, pad = 6, 210, 22
    n = len(rows)
    W = cols * cell + pad * 2
    H = ((n + cols - 1) // cols) * (cell + 18) + pad * 2 + 54
    im = Image.new('RGB', (W, H), (24, 26, 30))
    d = ImageDraw.Draw(im)
    d.text((pad, pad), '%s · %d 张 · %s' % (title, n, note), fill=(120, 210, 255), font=font(20))
    for i, m in enumerate(rows):
        r, c = divmod(i, cols)
        x, y = pad + c * cell, pad + 54 + r * (cell + 18)
        th = os.path.join(THUMB_DIR, os.path.splitext(m['文件'])[0] + '.jpg')
        if os.path.exists(th):
            t = Image.open(th)
            t.thumbnail((cell - 10, cell - 10), Image.LANCZOS)
            im.paste(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2))
        d.rectangle([x, y, x + cell - 4, y + cell - 4], outline=(60, 64, 72))
        d.text((x + 4, y + cell - 2), m['文件'][:28], fill=(170, 180, 190), font=font(12))
    im.save(out, optimize=True)
    print('  总览图:', os.path.basename(out), '%dx%d' % (W, H))


def write_manifest(rows):
    json.dump(rows, open(MANIFEST_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(MANIFEST_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for m in rows:
            w.writerow([m.get(k, '') for k in FIELDS])
    print('  清单:', len(rows), '条 ->', os.path.basename(MANIFEST_JSON), '/', os.path.basename(MANIFEST_CSV))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fresh', required=True, help='recover.py 输出目录（含 _fresh.json 与无扩展名原图）')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    fresh = json.load(open(os.path.join(args.fresh, '_fresh.json'), encoding='utf-8'))
    old = json.load(open(MANIFEST_JSON, encoding='utf-8'))
    have = {m['sha1'] for m in old}
    dup = [r for r in fresh if r['sha1'] in have]
    if dup:
        raise SystemExit('中止：%d 张与现有清单重复，请重新做差集' % len(dup))

    # 旧记录补齐新字段
    for m in old:
        m.setdefault('轮次', '第1轮')
        m.setdefault('路径', gallery.path_of(m))

    added = []
    for i, r in enumerate(fresh, 1):
        src = os.path.join(args.fresh, r['file'])
        if not os.path.isfile(src):
            raise SystemExit('缺原图: ' + src)
        grp = ('本轮新增/02_界面与过程记录' if i in UI_SHOTS
               else '本轮新增/01_角色设定与三视图')
        name = 'R2_%03d_%s.%s' % (i, r['file'], r['ext'])
        rel = grp + '/' + name
        dst = os.path.join(ROOT, rel.replace('/', os.sep))
        added.append({
            '组': grp, '文件': name, '原缓存ID': r['file'],
            '宽': r['w'], '高': r['h'], '模式': r['mode'],
            '字节': r['size'], '绿占比': r.get('green', ''),
            'sha1': r['sha1'], '完整性': '', '来源': '元宝 App 缓存（第2轮）',
            '归属': '本项目', '轮次': ROUND, '路径': rel,
        })
        if args.dry_run:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        added[-1]['完整性'] = integrity(dst)
        thumb(dst, name)

    a_art = [m for m in added if m['组'].endswith('01_角色设定与三视图')]
    a_ui = [m for m in added if m['组'].endswith('02_界面与过程记录')]
    print('新增 %d 张：角色设定 %d / 界面记录 %d，合计 %.1f MB'
          % (len(added), len(a_art), len(a_ui), sum(m['字节'] for m in added) / 1048576))
    if args.dry_run:
        print('dry-run，未落盘')
        return

    sheet(a_art, '本轮新增 · 角色设定与三视图', '第13卷八向新文件',
          os.path.join(ROOT, '总览', '总览_本轮新增_角色设定.png'))
    sheet(a_ui, '本轮新增 · 界面与过程记录', '对话/网页实测截图',
          os.path.join(ROOT, '总览', '总览_本轮新增_界面记录.png'))

    rows = old + added
    write_manifest(rows)
    gallery.build(rows)

    mine = [m for m in rows if m['归属'] == '本项目']
    print('\n档案合计 %d 张 / %.1f MB（本项目 %d + 其他对话 %d）'
          % (len(rows), sum(m['字节'] for m in rows) / 1048576,
             len(mine), len(rows) - len(mine)))


if __name__ == '__main__':
    main()
