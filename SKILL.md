---
name: wj-bogle-market-thermometer
version: 1.1.1
display_name: 望京博格的市场温度计
display_name_en: WJ Bogle Market Thermometer
prerequisites: 必须已安装金融数据 MCP（Wind 指数数据 MCP，或东方财富妙想 MCP）；否则取不到指数 PE 十年分位数，skill 无法产出。安装方式见 references/mcp-setup.md
description: 复刻望京博格「市场温度计」——用 Wind 取 31 个申万一级行业 + 6 个宽基（A股 37 个标的）与 7 只港股指数的 PE(TTM) 近十年分位数，等权平均成 0-100 的市场温度，产出单文件 HTML 看板并导出 2160×6904 高清长图。历史温度累积在 data/temperature-history.json，十年走势只补新点、不重取。前置条件：需先安装金融数据 MCP（Wind 指数数据 MCP 或东方财富妙想 MCP），否则取不到分位数，安装方式见 references/mcp-setup.md。 当用户提到「市场温度计」「望京博格温度」「A股/港股温度」「行业估值分位」「申万行业温度」「更新温度」「出温度长图」时使用。
description_zh: "复刻望京博格「市场温度计」：用 Wind 取 31 个申万一级行业 + 6 个宽基（A股 37 个标的）与 7 只港股指数的 PE(TTM) 近十年分位数，等权平均成 0-100 的市场温度，产出单文件 HTML 看板并导出 2160×6904 高清长图。历史温度累积在 data/temperature-history.json，十年走势只补新点、不重取。前置条件：需先安装金融数据 MCP（Wind 或东方财富妙想），否则取不到分位数。当用户提到「市场温度计」「A股/港股温度」「行业估值分位」「申万行业温度」「更新温度」时使用。"
description_en: "Reproduces WJ Bogle's Market Thermometer: pulls 10-year PE(TTM) percentiles from Wind for 31 SW level-1 industries plus 6 broad-based indices (37 A-share targets) and 7 Hong Kong indices, equal-weights them into a 0-100 market temperature, builds a single-file HTML dashboard and exports a 2160x6904 hi-res long image. History accumulates in data/temperature-history.json (append-only, no re-fetching). Prerequisite: a financial-data MCP (Wind index-data MCP or Eastmoney Miaoxiang MCP) must be installed, otherwise percentiles cannot be fetched; see references/mcp-setup.md. Use when the user mentions market thermometer, A-share or HK temperature, industry valuation percentile, SW industry temperature, or updating the temperature chart."
agent_created: true
---

# 望京博格的市场温度计

## 这个 skill 做什么

把一篮子指数的估值位置压成一个 0–100 的数字，再把它排版成可以直接发的图。温度 = 每个标的当前 PE(TTM) 在**自己近十年历史**里的分位数，37 个（A股）或 7 个（港股）分位数**等权**平均。

读数是：0 极冷、100 极热。30° 以下开始买入（可提高仓位），50° 以上开始卖出（不可提高仓位）。

---

## ⚠️ 先决条件：必须装一个金融数据 MCP，否则用不了

**这个 skill 自己不带数据、不联网取数。** 它只做三件事：排取数计划、组装 HTML、导出长图。44 个标的的 PE(TTM) 十年分位数，必须由外部的**金融数据 MCP** 提供。

**没装 MCP 的表现**：`scripts/fetch.py` 能跑、`build.py` 能跑，但 Step 1 一个数字都取不回来，`snapshot` 全是 None，卡片和表格是空的。遇到这种情况，先按 `references/mcp-setup.md` 装 MCP，别硬着头皮往下走，更不要凭印象编数字。

需要的能力只有两条（缺一不可）：

| # | 能力 | 说明 |
|---|---|---|
| 1 | 指数行情快照：最新交易日 / 涨跌幅 / 年初至今 / 市盈率(TTM) | 一次能传 44 个代码最佳 |
| 2 | **指数 PE(TTM) 的近十年分位数**，支持「指定指数 + 指定交易日」 | 温度就是它，没有替代品 |

