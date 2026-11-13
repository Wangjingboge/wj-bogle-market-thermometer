# -*- coding: utf-8 -*-
"""环境自检：跑一次，确认这个 skill 在本机能用。

检查项：
  1) 运行环境（Python 版本、node、playwright-core、浏览器，见 scripts/runtime.py）
  2) 必需文件是否齐全
  3) 标的清单：56 个（A股 37 + 港股 7 + 美股 12）、代码不重复、ETF 格式、924 基准价为正
  4) SKILL.md「标的清单」表 与 scripts/targets.py 是否一致（写死两处，最怕改一处忘另一处）
  5) 历史库 JSON 结构与单调性；最近一份 snapshot 的等权均值是否等于历史库末点（硬规则 7）
  6) 明细库 data/market-data.json：日期键、代码归属、覆盖度、末点=等权均值
  7) 模板占位符是否还在（build.py 靠它注入数据）

用法：
    python scripts/check_env.py

退出码：0 全通过（可能有 WARN）；1 有 FAIL。

注意：MCP 是否已连接**无法用脚本检测**，只能人工确认，最后会打印一份核对清单。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import runtime  # noqa: E402  同目录的运行时探测模块

FAIL = []
WARN = []
OK = []


def ok(msg):
    OK.append(msg)


def warn(msg):
    WARN.append(msg)


def fail(msg):
    FAIL.append(msg)


def check_runtime():
    if sys.version_info < (3, 8):
        fail("Python 版本过低：%s，需要 >= 3.8" % sys.version.split()[0])
    else:
        ok("Python %s" % sys.version.split()[0])

    try:
        import targets  # noqa: F401
        ok("scripts/targets.py 可导入")
    except Exception as e:  # pragma: no cover
        fail("scripts/targets.py 导入失败：%s" % e)
        return None

    node = runtime.find_node()
    if node:
        ok("node 可执行文件：%s" % node)
    else:
        warn("未找到 node（写历史库、导出长图要用）：\n    " + runtime.NODE_HINT.replace("\n", "\n    "))
    return targets


def check_files():
    need = [
        "SKILL.md",
        "assets/page_template.html",
        "references/data-sourcing.md",
        "references/mcp-setup.md",
        "references/rendering.md",
        "references/export.md",
        "data/temperature-history.json",
        "data/us-history.json",
        "scripts/targets.py",
        "scripts/runtime.py",
        "scripts/fetch.py",
        "scripts/update.py",
        "scripts/build.py",
        "scripts/history.js",
        "scripts/export_long.js",
    ]
    missing = [p for p in need if not os.path.exists(os.path.join(SKILL, p))]
    if missing:
        fail("缺少文件：%s" % ", ".join(missing))
    else:
        ok("必需文件齐全（%d 个）" % len(need))

    # 导出长图依赖
    mods = runtime.find_node_modules()
    if mods:
        ok("playwright-core 依赖目录：%s" % mods)
    else:
        warn("未找到 playwright-core（导出长图要用）：\n    "
             + runtime.NODE_MODULES_HINT.replace("\n", "\n    "))

    chrome = runtime.find_chrome()
    if chrome:
        ok("浏览器可执行文件：%s" % chrome)
    else:
        warn("未找到 Chrome / Chromium（导出长图要用）：\n    "
             + runtime.CHROME_HINT.replace("\n", "\n    "))


def check_targets(t):
    if t is None:
        return
    n_ind, n_wide, n_hk, n_us = len(t.INDUSTRIES), len(t.WIDE), len(t.HK), len(t.US)
    if (n_ind, n_wide, n_hk, n_us) != (31, 6, 7, 12):
        fail("标的数量不对：行业 %d / 宽基 %d / 港股 %d / 美股 %d，应为 31 / 6 / 7 / 12"
             % (n_ind, n_wide, n_hk, n_us))
    else:
        ok("标的数量 31 行业 + 6 宽基 + 7 港股 + 12 美股 = 56")

    codes = t.ALL_CODES
    dup = sorted({c for c in codes if codes.count(c) > 1})
    if dup:
        fail("代码重复：%s" % ", ".join(dup))
    else:
        ok("%d 个代码无重复" % len(codes))

    bad_etf = []
    for name, code, etf, base in t.INDUSTRIES + t.WIDE + t.HK + t.US:
        if etf and not re.fullmatch(r"\d{6}", str(etf)):
            bad_etf.append("%s(%s)->%s" % (name, code, etf))
        if not (isinstance(base, (int, float)) and base > 0):
            fail("%s 的 924 基准价异常：%r" % (name, base))
    if bad_etf:
        fail("ETF 代码格式不对（应为 6 位数字）：%s" % ", ".join(bad_etf))
    else:
        ok("代表 ETF 代码格式正常（无 ETF 的行业留空，属定版）")


def check_skill_table(t):
    """SKILL.md 的「标的清单」表 vs targets.py，逐行比对。"""
    if t is None:
        return
    path = os.path.join(SKILL, "SKILL.md")
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.count("|") < 6:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6 or not cells[0].isdigit():
            continue
        seq, name, code, etf, base, group = cells
        code = code.strip("`")
        etf = "" if etf in ("—", "-", "") else etf.strip("`")
        rows[code] = dict(name=name, etf=etf, base=base, group=group)

    if len(rows) != 56:
        fail("SKILL.md 标的清单解析到 %d 行，应为 56 行（表被改坏了？）" % len(rows))
        return

    tgt = t.by_code()
    diff = []
    for code, info in tgt.items():
        r = rows.get(code)
        if r is None:
            diff.append("SKILL.md 缺 %s" % code)
            continue
        if r["name"] != info["name"]:
            diff.append("%s 名称 %r != %r" % (code, r["name"], info["name"]))
        if r["etf"] != (info["etf"] or ""):
            diff.append("%s ETF %r != %r" % (code, r["etf"], info["etf"]))
        if info["base"] is None:
            if r["base"] not in ("—", "-", ""):
                diff.append("%s 基准应为「—」，实际 %r" % (code, r["base"]))
        else:
            try:
                if abs(float(r["base"]) - float(info["base"])) > 0.005:
                    diff.append("%s 924 基准 %s != %s" % (code, r["base"], info["base"]))
            except ValueError:
                diff.append("%s 924 基准不是数字：%r" % (code, r["base"]))
        if r["group"] != info["group"]:
            diff.append("%s 分组 %r != %r" % (code, r["group"], info["group"]))
    extra = set(rows) - set(tgt)
    if extra:
        diff.append("SKILL.md 多出代码：%s" % ", ".join(sorted(extra)))

    if diff:
        fail("SKILL.md 标的清单与 targets.py 不一致：\n    " + "\n    ".join(diff[:12])
             + ("\n    ……共 %d 处" % len(diff) if len(diff) > 12 else ""))
    else:
        ok("SKILL.md 标的清单与 targets.py 完全一致（56 行逐项比对）")


def check_history(t):
    path = os.path.join(SKILL, "data/temperature-history.json")
    if not os.path.exists(path):
        return
    try:
        h = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        fail("历史库 JSON 解析失败：%s" % e)
        return
    for key, min_len in (("a", 2), ("hk", 3), ("us", 2)):
        s = h.get("series", {}).get(key)
        if not s:
            fail("历史库缺少 series.%s" % key)
            continue
        dates = [p[0] for p in s]
        if dates != sorted(dates):
            fail("series.%s 日期不是升序" % key)
        if len(set(dates)) != len(dates):
            fail("series.%s 有重复日期" % key)
        # A股早期点是 [日期, 温度]（标的数固定 37 可省），港股必须带第三位
        if any(len(p) < min_len for p in s):
            fail("series.%s 有点少于 %d 个字段" % (key, min_len))
        bad = [p for p in s if not (isinstance(p[1], (int, float)) and 0 <= p[1] <= 100)]
        if bad:
            fail("series.%s 有温度越界（应在 0–100）：%s" % (key, bad[:3]))
        ok("series.%s：%d 点，%s → %s" % (key, len(s), dates[0], dates[-1]))
    return h


def check_market_data(t, h):
    """明细库 data/market-data.json：结构、覆盖、以及硬规则 7（末点 = 当天等权均值）。"""
    path = os.path.join(SKILL, "data/market-data.json")
    if not os.path.exists(path):
        warn("没有 data/market-data.json（跑 `python scripts/update.py migrate` 或 plan 后会生成）")
        return None
    try:
        db = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        fail("market-data.json 解析失败：%s" % e)
        return None
    dates = db.get("dates") or {}
    if not dates:
        warn("明细库是空的")
        return None
    total = len(t.ALL_CODES)
    known = t.by_code()

    bad_keys = [d for d in dates if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
    if bad_keys:
        fail("明细库有非法日期键：%s" % ", ".join(bad_keys[:5]))
        return None
    alien = sorted({c for rows in dates.values() for c in rows if c not in known})
    if alien:
        fail("明细库里有不在标的清单的代码：%s" % ", ".join(alien[:6]))
        return None

    ordered = sorted(dates)
    partial = []
    for d in ordered:
        rows = dates[d]
        full = [c for c in t.ALL_CODES
                if all(rows.get(c, {}).get(k) is not None
                       for k in ("chg", "ytd", "close", "pe", "t"))]
        if len(full) < total:
            partial.append("%s(%d/%d)" % (d, len(full), total))
    ok("明细库：%d 个交易日，%s → %s" % (len(ordered), ordered[0], ordered[-1]))
    if partial:
        warn("不完整的日子（历史遗留可接受）：%s%s"
             % (", ".join(partial[:4]), " 等 %d 天" % len(partial) if len(partial) > 4 else ""))
    else:
        ok("每个交易日都是 %d/%d，明细齐" % (total, total))

    if t is None or not h:
        return db

    # 硬规则 7：只用「最近一个齐全的日子」比
    complete = [d for d in ordered
                if all(all(dates[d].get(c, {}).get(k) is not None
                           for k in ("chg", "ytd", "close", "pe", "t"))
                       for c in t.ALL_CODES)]
    if not complete:
        warn("没有一天是 %d/%d 齐全的，跳过等权均值校验" % (total, total))
        return db
    d = complete[-1]
    rows = dates[d]
    for key, codes in (("a", t.A_CODES), ("hk", t.HK_CODES), ("us", t.US_CODES)):
        mean = sum(rows[c]["t"] for c in codes) / len(codes)
        pts = [p for p in h["series"][key] if p[0] == d]
        if not pts:
            warn("历史库还没有 %s 这个点（%s），先跑 build 再复核" % (d, key))
            continue
        if abs(pts[-1][1] - mean) > 0.01:
            fail("%s %s 末点 %.2f 与明细库等权均值 %.2f 不一致（硬规则 7）"
                 % (key, d, pts[-1][1], mean))
        else:
            ok("%s %s 温度 %.2f = 明细库等权均值 %.2f" % (key, d, pts[-1][1], mean))
    return db


def check_us_history():
    path = os.path.join(SKILL, "data/us-history.json")
    if not os.path.exists(path):
        return
    try:
        db = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        fail("us-history.json 解析失败：%s" % e)
        return
    pts = db.get("points") or []
    if len(pts) < 3:
        fail("us-history.json 只有 %d 个点，画不出走势" % len(pts))
        return
    dates = [p[0] for p in pts]
    if dates != sorted(dates):
        fail("us-history.json 的 points 日期不是升序")
    if len(set(dates)) != len(dates):
        fail("us-history.json 的 points 有重复日期")
    bad = [p for p in pts if not (isinstance(p[1], (int, float)) and 0 <= p[1] <= 100)]
    if bad:
        fail("us-history.json 有温度越界（0–100）：%s" % bad[:3])
        return
    ok("美股十年回溯：%d 个点，%s → %s" % (len(pts), dates[0], dates[-1]))


def check_template():
    path = os.path.join(SKILL, "assets/page_template.html")
    if not os.path.exists(path):
        return
    html = open(path, encoding="utf-8").read()
    need = ["const A = [", "const H = [", "const U = [", "const TH = [", "const THH = [", "const THU = [",
            "/* ───────── 卡片 ───────── */"]
    miss = [s for s in need if s not in html]
    if miss:
        fail("模板缺少 build.py 依赖的占位符：%s" % ", ".join(miss))
    else:
        ok("模板占位符齐全（A / H / U / TH / THH / THU / 卡片注释）")


def main():
    t = check_runtime()
    check_files()
    check_targets(t)
    check_skill_table(t)
    h = check_history(t)
    check_market_data(t, h)
    check_us_history()
    check_template()

    print("=" * 66)
    for m in OK:
        print("  OK   " + m)
    for m in WARN:
        print("  WARN " + m)
    for m in FAIL:
        print("  FAIL " + m)
    print("=" * 66)

    print("""
MCP 需人工确认（脚本查不到，逐条打勾）：
  [ ] 已安装金融数据 MCP：Wind 指数数据 MCP，或 东方财富妙想 mx-ds-mcp
  [ ] 连接器页面已「信任」，工具列表里能看到对应工具
  [ ] 冒烟测试通过：查 000300.SH 在 <最近交易日> 的 PE(TTM) 及其近10年分位数
      → 应返回 市盈率 / 市盈率序号 / 市盈率最大序号 / 分位数 四项
  [ ] 安装方式见 references/mcp-setup.md；缺 MCP 时先装，不要凭印象填数
""")

    print("结论：%s" % ("全部通过，可以开工（记得先确认 MCP）" if not FAIL
                       else "有 %d 项 FAIL，先修再取数" % len(FAIL)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
