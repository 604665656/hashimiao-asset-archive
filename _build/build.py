# -*- coding: utf-8 -*-
"""把元宝 App 缓存里的图片 + 桌面散件，整理成一个可浏览的素材档案。

输入：
  _yb_stage/          已从 EBWebView Cache_Data 提取的图片
  /Desktop 散件        元宝下载但未进缓存的原图
输出：本目录（档案仓库根）

跑法：python _build/build.py
"""
import hashlib
import json
import os
import re
import shutil

from PIL import Image, ImageDraw, ImageFile, ImageFont

# 缓存里有几条记录尾部被截断（缺 13~54 字节），实际画面完整，允许读入
ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(os.path.dirname(ROOT), '_yb_stage')
DESKTOP = r'C:/Users/60466/Desktop'

BUCKETS = [
    ('01_绿幕与白模', '绿幕/拼板', '纯绿背景上的生成结果与白模拼板，可直接做去背输入'),
    ('02_生成稿_1328x1776', '1328x1776 生成稿', '元宝默认画布 1328×1776 的整张生成稿'),
    ('03_大幅', '大幅(>=1000x600)', '尺寸 ≥1000×600 的其他大图，含拼板与成图'),
    ('04_其他', '其他', '缩略图、小图、界面截图等'),
]

DESKTOP_FILES = [
    '00_原始RGB_20261105232049.png',
    '04_银时_设定卡_20261105231935.png',
    'L03_嘴与舌_20261105232056.png',
    'L04_左眼_20261105232104.png',
    '原型_正面手脚规范_20261105232003.png',
    '合成预览_20261105235437.png',
    '合成预览_20261105235451.png',
    '神乐_20261105235427.png',
    '配饰_假发与衣身_20261105235443.png',
    'README_动作与抠图_诊断修复_20261105232012.md',
]

THUMB_MAX = 420


def sha1(p):
    return hashlib.sha1(open(p, 'rb').read()).hexdigest()


def integrity(p):
    """严格校验：能完整解码返回「完整」，否则返回截断说明。非图片不检测。"""
    if os.path.splitext(p)[1].lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return '非图片'
    try:
        im = Image.open(p)
        im.load()
        return '完整'
    except Exception as e:
        m = re.search(r'truncated \((\d+) bytes', str(e))
        return '截断(缺%s字节)' % m.group(1) if m else '损坏'


def load_any(p):
    """无视截断标记，能读就返回图像对象，读完关掉标记。"""
    try:
        return Image.open(p)
    except Exception:
        return None


def integrity(p):
    """严格校验：能完整解码返回「完整」，否则返回截断说明。非图片不检测。"""
    if os.path.splitext(p)[1].lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return '非图片'
    try:
        im = Image.open(p)
        im.load()
        return '完整'
    except Exception as e:
        m = re.search(r'truncated \((\d+) bytes', str(e))
        return '截断(缺%s字节)' % m.group(1) if m else '损坏'


def load_any(p):
    """无视截断标记，能读就返回图像对象，读完关掉标记。"""
    try:
        return Image.open(p)
    except Exception:
        return None


