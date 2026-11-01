# 望京博格的市场温度计 · Skill 包 v1.1.1

把一篮子指数的估值位置压成一个 0–100 的数字，再排版成可以直接发的长图。
温度 = 每个标的当前 PE(TTM) 在**自己近十年历史**里的分位数，37 个（A股）或 7 个（港股）**等权**平均。

## ⚠️ 安装前必读：这个 skill 需要金融数据 MCP

Skill 本身**不带数据、不联网取数**，只负责「排取数计划 → 组装 HTML → 出长图」。
44 个标的的 **PE(TTM) 近十年分位数**必须由外部的金融数据 MCP 提供，否则取不到数、出不了图。

两条路线，二选一：

| 路线 | 适用 | 需要什么 |
|---|---|---|
| **A · Wind**（skill 默认按这套写） | 有 Wind 终端 / Wind 数据权限 | Wind 指数数据 MCP，工具 `get_index_price_indicators`、`get_index_fundamentals` |
| **B · 东方财富妙想 MCP** | 没有 Wind 账号 | `mx-ds-mcp`（`https://mxapi.eastmoney.com/mxds/mcp`，header `em_api_key`），按积分计费 |

**完整安装步骤、`mcp.json` 配置、Claude Code / Cursor 写法、自建 Wind MCP（`pip install wind-mcp`）与自算分位脚本** 见：

→ [`references/mcp-setup.md`](references/mcp-setup.md)

三条最短路径：

1. **WorkBuddy + 妙想**：连接器页 → MCP 加号 → 妙想/Choice/东方财富 APP 扫码授权 → 「去试试」。
2. **WorkBuddy + Wind**：连接器市场搜 Wind → 授权 → 工具列表出现 `wind-index-data` 系列。
3. **自建**：Wind 终端已登录 → `pip install wind-mcp` → 写进 `~/.workbuddy/mcp.json` → 连接器页点「信任」。

## 装完先自检

```bash
cd wj-bogle-market-thermometer
python scripts/check_env.py
```

它会查：文件完整性、44 个标的清单（含 SKILL.md 与 `scripts/targets.py` 是否一致）、历史库结构、最近快照的末点是否等于等权均值、模板占位符。
**MCP 是否连通脚本查不到**，最后会打印一份人工核对清单：问一句「查 000300.SH 在 <最近交易日> 的 PE(TTM) 及其近10年分位数」，能返回 市盈率 / 序号 / 最大序号 / 分位数 四项才算通。

## 跑一次（日更四步）

```bash
python scripts/runtime.py                 # ⓿ 先看 node / playwright-core / 浏览器有没有找齐
python scripts/fetch.py 2026-10-28        # ① 打印取数计划：快照串 + 44 条分位数问句 + snapshot 模板
# ② 用 MCP 取数（1 次快照 + 44 次单日分位数，一条消息并行发），填成 snapshot_2026-10-28.json
python scripts/build.py snapshot_2026-10-28.json 2026-10-27 --out ./out
node scripts/export_long.js ./out/市场温度计-2026-10-28.html ./out/市场温度计-2026-10-28.png
```

不用设 `NODE_PATH`、不用填浏览器路径，脚本自己找。
**没装 MCP 也能先试**：仓库里带了一份真实快照 `snapshot_2026-10-30.json`，直接

```bash
python scripts/build.py snapshot_2026-10-30.json --out ./out
node scripts/export_long.js ./out/市场温度计-2026-10-30.html ./out/市场温度计-2026-10-30.png
```

就能复现出 2160×6904 的成品长图，先看效果再决定装不装数据源。

产物：单文件 HTML 看板 + 2160×6904 高清长图（1:3.2，PNG 约 1.7MB）。

## 装到自己的 workbuddy / Claude Code

```bash
git clone https://github.com/<你的账号>/wj-bogle-market-thermometer.git \
  ~/.workbuddy/skills/wj-bogle-market-thermometer
```

（Claude Code 放 `~/.claude/skills/`，Cursor 放 `.cursor/skills/`，都是同一个目录结构。）

## 目录结构

```
wj-bogle-market-thermometer/
├── SKILL.md                     # 主文档：先决条件、硬规则、44 标的清单（含代表 ETF）、工作流
├── README.md                    # 本文件（给人看的安装说明）
├── references/
│   ├── mcp-setup.md             # ★ 金融数据 MCP 安装与验证（Wind / 妙想）
│   ├── data-sourcing.md         # Wind 简称核对表、调用写法、校验锚点、数据清洗
│   ├── rendering.md             # 页面数组字段、温度计 SVG、走势图参数、字号基线
│   └── export.md                # 长图导出：三处注入、尺寸、翻车点
├── assets/page_template.html    # 主看板模板（改数据即用）
├── data/temperature-history.json# 十年温度序列（资产，别删）
├── scripts/
│   ├── targets.py               # 单一事实源：44 标的代码/名称/ETF/924 基准价
│   ├── runtime.py               # 运行时探测：node / playwright-core / 浏览器
│   ├── check_env.py             # 环境自检
│   ├── fetch.py                 # 取数计划生成器
│   ├── build.py                 # 组装 HTML（写历史库、注入 PAVG）
│   ├── history.js               # 历史库：import / add / print / stat
│   └── export_long.js           # 整页长图导出
└── snapshot_2026-10-30.json     # 示例快照（真实数据，可直接 build 复现）
```

## 三条铁律（动手前务必看 SKILL.md 的「硬规则」）

1. **等权**，不是市值加权。
2. 分位数**必须一指数一日期单问**；区间查询会系统性偏高 15–27 度。
3. 历史库**只补新点**，不要重取整条序列（那是几小时的工作量）。

温度是估值位置的模糊刻度，不是点位预测。不构成投资建议。

## License

MIT © 望京博格（郑志勇）。随便用、随便改，改了别说是我写的就行——数据源和取数口径的坑，见 `references/`。
