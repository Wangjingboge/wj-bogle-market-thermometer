# -*- coding: utf-8 -*-
"""取数计划生成器：一键打印「1 次快照串 + 44 行分位数问句 + 空 snapshot 模板」。

用法：
    python fetch.py 2026-10-23

输出三块，照抄即可：
  1) SNAPSHOT —— 一条 get_index_price_indicators 的 windcode，44 个代码一次拿全；
  2) QUERIES —— 44 条 get_index_fundamentals 的单日分位数问句（一条消息全部并行发出）；
  3) SNAPSHOT JSON —— 填完 chg/ytd/close/pe/t 后存成 snapshot_<日期>.json，交给 build.py。

铁律：分位数必须「一个指数一个日期」单问，区间查询会系统性偏高 15–27 度。
"""
import sys, json
import targets

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-23"

def main():
    print("=" * 70)
    print("⚠ 前置条件：本 skill 不联网取数，必须先装金融数据 MCP")
    print("  · 路线 A  Wind 指数数据 MCP：get_index_price_indicators / get_index_fundamentals")
    print("  · 路线 B  东方财富妙想 MCP：mx-ds-mcp（https://mxapi.eastmoney.com/mxds/mcp）")
    print("  安装与验证：references/mcp-setup.md   环境自检：python scripts/check_env.py")
    print("  若工具列表里没有上述工具，先装 MCP，不要凭印象填数。")
    print("=" * 70)
    print("① SNAPSHOT 快照（get_index_price_indicators，一次传全 44 个）")
    print("indexes:", "最新交易日,中文简称,最新成交价,涨跌幅,年初至今涨跌幅,市盈率(TTM)")
    print("windcode:", ",".join(targets.ALL_CODES))
    print()

    print("=" * 70)
    print(f"② QUERIES 分位数（get_index_fundamentals，{len(targets.ALL_CODES)} 条并行）")
    for c in targets.ALL_CODES:
        print(f"查询 {c} 在 {DATE} 的市盈率PE(TTM)及其近10年分位数")
    print()

    print("=" * 70)
    print("③ SNAPSHOT JSON 模板（填数后存 snapshot_%s.json）" % DATE)
    tpl = {"date": DATE,
           "snapshot": {c: {"chg": None, "ytd": None, "close": None, "pe": None, "t": None}
                        for c in targets.ALL_CODES}}
    print(json.dumps(tpl, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
