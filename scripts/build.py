# -*- coding: utf-8 -*-
"""望京博格市场温度计 · 构建脚本（通用版，随 skill 分发）

取数见 scripts/fetch.py，两条路：
  1) 快照    get_index_price_indicators   一次传 44 个代码，拿 chg/ytd/close/pe(核对)
  2) 分位数  get_index_fundamentals       44 条单日问句并行（铁律：一指数一日期）
结果填进 snapshot_<日期>.json，本脚本只读 targets + snapshot，不再重复取数。

用法（在任意项目目录下）:
    python scripts/build.py <snapshot.json路径> [上一交易日] [--out 输出目录]
输出目录缺省为当前工作目录；HTML 命名 市场温度计-<日期>.html。
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import runtime
import targets

NODE = runtime.find_node()
if not NODE:
    sys.exit("[build] " + runtime.NODE_HINT)

ap = argparse.ArgumentParser()
ap.add_argument("snapshot")
ap.add_argument("prev", nargs="?")
ap.add_argument("--out", default=os.getcwd())
args = ap.parse_args()

def _prev_default(date):
    # 无上一交易日参数时，从历史库取「日期早于 DATE 的最后一个点」
    hist = json.load(open(os.path.join(SKILL, "data/temperature-history.json"), encoding="utf-8"))
    for p in reversed(hist["series"]["a"]):
        if p[0] < date:
            return p[0]
    return date

snap = json.load(open(args.snapshot, encoding="utf-8"))
DATE = snap["date"]
S = snap["snapshot"]
PREV = args.prev or _prev_default(DATE)

def fill(entries, g):
    out = []
    for n, code, etf, base in entries:
        d = S[code]
        empty = [k for k in ("chg", "ytd", "close", "pe", "t") if d.get(k) is None]
        if empty:
            sys.exit(
                f"[build] {code}（{n}）缺字段 {empty}：snapshot 里是空值，取数没做成。\n"
                "  本 skill 不自带数据，必须靠金融数据 MCP 取「指数 PE(TTM) 近十年分位数」：\n"
                "    · 路线 A：Wind 指数数据 MCP（get_index_price_indicators / get_index_fundamentals）\n"
                "    · 路线 B：东方财富妙想 MCP（mx-ds-mcp，https://mxapi.eastmoney.com/mxds/mcp）\n"
                "  安装方式见 references/mcp-setup.md，装完跑 python scripts/check_env.py 自检，\n"
                "  再重新取数。不要用编造的数字绕过这一步。"
            )
        out.append(dict(n=n, g=g, chg=d["chg"], ytd=d["ytd"], close=d["close"],
                        pe=d["pe"], t=d["t"], etf=etf, base=base))
    return out

A_RAW = fill(targets.INDUSTRIES, "行业") + fill(targets.WIDE, "宽基")
H_RAW = fill(targets.HK, "港股")

def row_a(r):
    s924 = (r["close"] / r["base"] - 1) * 100
    return (f"  {{ n:'{r['n']}',{' ' * max(0, 22 - len(r['n'].encode('gbk', 'ignore')))}g:'{r['g']}', "
            f"chg:{r['chg']:5.2f}, ytd:{r['ytd']:6.2f}, s924:{s924:6.2f}, pe:{r['pe']:5.2f}, t:{r['t']:7.4f}, etf:'{r['etf']}' }},")

def row_h(r):
    s924 = (r["close"] / r["base"] - 1) * 100
    return (f"  {{ n:'{r['n']}',{' ' * max(0, 14 - len(r['n'].encode('gbk', 'ignore')))}chg:{r['chg']:5.2f}, "
            f"ytd:{r['ytd']:6.2f}, s924:{s924:6.2f}, pe:{r['pe']:6.2f}, t:{r['t']:7.4f}, etf:'{r['etf']}' }},")

avgA = sum(r["t"] for r in A_RAW) / len(A_RAW)
avgH = sum(r["t"] for r in H_RAW) / len(H_RAW)
print(f"A股 温度 = {avgA:.4f}  ({len(A_RAW)} 只)", file=sys.stderr)
print(f"港股 温度 = {avgH:.4f}  ({len(H_RAW)} 只)", file=sys.stderr)

# ── 落历史库（只补新点，同日重复写入覆盖）──
hist_path = os.path.join(SKILL, "data/temperature-history.json")
for series, val, n in (("a", avgA, len(A_RAW)), ("hk", avgH, len(H_RAW))):
    subprocess.run([NODE, "scripts/history.js", "add", "data/temperature-history.json",
                    series, DATE, f"{val:.2f}", str(n)], cwd=SKILL, check=True, stdout=sys.stdout)
hist = json.load(open(hist_path, encoding="utf-8"))

def js_series(pts, with_n):
    if with_n:
        items = [f"['{p[0]}', {p[1]:.2f}, {p[2] if len(p) > 2 else 7}]" for p in pts]
    else:
        items = [f"['{p[0]}', {p[1]:.2f}]" for p in pts]
    return "\n".join("  " + ", ".join(items[i:i + 4]) + "," for i in range(0, len(items), 4))

TH_JS = "const TH = [\n" + js_series(hist["series"]["a"], False) + "\n];"
THH_JS = "const THH = [\n" + js_series(hist["series"]["hk"], True) + "\n];"
n_a, n_h = len(hist["series"]["a"]), len(hist["series"]["hk"])

tpl = open(os.path.join(SKILL, "assets/page_template.html"), encoding="utf-8").read()
html = tpl

a_rows = []
for i, r in enumerate(A_RAW):
    if r["g"] == "宽基" and A_RAW[i - 1]["g"] == "行业":
        a_rows.append("  // ── 6 个宽基 ──")
    a_rows.append(row_a(r))
a_block = "const A = [\n  // ── 31 个申万一级行业 ──\n" + "\n".join(a_rows) + "\n];"
html = re.sub(r"const A = \[.*?\n\];", lambda m: a_block, html, flags=re.S)

h_block = "const H = [\n" + "\n".join(row_h(r) for r in H_RAW) + "\n];"
html = re.sub(r"const H = \[.*?\n\];", lambda m: h_block, html, flags=re.S)

html = re.sub(r"const TH = \[.*?\n\];", lambda m: TH_JS, html, flags=re.S)
html = re.sub(r"const THH = \[.*?\n\];", lambda m: THH_JS, html, flags=re.S)

prev_a = [p[1] for p in hist["series"]["a"] if p[0] == PREV][0]
prev_h = [p[1] for p in hist["series"]["hk"] if p[0] == PREV][0]
html = html.replace("/* ───────── 卡片 ───────── */",
                    f"/* 上一交易日（{PREV}）两组合的等权温度，来自历史库 */\n"
                    f"const PAVG = {{ a: {prev_a:.2f}, h: {prev_h:.2f} }};\n\n/* ───────── 卡片 ───────── */")
html = html.replace("  const p = data.reduce((s, x) => s + x.prev, 0) / data.length;\n", "  const p = PAVG[cls];\n")
html = html.replace("   prev 上一交易日温度（用于计算日变化）                             */",
                    "   prev 字段已移除；卡片的「较上一交易日」改用 PAVG（历史库聚合值）  */")

reps = [
 ("<title>望京博格 · 市场温度计 | 2026-10-16</title>", f"<title>望京博格 · 市场温度计 | {DATE}</title>"),
 ("<b>2026 / 10 / 16</b>", f"<b>{DATE[:4]} / {DATE[5:7]} / {DATE[8:10]}</b>"),
 ("两图共用 48 个采样点（2016Q4–2025Q3 按季末，2025Q4 起按月，末点 2026-10-16）",
  f"A股 {n_a} 个、港股 {n_h} 个采样点（2016Q4–2025Q3 按季末，2025Q4 起按月，末点 {DATE} 收盘）"),
 ("2026-10-16 收 3605.58", f"{DATE} 收 {S['931024.CSI']['close']:.2f}"),
 ("「924 以来」= 2026-10-16 收盘", f"「924 以来」= {DATE} 收盘"),
 ("最后一点为 2026-10-16。", f"最后一点为 {DATE}。"),
]
for old, new in reps:
    assert old in html, old
    html = html.replace(old, new)

out_html = os.path.join(args.out, f"市场温度计-{DATE}.html")
open(out_html, "w", encoding="utf-8").write(html)
print(out_html)