### 两条可选路线

| 路线 | 适用 | 服务 / 工具 | 安装文档 |
|---|---|---|---|
| **A · Wind**（本 skill 默认按这套写） | 有 Wind 终端或 Wind 数据权限 | `get_index_price_indicators`、`get_index_fundamentals`（`wind-index-data` 系列） | `references/mcp-setup.md` §2 |
| **B · 东方财富妙想 MCP** | 无 Wind 账号 | `mx-ds-mcp`，`https://mxapi.eastmoney.com/mxds/mcp`，header `em_api_key` | `references/mcp-setup.md` §3 |

**东方财富妙想一句话接入**（WorkBuddy）：连接器页 → MCP 加号 → 用妙想/Choice/东方财富 APP 扫码或手机号授权 → 「去试试」。手写 `~/.workbuddy/mcp.json` 的完整 JSON、Claude Code / Cursor 配置、以及自建 Wind MCP（`pip install wind-mcp`）的写法，都在 `references/mcp-setup.md`。

> 妙想若只返回 PE、不返回分位数，走兜底：拉该指数近十年逐日 PE 序列**自算分位**（脚本片段见 `references/mcp-setup.md` §2.3）。口径要整条序列统一，别和 Wind 页面值混着写。

### 装完先跑自检

```bash
python scripts/check_env.py     # 查文件、标的清单、依赖；MCP 需人工确认已连接
```

再问一句「查 000300.SH 在 2026-10-28 的 PE(TTM) 及其近10年分位数」，能返回 `PE ≈ 12.8 / 序号 / 最大序号 / 分位 ≈ 52.8`，才算通了。

---


## 硬规则：先读这段再动手

1. **等权，不是市值加权。** 市值加权会把银行地产的权重带进来，温度被系统性压低，博格不用这个口径。
2. **分位数必须逐日单问。** Wind 的 `get_index_fundamentals` 在「一天一问」时返回与页面同源的值；写区间或多日期会走另一套算法，**系统性偏高 15–27 度**，且受 100 行上限截断。这是本 skill 最贵的教训，不要图省事批量查。
3. **港股通非银是 `931024.CSI`（中证港股通非银行金融主题指数）**，不是恒生系的 `HSSCHKY.HI`。后者 2026 年才有行情，用它会让 2026 年前的港股曲线全线失真。
4. **新指数样本不足不进均值。** 分位数基于过短的历史会被首日/短期极值钉死在 0 或 100，造出假尖峰。经验阈值：不足 120 个交易日不计入；要严谨可比则放宽到 500 个交易日（约两年）。
5. **历史只补不重取。** 十年序列存在 `data/temperature-history.json` 里，每次更新只取新增的那几个点。重取 48×37 次查询是几小时的工作量，没必要。
6. **每次出图前跑一遍校验。** A股历史序列的锚点值见 `references/data-sourcing.md`，对不上就说明取数口径错了，别往下走。
7. **末点必须等于当天快照的等权平均。** 卡片上的大数字是 37 个（或 7 个）温度现算的，历史序列末点若对不上（曾出现 51.52 vs 51.55），曲线标签和卡片会自相矛盾。写完新点后拿快照均值复核一遍，差 0.01 以上就覆盖修正。

## 博格的固定偏好（2026-10 定版，别自己改回去）

| 项目 | 定版 |
|---|---|
| 页头标题 | **望京博格的市场温度计**（副标题只写「31个申万一级行业 + 6个宽基」，不重复署名） |
| 表格列 | 序 / 行业名称 / 今年以来 / 924以来 / 当日PE / 行业温度 / 相关标的 —— **没有「当日涨幅」列** |
| 默认排序 | **按行业温度升序（冷 → 热）**，`sortKey='t', sortAsc=true` |
| 分项区字号 | 表格正文 21px、表头 18px、小标题 23px（比原始版大两个字号） |
| 产物规格 | **默认 2160×6904 高清 PNG**（视口 1080、输出 2x 像素），1:3.2 长图；1080 版只在要小体积时降级出 |

