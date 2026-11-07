# -*- coding: utf-8 -*-
"""清单驱动的静态图廊生成器。

不再依赖首轮的 stage 目录，只读 清单/图片清单.json：
  - 每条记录的「路径」字段决定原图位置
  - 每条记录的「归属」决定进主区还是「其他对话」区
  - 每条记录的「组」决定分区，按 SECTIONS 里的顺序输出

跑法：python _build/gallery.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, '清单', '图片清单.json')

# 主区分组顺序；未列出的组按名称排在后面
SECTIONS = [
    ('01_绿幕与白模', '纯绿背景上的生成结果与白模拼板，可直接做去背输入'),
    ('02_生成稿_1328x1776', '元宝默认画布 1328×1776 的整张生成稿'),
    ('03_大幅', '尺寸 ≥1000×600 的其他大图，含拼板与成图'),
    ('04_其他', '缩略图、小图、界面截图等'),
    ('桌面散件', '从元宝下载到桌面、但没进缓存的散件'),
    ('本轮新增/01_角色设定与三视图',
     '第 2 轮（13 卷总包 · 第 13 卷八向新文件）：角色三视图、设定稿、立绘、标识印章'),
    ('本轮新增/02_界面与过程记录',
     '第 2 轮的对话/网页实测截图，不是美术素材，但属于本项目的过程记录，完整保留'),
]


def path_of(m):
    """兼容首轮旧记录：没有「路径」字段时按组与归属推导。"""
    if m.get('路径'):
        return m['路径']
    g = m['组']
    if m.get('归属') != '本项目':
        return '其他对话/' + g + '/' + m['文件']
    if g == '桌面散件':
        return '桌面散件/' + m['文件']
    if g.startswith('本轮新增/'):
        return g + '/' + m['文件']
    return '元宝缓存/' + g + '/' + m['文件']


def build(manifest):
    mine = [m for m in manifest if m.get('归属') == '本项目']
    other = [m for m in manifest if m.get('归属') != '本项目']

    # 校验：清单里的每条都要能在磁盘上找到原图
    missing = [path_of(m) for m in manifest
               if not os.path.isfile(os.path.join(ROOT, path_of(m).replace('/', os.sep)))]
    if missing:
        print('  警告：清单有 %d 条找不到原图，前 5 条：' % len(missing))
        for p in missing[:5]:
            print('   ', p)

    known = {s[0] for s in SECTIONS}
    extra_groups = sorted({m['组'] for m in mine if m['组'] not in known})
    sections = list(SECTIONS) + [(g, '自动归组') for g in extra_groups]

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
<div class="sub">从元宝 App 本地缓存恢复本项目 <b>''' + str(len(mine)) + '''</b> 张，点图看原图。
其中 <b>''' + str(len([m for m in mine if '本轮新增' in m['组']])) + '''</b> 张来自第 2 轮（八向 / 角色三视图新文件）。
另有 <b>''' + str(len(other)) + '''</b> 张混进来的其他对话图片，已挪到页尾单独存档。</div></header>
<nav>''']

    nav = []
    for g, note in sections:
        n = len([m for m in mine if m['组'] == g])
        if n:
            nav.append('<a href="#%s">%s（%d）</a>' % (g, g.split('/')[-1], n))
    if other:
        nav.append('<a href="#其他对话">其他对话（%d）</a>' % len(other))
    parts.append(''.join(nav))
    parts.append('</nav><main>')

    for g, note in sections:
        items = [m for m in mine if m['组'] == g]
        if not items:
            continue
        parts.append('<section id="%s"><h2>%s</h2><div class="hint">%s · 共 %d 张</div><div class="grid">'
                     % (g, g, note, len(items)))
        for m in items:
            rel = path_of(m)
            thumb = '总览/thumb/' + os.path.splitext(m['文件'])[0] + '.jpg'
            dims = ('%s×%s' % (m['宽'], m['高'])) if m.get('宽') else ''
            kb = '%.0fKB' % (m['字节'] / 1024)
            parts.append('<div class="card"><a href="%s" target="_blank"><img loading="lazy" src="%s" alt="%s">'
                         '<div class="meta">%s %s %s</div></a></div>'
                         % (rel, thumb, m['文件'], m['文件'][:16], dims, kb))
        parts.append('</div></section>')

    if other:
        parts.append('<section id="其他对话"><h2>其他对话 · 单独存档</h2>'
                     '<div class="hint">同一个元宝账号下别的对话的图片，混在缓存里被一起捞出来的。'
                     '不算本项目素材，但完整保留不删，默认展开供查。共 %d 张。</div>'
                     '<div class="grid">' % len(other))
        for m in other:
            rel = path_of(m)
            thumb = '总览/thumb/' + os.path.splitext(m['文件'])[0] + '.jpg'
            parts.append('<div class="card"><a href="%s" target="_blank"><img loading="lazy" src="%s" alt="%s">'
                         '<div class="meta">%s %s</div></a></div>'
                         % (rel, thumb, m['文件'], m['文件'][:16], '%.0fKB' % (m['字节'] / 1024)))
        parts.append('</div></section>')

    parts.append('''</main>
<footer>缩略图在本页，点开是原图。完整字段（含轮次、归属）见 <a href="清单/图片清单.csv" style="color:#5cc8ff">清单/图片清单.csv</a>。
<br>来源：元宝 App（WebView2 缓存）2026-11-07 两轮导出。对话正文未缓存，无法恢复。</footer>
</body></html>''')
    p = os.path.join(ROOT, 'index.html')
    open(p, 'w', encoding='utf-8').write(''.join(parts))
    print('  画廊:', p, os.path.getsize(p), '字节')
    print('  主区 %d 张 / 其他对话 %d 张 / 分区 %d 个'
          % (len(mine), len(other), len([1 for g, _ in sections if any(m['组'] == g for m in mine)])))


if __name__ == '__main__':
    build(json.load(open(MANIFEST, encoding='utf-8')))
