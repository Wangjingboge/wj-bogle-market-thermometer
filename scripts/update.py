# -*- coding: utf-8 -*-
"""增量取数入口 —— 历史进库，只补缺口。

一个库：data/market-data.json
    { "schema": 1, "updated": "2026-11-12",
      "dates": { "2026-11-12": { "801010.SI": {"chg":..,"ytd":..,"close":..,"pe":..,"t":..}, ... } } }
    —— 按日期存 56 个标的的逐日明细（chg/ytd/close/pe/t），一个标的都不能少。
    —— 温度均值、924 涨幅都是派生量，不存库，每次现算。

子命令：
    python update.py status [--date D]        库里有什么、缺哪几天、最近一天覆盖多少
    python update.py plan   [--date D]        今天要取什么（已入库的自动跳过，断点续跑）
    python update.py apply  <json>            把取回的裸数据合并进库（原子写 + 自动备份 + 审计）
    python update.py migrate                  把 data/snapshot_*.json 全部收编进库（幂等）
    python update.py build  [--date D]        从库里导出一份 snapshot 临时文件，交给 build.py 出图
    python update.py all    [--date D]        完整：日数据齐 → 直接 build；不齐 → 只打印缺口计划

设计约定（和 wj-buyback-reduction-monitor 一致）：
  - 库只增不改：同一天重跑，非空值不覆盖已有非空值（要改坏点加 --force）
  - 允许半份：56 条只回来 40 条也能落库，plan 下次只补剩下 16 条
  - 任何写操作前先备份，写操作进审计流水
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import date as _date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import targets

DB = os.path.join(SKILL, "data", "market-data.json")
HIST = os.path.join(SKILL, "data", "temperature-history.json")
BACKUP_DIR = os.path.join(SKILL, "data", "backup")
INBOX_DIR = os.path.join(SKILL, "data", "inbox")
AUDIT = os.path.join(SKILL, "data", "audit.log")
SNAP_DIR = os.path.join(SKILL, "data")
SCHEMA = 1
FIELDS = ("chg", "ytd", "close", "pe", "t")
KEEP_BACKUPS = 10


# ────────────────────────── 基础工具 ──────────────────────────

def die(msg):
    print("[update] " + msg, file=sys.stderr)
    sys.exit(1)


def load_db():
    if not os.path.exists(DB):
        return {"schema": SCHEMA, "updated": None, "dates": {}}
    with open(DB, encoding="utf-8") as f:
        db = json.load(f)
    db.setdefault("schema", SCHEMA)
    db.setdefault("dates", {})
    return db


def save_db(db):
    """原子写：先落 .tmp 再 os.replace，断电也不会留半份 JSON。"""
    dates = db["dates"]
    db["dates"] = {d: dates[d] for d in sorted(dates)}
    db["updated"] = max(dates) if dates else None
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    os.replace(tmp, DB)


def backup_db():
    if not os.path.exists(DB):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = os.path.join(BACKUP_DIR, "market-data-%s.json" % stamp)
    shutil.copy2(DB, dst)
    old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("market-data-"))
    for f in old[:-KEEP_BACKUPS]:
        os.remove(os.path.join(BACKUP_DIR, f))
    return dst


def audit(action, date, detail):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    line = "%s | %-6s | %s | %s\n" % (
        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), action, date, detail)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(line)


def is_trading_day(d):
    return d.weekday() < 5


def latest_trading_day(ref=None):
    """今天（或 ref）是周末就往前退到周五；节假日不判断，由人用 --date 指定。"""
    d = ref or _date.today()
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d.isoformat()


def norm_date(s):
    if not s:
        return None
    s = str(s).strip()
    if re.fullmatch(r"\d{8}", s):
        return "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", s):
        return s.replace("/", "-")
    die("日期格式不对：%r（要 YYYY-MM-DD）" % s)


def day_rows(db, date):
    return db["dates"].get(date, {})


def missing_fields(item):
    return [k for k in FIELDS if item.get(k) is None]


def day_status(db, date):
    """返回 (已覆盖标的数, 完整标的数, 缺 t 的代码, 完全缺的代码)。"""
    rows = day_rows(db, date)
    full, no_t, absent = [], [], []
    for c in targets.ALL_CODES:
        it = rows.get(c)
        if not it:
            absent.append(c)
        elif it.get("t") is None:
            no_t.append(c)
        else:
            full.append(c)
    return len(rows), len(full), no_t, absent


# ────────────────────────── validate ──────────────────────────

def validate_item(code, it):
    """返回清洗后的 dict；非法值抛 ValueError。允许半份（缺的字段留 None）。"""
    name = targets.by_code().get(code, {}).get("name", code)
    out = {}
    for k in FIELDS:
        v = it.get(k)
        if v is None or v == "":
            out[k] = None
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("%s（%s）的 %s 不是数字：%r" % (name, code, k, v))
        if k in ("close", "pe") and v <= 0:
            raise ValueError("%s（%s）的 %s 应为正数：%r" % (name, code, k, v))
        if k == "t" and not (0 <= v <= 100):
            raise ValueError("%s（%s）的温度越界 0-100：%r" % (name, code, v))
        out[k] = round(v, 6) if k == "t" else round(v, 4)
    return out


# ────────────────────────── status ──────────────────────────

def cmd_status(args):
    db = load_db()
    dates = sorted(db["dates"])
    total = len(targets.ALL_CODES)
    print("=" * 66)
    print("市场温度计 · 明细库  %s" % DB)
    print("=" * 66)
    if not dates:
        print("库是空的。先跑 `python scripts/update.py migrate` 把历史 snapshot 收编，")
        print("或直接 `python scripts/update.py plan` 看今天要取什么。")
        return

    print("共 %d 个交易日，%s → %s\n" % (len(dates), dates[0], dates[-1]))
    bad = []
    for d in dates:
        n_row, n_full, no_t, absent = day_status(db, d)
        flag = "OK  " if n_full == total else "缺  "
        if n_full != total:
            bad.append((d, no_t, absent))
        print("  %s %s  完整 %2d/%d  缺分位 %2d  整只缺 %2d"
              % (flag, d, n_full, total, len(no_t), len(absent)))

    print()
    if bad:
        print("有不完整的日子（plan 会对最新一天给补数清单）：")
        for d, no_t, absent in bad[-5:]:
            bits = []
            if no_t:
                bits.append("缺 t:" + ",".join(no_t[:6]) + ("…" if len(no_t) > 6 else ""))
            if absent:
                bits.append("整缺:" + ",".join(absent[:6]) + ("…" if len(absent) > 6 else ""))
            print("  %s  %s" % (d, "；".join(bits)))
    else:
        print("全部日子都是 56/56，明细齐。")

    # 与温度历史库对齐
    if os.path.exists(HIST):
        hist = json.load(open(HIST, encoding="utf-8"))
        ha = {p[0] for p in hist["series"].get("a", [])}
        hh = {p[0] for p in hist["series"].get("hk", [])}
        hu = {p[0] for p in hist["series"].get("us", [])}
        print("\n温度历史库：A股 %d 点 / 港股 %d 点 / 美股 %d 点（末点 a=%s hk=%s us=%s）"
              % (len(ha), len(hh), len(hu),
                 max(ha) if ha else "-", max(hh) if hh else "-", max(hu) if hu else "-"))
        only_db = sorted(set(dates) - ha)
        if only_db:
            print("  库里这些日期还没进温度历史（build 时会补）：%s" % ", ".join(only_db[-8:]))

    if os.path.exists(AUDIT):
        tail = open(AUDIT, encoding="utf-8").read().strip().splitlines()[-3:]
        if tail:
            print("\n最近 3 条流水：")
            for ln in tail:
                print("  " + ln)


# ────────────────────────── plan ──────────────────────────

def cmd_plan(args, quiet=False):
    date = norm_date(args.date) or latest_trading_day()
    db = load_db()
    total = len(targets.ALL_CODES)
    n_row, n_full, no_t, absent = day_status(db, date)

    need_snap = [c for c in targets.ALL_CODES
                 if c in absent or any(day_rows(db, date).get(c, {}).get(k) is None
                                       for k in ("chg", "ytd", "close", "pe"))]
    need_t = list(no_t) + list(absent)

    if not quiet:
        print("=" * 70)
        print("⚠ 本 skill 不联网取数，必须先装金融数据 MCP（否则下面这些问句没人回答）")
        print("  · 路线 A  Wind 指数数据 MCP：get_index_price_indicators / get_index_fundamentals")
        print("  · 路线 B  东方财富妙想 MCP：mx-ds-mcp（https://mxapi.eastmoney.com/mxds/mcp）")
        print("  安装与验证：references/mcp-setup.md   环境自检：python scripts/check_env.py")
        print("=" * 70)
        print("日期 %s    库内已有 %d/%d 只（完整 %d）" % (date, n_row, total, n_full))

    if not need_snap and not need_t:
        if not quiet:
            print("\n✅ 这一天已经齐了，不用再取数。直接出图：")
            print("   python scripts/update.py build --date %s" % date)
        return {"date": date, "need_snapshot": [], "need_t": [], "done": True}

    if not quiet:
        print("\n本次只需取 %d 只的行情 + %d 条分位数（已入库的自动跳过）"
              % (len(need_snap), len(need_t)))

    # ① 快照
    if need_snap:
        if not quiet:
            print("\n" + "─" * 70)
            print("① SNAPSHOT 快照（get_index_price_indicators，一次传全 %d 个）" % len(need_snap))
            print("indexes:", "最新交易日,中文简称,最新成交价,涨跌幅,年初至今涨跌幅,市盈率(TTM)")
            print("windcode:", ",".join(need_snap))
    else:
        if not quiet:
            print("\n① 快照：齐全，跳过。")

    # ② 分位数
    if need_t:
        if not quiet:
            print("\n" + "─" * 70)
            print("② QUERIES 分位数（get_index_fundamentals，一条指数一条日期，每批 5 条并行）")
            for c in need_t:
                print("查询 %s 在 %s 的市盈率PE(TTM)及其近10年分位数" % (c, date))
    else:
        if not quiet:
            print("\n② 分位数：齐全，跳过。")

    # ③ 落地模板
    if not quiet:
        os.makedirs(INBOX_DIR, exist_ok=True)
        tpl = {"date": date,
               "items": {c: {"chg": None, "ytd": None, "close": None, "pe": None, "t": None}
                         for c in sorted(set(need_snap) | set(need_t))}}
        print("\n" + "─" * 70)
        print("③ 取回后存成 data/inbox/%s.json，然后 apply（允许只填一部分）" % date)
        print("   python scripts/update.py apply data/inbox/%s.json" % date)
        print(json.dumps(tpl, ensure_ascii=False, indent=1))
    return {"date": date, "need_snapshot": need_snap, "need_t": need_t, "done": False}


# ────────────────────────── apply ──────────────────────────

def cmd_apply(args):
    path = args.file
    if not os.path.exists(path):
        die("找不到 %s" % path)
    raw = json.load(open(path, encoding="utf-8"))
    date = norm_date(raw.get("date")) or (norm_date(os.path.basename(path).replace("snapshot_", "").replace(".json", "")))
    if not date:
        die("这份 json 没写 date 字段，文件名里也认不出日期")
    items = raw.get("items") or raw.get("snapshot") or raw
    if not isinstance(items, dict):
        die("json 结构不对：要 {date, items:{代码:{chg,ytd,close,pe,t}}}")

    unknown = [c for c in items if c not in targets.by_code()]
    if unknown:
        die("这些代码不在标的清单里，先确认是不是打错了：%s" % ", ".join(unknown[:8]))

    db = load_db()
    rows = db["dates"].setdefault(date, {})
    filled, skipped, kept = [], [], []
    errors = []
    for c, it in items.items():
        try:
            clean = validate_item(c, it)
        except ValueError as e:
            errors.append(str(e))
            continue
        cur = rows.get(c, {k: None for k in FIELDS})
        touched = False
        for k in FIELDS:
            v = clean[k]
            if v is None:
                continue
            if cur.get(k) is not None and not args.force:
                if abs(float(cur[k]) - v) > 1e-6:
                    kept.append("%s.%s" % (c, k))
                continue
            cur[k] = v
            touched = True
        rows[c] = cur
        (filled if touched else skipped).append(c)

    if errors:
        print("[update] 以下值不合法，已整条丢弃：")
        for e in errors:
            print("  · " + e)

    if not filled:
        print("[update] 没有新数据入库（%d 只原样、%d 只被已有值挡住）。" % (len(skipped), len(kept)))
        if kept and not args.force:
            print("  想覆盖已有值请加 --force（仅在确认原值错了时用）。")
        return

    backup = backup_db()
    save_db(db)
    n_row, n_full, no_t, absent = day_status(db, date)
    audit("apply", date, "+%d 只，覆盖 %d/%d" % (len(filled), n_full, len(targets.ALL_CODES)))
    print("[update] 已入库 %s：新增/更新 %d 只，当前完整 %d/%d"
          % (date, len(filled), n_full, len(targets.ALL_CODES)))
    if backup:
        print("         备份 → %s" % os.path.relpath(backup, SKILL))
    if no_t or absent:
        print("         仍缺：分位数 %d 只、整只 %d 只 —— 再跑 plan 只看缺口" % (len(no_t), len(absent)))
    else:
        print("         56/56 齐了，可以 build。")


# ────────────────────────── migrate ──────────────────────────

def cmd_migrate(args):
    # 快照可能放在 skill 根目录，也可能已经收到 data/ 下，两处都扫
    cand = []
    for d in (SKILL, SNAP_DIR, os.path.join(SNAP_DIR, "archive")):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if re.fullmatch(r"snapshot_\d{4}-\d{2}-\d{2}\.json", f):
                cand.append(os.path.join(d, f))
    files = sorted(cand)
    if not files:
        print("[update] 找不到 snapshot_*.json，不用迁移。")
        return
    db = load_db()
    added_days, added_cells = 0, 0
    for path in files:
        f = os.path.basename(path)
        raw = json.load(open(path, encoding="utf-8"))
        date = norm_date(raw.get("date")) or f[len("snapshot_"):-len(".json")]
        items = raw.get("items") or raw.get("snapshot") or {}
        rows = db["dates"].setdefault(date, {})
        hit = 0
        for c, it in items.items():
            if c not in targets.by_code():
                continue
            clean = validate_item(c, it)          # 迁移不做兜底，脏数据直接报错
            cur = rows.setdefault(c, {k: None for k in FIELDS})
            for k in FIELDS:
                if clean[k] is not None and cur.get(k) is None:
                    cur[k] = clean[k]
                    hit += 1
        if hit:
            added_days += 1
            added_cells += hit
    if added_cells:
        backup = backup_db()
        save_db(db)
        audit("migrate", "", "%d 天 / %d 个字段（源 %d 份 snapshot）" % (added_days, added_cells, len(files)))
        print("[update] 迁移完成：%d 天、%d 个字段值进库（来自 %d 份 snapshot）"
              % (added_days, added_cells, len(files)))
    else:
        print("[update] 这些 snapshot 的内容库里都有，无需再迁移（幂等）。")
    print("         当前库：%d 个交易日" % len(db["dates"]))


# ────────────────────────── build ──────────────────────────

def export_snapshot(db, date):
    rows = day_rows(db, date)
    total = len(targets.ALL_CODES)
    lacking = [c for c in targets.ALL_CODES if any(rows.get(c, {}).get(k) is None for k in FIELDS)]
    if lacking:
        die("%s 还缺 %d 只的数据（%s%s），先 apply 补齐再 build。"
            % (date, len(lacking), ", ".join(lacking[:6]), "…" if len(lacking) > 6 else ""))
    out = {"date": date, "snapshot": {c: {k: rows[c][k] for k in FIELDS} for c in targets.ALL_CODES}}
    tmp = os.path.join(INBOX_DIR, ".build-%s.json" % date)
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return tmp, total


def cmd_build(args):
    db = load_db()
    date = norm_date(args.date) or db.get("updated") or (_date.today().isoformat())
    if date not in db["dates"]:
        die("库里没有 %s 的明细。先 `update.py plan --date %s` 取数。可用日期：%s"
            % (date, date, ", ".join(sorted(db["dates"])[-6:])))
    snap, total = export_snapshot(db, date)

    prev = args.prev
    if not prev:
        earlier = [d for d in sorted(db["dates"]) if d < date]
        prev = earlier[-1] if earlier else date

    cmd = [sys.executable, os.path.join(HERE, "build.py"), snap, prev, "--out", args.out]
    print("[update] 从库导出 %s 的 %d 只 → %s" % (date, total, os.path.relpath(snap, SKILL)))
    print("[update] 构建：%s" % " ".join(cmd[1:]))
    import subprocess
    rc = subprocess.run(cmd, cwd=os.getcwd()).returncode
    try:
        os.remove(snap)
    except OSError:
        pass
    if rc != 0:
        die("build.py 失败（exit %d），没出图。" % rc)
    audit("build", date, "prev=%s" % prev)


# ────────────────────────── all ──────────────────────────

def cmd_all(args):
    d = cmd_plan(args)
    if d["done"]:
        cmd_build(args)
    else:
        print("\n[update] 数据没齐，先按上面的 ①②③ 取数并 apply，再跑 build。")
        sys.exit(2)


# ────────────────────────── main ──────────────────────────

def main():
    ap = argparse.ArgumentParser(
        prog="update.py",
        description="市场温度计 · 增量取数（历史进库，只补缺口）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, with_date=True):
        if with_date:
            p.add_argument("--date", help="目标交易日 YYYY-MM-DD，缺省=最近交易日")
        p.add_argument("--out", default=os.getcwd(), help="HTML 输出目录（build/all 用）")

    p = sub.add_parser("status", help="库里有什么、缺哪几天")
    common(p)
    p = sub.add_parser("plan", help="今天要取什么（自动跳过已入库）")
    common(p)
    p = sub.add_parser("apply", help="把取回的数据合并进库")
    p.add_argument("file")
    p.add_argument("--force", action="store_true", help="允许覆盖已有非空值（改坏点用）")
    p = sub.add_parser("migrate", help="把 data/snapshot_*.json 收编进库")
    p = sub.add_parser("build", help="从库出图")
    common(p)
    p.add_argument("--prev", help="上一交易日，缺省=库里该日之前最近一天")
    p = sub.add_parser("all", help="plan → 齐则直接 build")
    common(p)
    p.add_argument("--prev")

    args = ap.parse_args()
    {"status": cmd_status, "plan": cmd_plan, "apply": cmd_apply,
     "migrate": cmd_migrate, "build": cmd_build, "all": cmd_all}[args.cmd](args)


if __name__ == "__main__":
    main()