`chg`（当日涨幅）仍要取，留在数组里当核对用，只是不渲染。改列宽时先看 `references/rendering.md` 的字号基线一节。

## 标的清单（44 个，写死在 skill 里，别临时搜）

页面表格最后一列「**相关标的**」就是下面这张表里的**代表 ETF 代码**，直接写死，不要取数时现搜、也不要让模型自己配。页面显示名、Wind 代码、代表 ETF、924 基准收盘价都在这里，代码侧的单一事实源是同内容的 `scripts/targets.py`——**改清单时两处一起改**，改完跑 `python scripts/check_env.py` 校验一致性。

| 序 | 页面显示名 | Wind 代码 | 相关标的（代表 ETF） | 924 收盘 | 分组 |
|---|---|---|---|---|---|
| 1 | 猪肉+农业 | `801010.SI` | `159865` | 2242.07 | 行业 |
| 2 | 基础化工 | `801030.SI` | `159870` | 2847.70 | 行业 |
| 3 | 钢铁 | `801040.SI` | `515210` | 1785.20 | 行业 |
| 4 | 有色金属 | `801050.SI` | `561330` | 4065.63 | 行业 |
| 5 | 电子(芯片) | `801080.SI` | `159995` | 3119.15 | 行业 |
| 6 | 家用电器 | `801110.SI` | `159996` | 7361.20 | 行业 |
| 7 | 食品饮料(白酒) | `801120.SI` | `512690` | 15347.59 | 行业 |
| 8 | 纺织服饰 | `801130.SI` | — | 1218.63 | 行业 |
| 9 | 轻工制造 | `801140.SI` | — | 1631.45 | 行业 |
| 10 | 医药+医疗 | `801150.SI` | `512010` | 6277.48 | 行业 |
| 11 | 发电厂 | `801160.SI` | `159611` | 2267.16 | 行业 |
| 12 | 交通运输 | `801170.SI` | — | 1985.32 | 行业 |
| 13 | 房地产 | `801180.SI` | `512220` | 1819.65 | 行业 |
| 14 | 商贸零售 | `801200.SI` | — | 1543.06 | 行业 |
| 15 | 酒店+旅游+检测 | `801210.SI` | `159766` | 6407.12 | 行业 |
| 16 | 综合 | `801230.SI` | — | 1914.95 | 行业 |
| 17 | 建筑材料 | `801710.SI` | `159745` | 3670.84 | 行业 |
| 18 | 建筑装饰 | `801720.SI` | — | 1578.90 | 行业 |
| 19 | 电力设备(电池光伏) | `801730.SI` | `516090` | 5721.55 | 行业 |
| 20 | 国防军工 | `801740.SI` | `512660` | 1152.46 | 行业 |
| 21 | 计算机 | `801750.SI` | `512720` | 3095.35 | 行业 |
| 22 | 传媒(游戏) | `801760.SI` | `159869` | 491.24 | 行业 |
| 23 | 通信(5G) | `801770.SI` | `515880` | 2286.15 | 行业 |
| 24 | 银行 | `801780.SI` | `516310` | 3390.82 | 行业 |
| 25 | 证券+保险 | `801790.SI` | `512880` | 1451.03 | 行业 |
| 26 | 汽车 | `801880.SI` | `516110` | 5208.24 | 行业 |
| 27 | 机械设备 | `801890.SI` | `516960` | 1189.34 | 行业 |
| 28 | 煤炭 | `801950.SI` | `515220` | 2815.21 | 行业 |
| 29 | 石油石化 | `801960.SI` | — | 2149.42 | 行业 |
| 30 | 环保 | `801970.SI` | `512580` | 1354.20 | 行业 |
| 31 | 美容护理(医美) | `801980.SI` | — | 3654.80 | 行业 |
| 32 | 中证A500 | `000510.SH` | `159338` | 3885.17 | 宽基 |
| 33 | 上证50 | `000016.SH` | `510050` | 2352.14 | 宽基 |
| 34 | 沪深300 | `000300.SH` | `510300` | 3351.91 | 宽基 |
| 35 | 中证500 | `399905.SZ` | `510500` | 4689.60 | 宽基 |
| 36 | 创业板 | `399006.SZ` | `159915` | 1615.32 | 宽基 |
| 37 | 中证1000 | `000852.SH` | `512100` | 4642.56 | 宽基 |
| 38 | 恒生科技 | `HSTECH.HI` | `513010` | 3915.58 | 港股 |
| 39 | 港股通非银 | `931024.CSI` | `513750` | 2534.39 | 港股 |
| 40 | 恒生指数 | `HSI.HI` | `159920` | 19000.56 | 港股 |
| 41 | 港股通高股息 | `HSSCHKY.HI` | `513820` | 1953.64 | 港股 |
| 42 | 恒生消费 | `HSCGSI.HI` | `159699` | 2177.95 | 港股 |
| 43 | 港股创新药 | `HSSCID.HI` | `513120` | 1847.39 | 港股 |
| 44 | 港股汽车 | `HSSCAM.HI` | `159323` | 1961.58 | 港股 |