def font(size):
    for f in ('C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    rows = json.load(open(os.path.join(STAGE, '_index.json'), encoding='utf-8'))

    # 桌面散件去重比对：已在缓存里的不再收
    cache_sha = {r['sha1'] for r in rows}
    extra = []
    for f in DESKTOP_FILES:
        p = os.path.join(DESKTOP, f)
        if not os.path.isfile(p):
            print('  桌面缺件:', f)
            continue
        extra.append((p, f, sha1(p)))

    # 清掉上一次生成的图片目录，保留 _build
    for name, _, _ in BUCKETS:
        d = os.path.join(ROOT, '元宝缓存', name)
        if os.path.isdir(d):
            shutil.rmtree(d)
    for d in ('桌面散件', '总览'):
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    os.makedirs(os.path.join(ROOT, '总览', 'thumb'), exist_ok=True)

    manifest = []
    for bi, (dirname, key, note) in enumerate(BUCKETS, 1):
        items = [r for r in rows if r.get('bucket') == key]
        # 排序：绿占比高的在前，再按体积
        items.sort(key=lambda r: (-(r.get('green') or 0), -r['size']))
        out = os.path.join(ROOT, '元宝缓存', dirname)
        os.makedirs(out, exist_ok=True)
        for i, r in enumerate(items, 1):
            src = os.path.join(STAGE, r['file'])
            base = os.path.splitext(r['file'])[0]
            newname = '%03d_%s.%s' % (i, base, r['ext'])
            dst = os.path.join(out, newname)
            shutil.copy2(src, dst)
            # 缩略图
            try:
                im = Image.open(dst)
                im = im.convert('RGBA') if im.mode in ('RGBA', 'P', 'LA') else im.convert('RGB')
                if im.mode == 'RGBA':
                    bg = Image.new('RGB', im.size, (238, 238, 238))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
                im.save(os.path.join(ROOT, '总览', 'thumb', newname.rsplit('.', 1)[0] + '.jpg'),
                        'JPEG', quality=84)
            except Exception as e:
                print('  缩略失败', newname, e)
            manifest.append({
                '组': dirname, '文件': newname, '原缓存ID': base,
                '宽': r['w'], '高': r['h'], '模式': r['mode'],
                '字节': r['size'], '绿占比': r.get('green'),
                'sha1': r['sha1'], '来源': '元宝 App 缓存',
                '完整性': integrity(dst),
            })

    # 桌面散件
    ddir = os.path.join(ROOT, '桌面散件')
    os.makedirs(ddir, exist_ok=True)
    for p, f, h in extra:
        if h in cache_sha:
            print('  跳过（缓存已有）:', f)
            continue
        shutil.copy2(p, os.path.join(ddir, f))
        if f.lower().endswith(('.png', '.jpg')):
            try:
                im = Image.open(p).convert('RGB')
                im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
                im.save(os.path.join(ROOT, '总览', 'thumb', os.path.splitext(f)[0] + '.jpg'),
                        'JPEG', quality=84)
            except Exception:
                pass
        manifest.append({'组': '桌面散件', '文件': f, '原缓存ID': '', '宽': '', '高': '',
                         '模式': '', '字节': os.path.getsize(p), '绿占比': '',
                         'sha1': h, '来源': '桌面', '完整性': integrity(p)})

    # 清单
    os.makedirs(os.path.join(ROOT, '清单'), exist_ok=True)
    json.dump(manifest, open(os.path.join(ROOT, '清单', '图片清单.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, '清单', '图片清单.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        f.write('组,文件,原缓存ID,宽,高,模式,字节,绿占比,sha1,完整性,来源\n')
        for m in manifest:
            f.write(','.join(str(m.get(k, '')) for k in
                             ('组', '文件', '原缓存ID', '宽', '高', '模式', '字节', '绿占比', 'sha1', '完整性', '来源')) + '\n')

    # 分组总览图
    for dirname, key, note in BUCKETS:
        items = [m for m in manifest if m['组'] == dirname]
        if not items:
            continue
        cols = 8
        cell = 210
        pad = 22
        rowsn = (len(items) + cols - 1) // cols
        W = cols * cell + pad * 2
        H = rowsn * (cell + 18) + pad * 2 + 54
        sheet = Image.new('RGB', (W, H), (24, 26, 30))
        d = ImageDraw.Draw(sheet)
        title = '%s · %d 张 · %s' % (dirname, len(items), note)
        d.text((pad, pad), title, fill=(120, 210, 255), font=font(20))
        fl = font(12)
        for i, m in enumerate(items):
            r, c = divmod(i, cols)
            x = pad + c * cell
            y = pad + 54 + r * (cell + 18)
            th = os.path.join(ROOT, '总览', 'thumb', os.path.splitext(m['文件'])[0] + '.jpg')
            if os.path.exists(th):
                im = Image.open(th)
                im.thumbnail((cell - 10, cell - 10), Image.LANCZOS)
                sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
            d.rectangle([x, y, x + cell - 4, y + cell - 4], outline=(60, 64, 72))
            d.text((x + 4, y + cell - 2), m['文件'][:30], fill=(170, 180, 190), font=fl)
        out = os.path.join(ROOT, '总览', '总览_%s.png' % dirname)
        sheet.save(out, optimize=True)
        print('  总览图:', os.path.basename(out), '%dx%d' % (W, H))

    # 画廊
    build_gallery(manifest)

    total = sum(m['字节'] for m in manifest)
    print('\n合计 %d 个文件 / %.1f MB' % (len(manifest), total / 1048576))
    for dirname, _, _ in BUCKETS:
        n = [m for m in manifest if m['组'] == dirname]
        print('  %-22s %3d' % (dirname, len(n)))
    print('  %-22s %3d' % ('桌面散件', len([m for m in manifest if m['组'] == '桌面散件'])))


def build_gallery(manifest):
    groups = []
    for dirname, _, note in BUCKETS:
        groups.append((dirname, note))
    groups.append(('桌面散件', '从元宝下载到桌面、但没进缓存的散件'))

    parts = ['''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>哈士喵素材档案 · 元宝全量</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f1115;color:#e6e9ee;font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
header{padding:22px 26px;border-bottom:1px solid #23272f}
h1{font-size:19px;font-weight:600}
.sub{color:#98a2b3;font-size:12.5px;margin-top:6px}
.sub b{color:#5cc8ff;font-weight:600}
nav{position:sticky;top:0;z-index:5;display:flex;gap:6px;flex-wrap:wrap;
 padding:10px 26px;background:#14171c;border-bottom:1px solid #23272f}
nav a{color:#c9d3e0;text-decoration:none;font-size:12.5px;padding:5px 11px;
 border:1px solid #2c3340;border-radius:999px}
nav a:hover{border-color:#5cc8ff;color:#5cc8ff}
main{padding:8px 26px 60px}
section{margin-top:26px}
h2{font-size:15px;font-weight:600;color:#8fd4ff;margin-bottom:3px}
.hint{color:#8b95a5;font-size:12px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.card{background:#171a20;border:1px solid #242a33;border-radius:9px;overflow:hidden}
.card:hover{border-color:#5cc8ff}
.card a{display:block;text-decoration:none}
.card img{width:100%;height:150px;object-fit:contain;background:#1d2128;display:block}
.meta{padding:5px 7px;font-size:10.5px;color:#8b95a5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
footer{padding:26px;color:#6b7482;font-size:12px;border-top:1px solid #23272f}
</style></head><body>
<header><h1>哈士喵素材档案 · 元宝全量</h1>
<div class="sub">从元宝 App 本地缓存恢复 <b>''' + str(len([m for m in manifest if m['来源'] == '元宝 App 缓存'])) + '''</b> 张图片，加上桌面散件 <b>''' + str(len([m for m in manifest if m['来源'] == '桌面'])) + '''</b> 个。点图看原图。</div></header>
<nav>''']
    for dirname, _ in groups:
        n = len([m for m in manifest if m['组'] == dirname])
        if n:
            parts.append('<a href="#%s">%s（%d）</a>' % (dirname, dirname, n))
    parts.append('</nav><main>')
    for dirname, note in groups:
        items = [m for m in manifest if m['组'] == dirname]
        if not items:
            continue
        parts.append('<section id="%s"><h2>%s</h2><div class="hint">%s</div><div class="grid">'
                     % (dirname, dirname, note))
        for m in items:
            if dirname == '桌面散件':
                rel = '桌面散件/' + m['文件']
            else:
                rel = '元宝缓存/' + dirname + '/' + m['文件']
            thumb = '总览/thumb/' + os.path.splitext(m['文件'])[0] + '.jpg'
            dims = ('%s×%s' % (m['宽'], m['高'])) if m['宽'] else ''
            kb = '%.0fKB' % (m['字节'] / 1024)
            parts.append('<div class="card"><a href="%s" target="_blank"><img loading="lazy" src="%s" alt="%s">'
                         '<div class="meta">%s %s %s</div></a></div>'
                         % (rel, thumb, m['文件'], m['文件'][:14], dims, kb))
        parts.append('</div></section>')
    parts.append('''</main>
<footer>缩略图在本页，点开是原图。完整字段见 <a href="清单/图片清单.csv" style="color:#5cc8ff">清单/图片清单.csv</a>。
<br>来源：元宝 App（WebView2 缓存）2026-11-07 导出。对话正文未缓存，无法恢复。</footer>
</body></html>''')
    p = os.path.join(ROOT, 'index.html')
    open(p, 'w', encoding='utf-8').write(''.join(parts))
    print('  画廊:', p)


if __name__ == '__main__':
    main()
