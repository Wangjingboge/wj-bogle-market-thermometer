# -*- coding: utf-8 -*-
"""取数计划（兼容旧入口）—— 现在只是 update.py plan 的薄壳。

历史明细已经进 data/market-data.json，所以「计划」只说**还缺什么**，
不再无脑打印 56 条。老命令照样能用：

    python fetch.py 2026-11-12     # = update.py plan --date 2026-11-12
    python fetch.py                # = update.py plan（最近交易日）

完整用法见 `python scripts/update.py -h`：status / plan / apply / migrate / build / all。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import update


class _Args:
    date = None
    out = os.getcwd()


if __name__ == "__main__":
    a = _Args()
    if len(sys.argv) > 1:
        a.date = sys.argv[1]
    update.cmd_plan(a)