补充说明：

- 「—」的 8 个行业没有对得上的单行业 ETF，页面该列留空，这是定版状态，不是漏数。
- 代表 ETF 只是给读者一个可交易的对应物，**不参与任何计算**；换 ETF 不影响温度。
- 港股那 7 只是精挑的品类指数，别拿恒生一级行业指数替换（尤其「港股通非银」必须是 `931024.CSI`，见硬规则 3）。

## 工作流

### Step 0 · 定基准日

取最近一个交易日。所有快照、涨幅、末点都用同一天，不要混。开盘前跑就用前一交易日。

### Step 0.5 · 生成取数计划（三件套脚本）

取数、构建、标的清单已拆成三个脚本，**取数前先跑一次 `scripts/fetch.py` 把计划打出来**，照抄即可，不用手拼代码：

```bash
python scripts/fetch.py 2026-10-23
```

它输出三块：① 一条快照 windcode（44 个代码逗号分隔）② 44 条分位数问句 ③ 空 snapshot 模板。日更按这个流程走，能省掉重复取数（见下）。

### Step 1 · 取当期快照（44 个标的）

**开工前先确认金融数据 MCP 已连上**（见文首「先决条件」）。下面写的是 Wind 指数数据 MCP 的写法；如果你用的是东方财富妙想，或自建的 `wind-mcp`（WSD/WSS），等价写法见 `references/mcp-setup.md` §2.3 与 §3.4——**能力要求一样，44 次单日分位一条都不能少**。

对每个标的取四样：当日涨跌幅、今年以来涨幅、当日 PE(TTM)、PE 十年分位数（即温度）。涨跌幅里的「当日」不进表格（列已去掉），但取回来留着核对当日行情有没有抓错。

- **指数行情（点位/涨跌/PE）：`get_index_price_indicators`，一次把 44 个代码逗号分隔传全**，已实测一次返回 44 行，不要再拆成两三次。
- **分位数：`get_index_fundamentals`，一次一个指数一个日期**。44 次是铁律底线（区间查询会偏高 15–27 度，见硬规则 2），但把 44 条问句**在同一条消息里全部并行发出**，一轮往返拿完，别分五六轮。

取完把结果填进 `snapshot_<日期>.json`（fetch.py 会给出空模板），数据一次落盘，构建阶段重跑不再重复取数。

44 个标的的代码与代表 ETF 就在上面的「标的清单」一节，代码侧以 `scripts/targets.py` 为准——两处必须一致，改动时一起改，改完跑 `python scripts/check_env.py`。

### Step 2 · 「924 以来」涨幅（基准价已固化）

「924 以来」= 基准日收盘 ÷ 2024-09-24 收盘 − 1，按点位算、不含分红。2024-09-24 是那轮一揽子政策的起点日，被当作这轮行情的原点，不要换成 9-30 或 10-08。

