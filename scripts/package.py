#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""打分发用的 zip。

Skill 平台只接受**两级目录**（根目录 / 二级目录 / 文件），子目录里再套子目录会直接
报「目录层级超限」。这个脚本按该规则收集文件，越界就报错，别再手搓 zip。

    python scripts/package.py                 # 输出到 dist/<name>-<version>.zip
    python scripts/package.py --out /tmp/x.zip
    python scripts/package.py --list          # 只打印将要打包的文件，不写盘

排除规则（这些不进包）：
  - __pycache__ / .git / node_modules / dist / data/backup / data/inbox / data/archive
    （backup、inbox 是运行时产物；archive 是已 migrate 进 market-data.json 的历史快照）
  - *.pyc / *.tmp / audit.log / .DS_Store / Thumbs.db
"""
import argparse
import os
import re
import sys
import zipfile

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_NAME = os.path.basename(SKILL)
MAX_DEPTH = 2                      # 根目录 / 二级目录 / 文件

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", "dist", ".idea", ".vscode",
    "backup", "inbox", "archive",
}
SKIP_FILES = {"audit.log", ".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_EXT = {".pyc", ".pyo", ".tmp", ".log.bak"}


def version():
    path = os.path.join(SKILL, "SKILL.md")
    try:
        head = open(path, encoding="utf-8").read(4000)
    except OSError:
        return "0.0.0"
    m = re.search(r"^version:\s*(\S+)", head, re.M)
    return m.group(1) if m else "0.0.0"


def collect():
    files, skipped = [], []
    for root, dirs, names in os.walk(SKILL):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(names):
            if f in SKIP_FILES or os.path.splitext(f)[1] in SKIP_EXT:
                skipped.append(os.path.relpath(os.path.join(root, f), SKILL))
                continue
            files.append(os.path.join(root, f))
    # 单独记一下被跳过的 archive，报告里好交代
    arch = os.path.join(SKILL, "data", "archive")
    if os.path.isdir(arch):
        skipped.append("data/archive/（%d 份历史快照，已 migrate 进 market-data.json）"
                       % len([x for x in os.listdir(arch) if x.startswith("snapshot_")]))
    return files, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="输出 zip 路径")
    ap.add_argument("--list", action="store_true", help="只列出文件，不写盘")
    args = ap.parse_args()

    ver = version()
    files, skipped = collect()

    # 层级校验：root/<file> 或 root/<dir>/<file>，超过就报错
    deep = []
    for full in files:
        rel = os.path.relpath(full, SKILL).replace(os.sep, "/")
        if rel.count("/") + 1 > MAX_DEPTH:
            deep.append(rel)
    if deep:
        print("[package] 目录层级超限（平台上只允许 %d 级）：" % MAX_DEPTH, file=sys.stderr)
        for d in deep[:20]:
            print("  " + d, file=sys.stderr)
        print("  → 请拍平这些子目录，或把它们加进 SKIP_DIRS。", file=sys.stderr)
        return 2

    groups = {}
    for full in files:
        rel = os.path.relpath(full, SKILL).replace(os.sep, "/")
        groups.setdefault(os.path.dirname(rel) or ".", []).append(rel)

    if args.list:
        for g in sorted(groups):
            print("%s/  (%d)" % (g, len(groups[g])))
            for r in groups[g]:
                print("    " + os.path.basename(r))
        print("\n合计 %d 个文件，版本 %s" % (len(files), ver))
        return 0

    out = args.out or os.path.join(SKILL, "dist", "%s-%s.zip" % (ROOT_NAME, ver))
    out = os.path.abspath(os.path.expanduser(out))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for full in files:
            rel = os.path.relpath(full, SKILL).replace(os.sep, "/")
            z.write(full, "%s/%s" % (ROOT_NAME, rel))

    # 写盘后回读校验，别只信自己
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        bad = [n for n in names if n.split("/").__len__() - 1 > MAX_DEPTH]
        if bad:
            print("[package] 生成结果里仍有超层级条目：%s" % bad[:5], file=sys.stderr)
            return 3
        size = os.path.getsize(out)

    print("[package] %s" % out)
    print("          版本 %s · %d 个文件 · %.1f KB · 最深 %d 级"
          % (ver, len(names), size / 1024.0,
             max(len(n.split("/")) - 1 for n in names)))
    for g in sorted(groups):
        print("          %-12s %d" % (g, len(groups[g])))
    if skipped:
        print("          已排除：%s" % "、".join(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