**2024-09-24 的收盘价已固化在 `scripts/targets.py` 里**（每个标的最后一列 base），是常量、不会变，**不要再每天取 `get_index_kline` 重复拉它**。只有新增标的时才需要补一次 kline。

### Step 3 · 更新历史温度（只补新点）

先看存档现状：

```bash
node scripts/history.js stat data/temperature-history.json
```

它给出两条序列的点数、区间、均值、极值、末点。**末点之后的日子就是需要补的。**

对每个要补的采样日，取当天全部标的的分位数求等权平均，再写入：

```bash
node scripts/history.js add data/temperature-history.json a 2026-11-30 52.31 37
node scripts/history.js add data/temperature-history.json hk 2026-11-30 31.04 7
```

- 采样节奏：2016Q4–2025Q3 按季末，2025Q4 起按月。别打乱，两套曲线用的是同一批日期。
- 港股要记当天**实际参与平均的标的数**（第三个数）。它从 2 只长到 7 只，曲线两端不可比，图注里必须交代。
- 同日期重复写入会覆盖，修正坏点不用先删。

写入前先确认这些点算对了：一个采样点的温度是 37 次（A股）或 ≤7 次（港股）单日分位数查询的平均，别拿区间查询的返回凑。

### Step 4 · 组装单文件 HTML（用 build.py，别手贴）

`scripts/build.py` 读 `targets.py`（标的清单 + 924 基准）和 `snapshot_<日期>.json`（当日数据），自动换掉 `A` / `H` / `TH` / `THH` 四个数组并写好历史库：

```bash
python scripts/build.py snapshot_2026-10-22.json 2026-10-21 --out <输出目录>
# 第二个参数是上一交易日（用于卡片「较上一交易日」），可省略——省略时自动从历史库取 DATE 之前最后一个点
```

- 它会顺带把当天温度写进 `data/temperature-history.json`（等价于手动跑 history.js add），只补新点、同日覆盖。
- 卡片上的「较上一交易日」不用逐个取 44 次 prev：脚本用历史库里上一交易日的**聚合值**注入全局 `PAVG`，差分仍是真实聚合差分，但省掉一整轮 44 次单日分位数查询。
- 数组字段含义和页面结构见 `references/rendering.md`。

不要重新设计版式。这套版式已经处理过的坑：双栏压缩后字号掉到 5px、极值标签压在参考线上、30°/50° 文案被末端点遮挡——重画会把这些坑重新踩一遍。

### Step 5 · 导出长图

**标准产物就是高清图**（2026-10-19 定版）：默认出 2160×6904，发小红书/公众号都直接用这张，别再交 1080 的。

```bash
node scripts/export_long.js <html> <输出png>              # 高清版 2160×6904（默认）
```

playwright-core 与 Chromium 内核浏览器由脚本自动探测（环境变量 → PATH → 常见安装位置），**不需要在命令里写 `NODE_PATH` 或浏览器路径**。装之前先跑 `python scripts/runtime.py` 看本机探测结果：

```bash
python scripts/runtime.py        # 打印平台 / python / node / playwright-core / 浏览器的探测结果
```

任何一个没找到，按它的提示二选一：装（`npm i playwright-core`、装 Chrome），或指（`THERMO_NODE_MODULES`、`THERMO_CHROME` 指到已有位置）。

只有明确要小体积（微信预览、直接发聊天框）时才显式降级：

```bash
node scripts/export_long.js <html> <输出png> 1080 1080    # 轻量版 1080×3452
```

产物比例约 1:3.2（CSS 高 3452，高清版像素高 6904），PNG 约 1.7MB。参数与翻车点见 `references/export.md`。

## 日更四步（标准动作）

0. **前置检查**：金融数据 MCP 已连接（Wind 或妙想）；`python scripts/check_env.py` 无 FAIL
1. `python scripts/fetch.py <日期>` → 拿到快照串 + 44 条分位数问句 + 空 snapshot 模板
2. 取数：1 次快照（44 代码一次传全）+ 44 次分位数（一条消息并行发完）
3. 把结果填进 `snapshot_<日期>.json`
4. `python scripts/build.py snapshot_<日期>.json [上一交易日] --out <输出目录>` → 出 HTML，再按 Step 5 导出长图

每步数据都落盘、能重跑，不再重复取数。第 1 步之外的三步**不依赖 MCP**，换机器、离线重出图都能跑。

## 历史存档

`data/temperature-history.json`，两条序列：

```json
{
 "updated": "2026-10-16",
 "series": {
  "a":  [["2016-12-30",55.14], ["2017-03-31",56.72], ...],
  "hk": [["2016-12-30",51.36,2], ["2017-03-31",66.69,2], ...]
 }
}
```

- 每点 `[日期, 温度, 参与标的数]`；A股第三位固定 37，早期点只存 `[日期, 温度]` 两位（省掉），港股必须带第三位。
- 一个点一行，方便人工复核和版本管理。
- 这个文件是**资产不是缓存**：删了就回到「必须重取 1776 次查询」的状态。换机器或备份时优先带走它。
- 从旧看板反向补录：`node scripts/history.js import <看板html> data/temperature-history.json`，会扫描 HTML 里的 `TH` / `THH` 合并进来，不覆盖其他点。

## 文件索引

| 文件 | 什么时候读 |
|---|---|
| `references/mcp-setup.md` | **第一次用必读**：Wind / 东方财富妙想 MCP 的安装与验证，自建 Wind MCP 的工具映射与自算分位 |
| `references/data-sourcing.md` | 取数前必读：Wind 官方简称核对表、调用写法、校验锚点值、数据清洗规则 |
| `references/rendering.md` | 改页面时读：数组字段、温度计 SVG 规格、走势图参数、配色与字号基线 |
| `references/export.md` | 导出长图时读：三处注入、尺寸、翻车点 |
| `data/temperature-history.json` | 十年走势的数据底座，Step 3 读写 |
| `assets/page_template.html` | 主看板模板（改数据即用） |
| `scripts/targets.py` | 单一事实源：44 标的代码/名称/分组/ETF/924 基准价，改清单只改这里 |
| `scripts/check_env.py` | 环境自检：文件完整性、标的清单一致性、依赖、MCP 人工确认清单 |
| `scripts/runtime.py` | 运行时探测：node / playwright-core / 浏览器，跨平台，不写死路径 |
| `scripts/fetch.py` | 取数计划生成器：一键输出快照串 + 44 问 + snapshot 模板 |
| `scripts/build.py` | 组装 HTML：读 targets + snapshot，写历史库、注入 PAVG |
| `scripts/history.js` | 历史温度：import / add / print / stat |
| `scripts/export_long.js` | 整页长图导出 |

## 交付时说什么

温度是估值位置的模糊刻度，不是点位预测，图注和话术里都要留这句。盈利在涨的时候同样的点位温度会自己降下来——横向对比历史极值时锚点已经变了，这点要提醒。

不构成投资建议。

## 更新日志

- **1.1.1**：可移植性改造。新增 `scripts/runtime.py` 统一探测 node / playwright-core / 浏览器（环境变量 → PATH → 常见安装位置，覆盖 Windows / macOS / Linux），`build.py`、`check_env.py`、`export_long.js` 不再写死本机绝对路径，`export_long.js` 也不再需要 `NODE_PATH` 和 Pillow；SKILL.md 与 `references/export.md` 的命令示例同步去掉机器相关路径。
- **1.1.0 / 2026-10-28**：补上「先决条件：金融数据 MCP」一节（Wind / 东方财富妙想两条路线、`references/mcp-setup.md` 安装指南）；把 44 个标的的页面名 / Wind 代码 / **代表 ETF（表格「相关标的」列）** / 924 基准价整表写进 SKILL.md，不再依赖临时搜索；新增 `scripts/check_env.py` 环境自检；`fetch.py` 开跑即提示 MCP 前置条件。
- **1.0.0**：定版。等权口径、44 标的、2160×6904 长图、历史库只补新点。
