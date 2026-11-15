---
name: wj-bogle-market-thermometer
version: 1.3.5
display_name: 望京博格的市场温度计
display_name_en: WJ Bogle Market Thermometer
prerequisites: 必须已安装金融数据 MCP（Wind 指数数据 MCP，或东方财富妙想 MCP）；否则取不到指数 PE 十年分位数，skill 无法产出。安装方式见 references/mcp-setup.md
description: 复刻望京博格「市场温度计」——用 Wind 取 31 个申万一级行业 + 6 个宽基（A股 37 个标的）与 7 只港股指数、12 只美股指数（标普500、纳斯达克100 + 10 个 GICS 一级行业）的 PE(TTM) 近十年分位数，等权平均成 0-100 的市场温度，产出单文件 HTML 看板并导出 2160×8340 高清长图。历史温度累积在 data/temperature-history.json，十年走势只补新点、不重取。前置条件：需先安装金融数据 MCP（Wind 指数数据 MCP 或东方财富妙想 MCP），否则取不到分位数，安装方式见 references/mcp-setup.md。 当用户提到「市场温度计」「望京博格温度」「A股/港股温度」「行业估值分位」「申万行业温度」「更新温度」「出温度长图」时使用。
description_zh: "复刻望京博格「市场温度计」：用 Wind 取 31 个申万一级行业 + 6 个宽基（A股 37 个标的）与 7 只港股指数、12 只美股指数（标普500、纳斯达克100 + 10 个 GICS 一级行业）的 PE(TTM) 近十年分位数，等权平均成 0-100 的市场温度，产出单文件 HTML 看板并导出 2160×8340 高清长图。历史温度累积在 data/temperature-history.json，十年走势只补新点、不重取。前置条件：需先安装金融数据 MCP（Wind 或东方财富妙想），否则取不到分位数。当用户提到「市场温度计」「A股/港股温度」「行业估值分位」「申万行业温度」「更新温度」时使用。"
description_en: "Reproduces WJ Bogle's Market Thermometer: pulls 10-year PE(TTM) percentiles from Wind for 31 SW level-1 industries plus 6 broad-based indices (37 A-share targets) plus 7 Hong Kong and 12 US indices (S&P 500, Nasdaq 100 and 10 GICS level-1 sectors), equal-weights them into a 0-100 market temperature, builds a single-file HTML dashboard and exports a 2160x8340 hi-res long image. History accumulates in data/temperature-history.json (append-only, no re-fetching). Prerequisite: a financial-data MCP (Wind index-data MCP or Eastmoney Miaoxiang MCP) must be installed, otherwise percentiles cannot be fetched; see references/mcp-setup.md. Use when the user mentions market thermometer, A-share or HK temperature, industry valuation percentile, SW industry temperature, or updating the temperature chart."
agent_created: true
---

# 望京博格的市场温度计

## 这个 skill 做什么

把一篮子指数的估值位置压成一个 0–100 的数字，再把它排版成可以直接发的图。温度 = 每个标的当前 PE(TTM) 在**自己近十年历史**里的分位数，37 个（A股）或 7 个（港股）分位数**等权**平均。

读数是：0 极冷、100 极热。30° 以下开始买入（可提高仓位），50° 以上开始卖出（不可提高仓位）。

---

## ⚠️ 先决条件：必须装一个金融数据 MCP，否则用不了

**这个 skill 自己不带数据、不联网取数。** 它只做三件事：排取数计划、组装 HTML、导出长图。56 个标的的 PE(TTM) 十年分位数，必须由外部的**金融数据 MCP** 提供。

**没装 MCP 的表现**：`scripts/fetch.py` 能跑、`build.py` 能跑，但 Step 1 一个数字都取不回来，`snapshot` 全是 None，卡片和表格是空的。遇到这种情况，先按 `references/mcp-setup.md` 装 MCP，别硬着头皮往下走，更不要凭印象编数字。

需要的能力只有两条（缺一不可）：

| # | 能力 | 说明 |
|---|---|---|
| 1 | 指数行情快照：最新交易日 / 涨跌幅 / 年初至今 / 市盈率(TTM) | 一次能传 56 个代码最佳；**美股指数不返回 PE 字段**，只能走分位数接口 |
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
| 页头标题 | **望京博格的市场温度计**（副标题写「A股指数 37 只 · 港股指数 7 只 · 美股指数 12 只」，不重复署名） |
| 表格列 | 序 / 行业名称（港股·美股为「指数名称」）/ 今年以来 / 924以来 / 当日PE / 行业温度 / 相关标的 —— **没有「当日涨幅」列** |
| 默认排序 | **按行业温度升序（冷 → 热）**，`sortKey='t', sortAsc=true` |
| 分项区字号 | 表格正文 21px、表头 18px、小标题 23px（比原始版大两个字号） |
| 四句操作纪律 | 放**三张走势图正下方**（不在页脚），18px，2×2 网格；买入列**红**、卖出列**蓝**（与参考线颜色相反，博格指定） |
| 产物规格 | **默认 2160×8340 高清 PNG**（视口 1080、输出 2x 像素），三图并排后约 1:3.8；1080 版只在要小体积时降级出 |

`chg`（当日涨幅）仍要取，留在数组里当核对用，只是不渲染。改列宽时先看 `references/rendering.md` 的字号基线一节。

## 标的清单（56 个，写死在 skill 里，别临时搜）

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
| 45 | 标普500 | `SPX.GI` | `513500` | 5732.93 | 美股 |
| 46 | 纳斯达克100 | `NDX.GI` | `513100` | 19944.84 | 美股 |
| 47 | 信息技术 | `S5INFT.SPI` | — | 4360.40 | 美股 |
| 48 | 医疗保健 | `S5HLTH.SPI` | — | 1797.38 | 美股 |
| 49 | 金融 | `SPF.SPI` | — | 749.62 | 美股 |
| 50 | 可选消费 | `S5COND.SPI` | — | 1615.03 | 美股 |
| 51 | 日常消费 | `S5CONS.SPI` | — | 887.83 | 美股 |
| 52 | 工业 | `S5INDU.SPI` | — | 1139.47 | 美股 |
| 53 | 通讯服务 | `S5TELS.SPI` | — | 309.75 | 美股 |
| 54 | 材料 | `S5MATR.SPI` | — | 604.57 | 美股 |
| 55 | 公用事业 | `S5UTIL.SPI` | — | 405.21 | 美股 |
| 56 | 房地产 | `S5RLST.SPI` | — | 281.88 | 美股 |

补充说明：

- 「—」的 8 个行业没有对得上的单行业 ETF，页面该列留空，这是定版状态，不是漏数。
- 代表 ETF 只是给读者一个可交易的对应物，**不参与任何计算**；换 ETF 不影响温度。
- 港股那 7 只是精挑的品类指数，别拿恒生一级行业指数替换（尤其「港股通非银」必须是 `931024.CSI`，见硬规则 3）。
- 美股 12 只 = 标普500 + 纳斯达克100 + 10 个标普500 GICS 一级行业指数。**GICS 一级行业共 11 个，「能源」在 Wind 取不到 PE(TTM) 十年序列**（`S5ENRS.SPI`、`SP500-1010.SPI`、`SP500-1010TR.SPI` 全部无估值数据），故行业位由「房地产」补足 10 个。
- 美股代码后缀是 `.SPI` 不是 `.SP`；「金融」是 `SPF.SPI`（不是 `S5FINL.SPI`，后者在 Wind 不存在，会报「未识别到有效的金融标的」）。`SP500-XXXX.SPI` 那套是 GICS **二级**行业，别混用。
- 美股「924 以来」基准取 2024-09-24 **美东收盘**点位（与 A股、港股同一口径），`base` 已固化在 `targets.py`，不要再重复取 kline。

## 工作流

### Step 0 · 定基准日

取最近一个交易日。所有快照、涨幅、末点都用同一天，不要混。开盘前跑就用前一交易日。

### Step 0.5 · 增量取数（`scripts/update.py`，唯一入口）

明细库 `data/market-data.json` 按日期存着 56 个标的的逐日数据（chg / ytd / close / pe / t），
**取数只补缺口**：库里已有完整一天就不再碰它，只回来一半也只补剩下一半。

```bash
python scripts/update.py status            # 库里有几天、哪天不完整、与温度历史是否对齐
python scripts/update.py plan              # 今天还缺什么（已入库的自动跳过）
python scripts/update.py apply data/inbox/2026-11-12.json   # 把取回的裸数据合并进库
python scripts/update.py build --date 2026-11-12 --out <目录>  # 从库出 HTML
python scripts/update.py all               # plan → 齐了就直接 build
```

- `plan` 不再无脑打印 56 条：库里已有的代码/字段直接跳过，输出只剩「真缺的那几只」；全齐了它会说「已齐，直接 build」。
- `apply` **允许半份**：56 条只回来 40 条也能落库，下次 plan 只补那 16 条（断点续跑）。
- 合并规则：**已有的非空值不覆盖**，只有 `--force` 才改（确认原值是坏点时才用）；写前自动备份到 `data/backup/`（保留 10 份），每笔操作进 `data/audit.log`。
- 写入是原子的（先 `.tmp` 再 `os.replace`），断电不会留半份 JSON。
- 老命令 `python scripts/fetch.py <日期>` 还留着，等价于 `update.py plan --date <日期>`。

### Step 1 · 照 plan 取数

**开工前先确认金融数据 MCP 已连上**（见文首「先决条件」）。`plan` 输出的两块就是全部工作量：

1. **一条快照**：`get_index_price_indicators`，把 plan 给的 `windcode` 整串传进去（56 个或缺口的那几个），一次返回。
2. **N 条分位数**：`get_index_fundamentals`，一条指数一条日期，**每批 5 条并行**，避开 QPS 限速。

对每个标的要四样：当日涨跌幅、今年以来涨幅、当日 PE(TTM)、PE 十年分位数（即温度）。
涨跌幅里的「当日」不进表格（列已去掉），但取回来留着核对行情有没有抓错。

**分位数必须单日单问**，区间查询会系统性偏高 15–27 度（见硬规则 2），这条不能省。

取完把结果填进 `data/inbox/<日期>.json`（`{date, items:{代码:{chg,ytd,close,pe,t}}}`，plan 会给空模板），
然后 `update.py apply` 落库。**不要手写 `snapshot_*.json`**——那是旧格式，`apply` 也认，但新流程统一走 inbox。

56 个标的的代码与代表 ETF 就在上面的「标的清单」一节，代码侧以 `scripts/targets.py` 为准——两处必须一致，
改动时一起改，改完跑 `python scripts/check_env.py`。

### Step 2 · 「924 以来」涨幅（基准价已固化）

「924 以来」= 基准日收盘 ÷ 2024-09-24 收盘 − 1，按点位算、不含分红。2024-09-24 是那轮一揽子政策的起点日，
被当作这轮行情的原点，不要换成 9-30 或 10-08。美股 12 只同口径，基准取 **2024-09-24 美东收盘**。

**基准价已固化在 `scripts/targets.py` 里**（每个标的最后一列 base），是常量、不会变，**不要再每天取 `get_index_kline` 重复拉**。
只有新增标的时才需要补一次 kline。

### Step 3 · 历史温度（自动补，不用手动 add）

`update.py build` 会顺带把当天等权温度写进 `data/temperature-history.json`，只补新点、同日覆盖，
不用再手动跑 `node history.js add`。想看存档现状：

```bash
node scripts/history.js stat data/temperature-history.json
```

- A股/港股采样节奏：2016Q4–2025Q3 按季末，2025Q4 起按月，末点每交易日。
- 港股要记当天**实际参与平均的标的数**（第三个数）。它从 2 只长到 7 只，曲线两端不可比，图注里必须交代。
- 美股十年走势不靠每日累积，而是 `data/us-history.json` 里的**年度回溯点**（2016–2025 每年最后一个交易日）
  加上日更点拼成。要重算就改这个文件的 `points`，或者在 `years` 里改各指数分位后重算 `points`。

### Step 4 · 组装单文件 HTML（用 `update.py build`，别手贴）

```bash
python scripts/update.py build --date 2026-11-12 --out <输出目录>
# 上一交易日默认取库里该日之前最近一天，也可以 --prev 指定
```

它从明细库导出一份临时 snapshot 交给 `scripts/build.py`，后者读 `targets.py`（清单 + 924 基准）注入
`A` / `H` / `U` / `TH` / `THH` / `THU` 六个数组，并写好温度历史库。

- 卡片上的「较上一交易日」不用逐个取 56 次 prev：脚本用历史库里上一交易日的**聚合值**注入全局 `PAVG`。
- 美股卡片首日（历史库只有一个点时）显示「首日建仓 —」，这是预期行为。
- 数组字段含义和页面结构见 `references/rendering.md`。

不要重新设计版式。这套版式已经处理过的坑：多栏压缩后字号掉到 5px、极值标签压在参考线上、30°/50° 文案被末端点遮挡——重画会把这些坑重新踩一遍。
A股 / 港股 / 美股**三张走势图并排一行**（各 301×270 的 viewBox，`compact: true` 窄版、`step: 2` 隔年标年份、统计条走 `.hist-bar.trio` 的 2×2 网格）；三图顶部标题、统计条与上方三张温度卡对齐。这是 1.3.4 定的版式，别再退回「两图并排 + 美股通栏」（页高多 900px），也别把图压到 298×250 以下（字号会掉到不可读）。

### Step 5 · 导出长图

**标准产物就是高清图**（2026-10-19 定版）：默认出 2160×8340，发小红书/公众号都直接用这张，别再交 1080 的。

```bash
node scripts/export_long.js <html> <输出png>              # 高清版 2160×8340（默认）
```

playwright-core 与 Chromium 内核浏览器由脚本自动探测（环境变量 → PATH → 常见安装位置），**不需要在命令里写 `NODE_PATH` 或浏览器路径**。装之前先跑 `python scripts/runtime.py` 看本机探测结果：

```bash
python scripts/runtime.py        # 打印平台 / python / node / playwright-core / 浏览器的探测结果
```

任何一个没找到，按它的提示二选一：装（`npm i playwright-core`、装 Chrome），或指（`THERMO_NODE_MODULES`、`THERMO_CHROME` 指到已有位置）。

只有明确要小体积（微信预览、直接发聊天框）时才显式降级：

```bash
node scripts/export_long.js <html> <输出png> 1080 1080    # 轻量版 1080×4075
```

产物比例约 1:3.8（CSS 高 4170，高清版像素高 8150），PNG 约 2.0MB。参数与翻车点见 `references/export.md`。

## 日更三步（标准动作）

0. **前置检查**：金融数据 MCP 已连接（Wind 或妙想）；`python scripts/check_env.py` 无 FAIL
1. `python scripts/update.py plan` → 只列出今天还缺的代码与问句（全齐就直接跳到第 3 步）
2. 取数 → 存 `data/inbox/<日期>.json` → `python scripts/update.py apply data/inbox/<日期>.json`
3. `python scripts/update.py build --date <日期> --out <输出目录>` → 出 HTML，再按 Step 5 导出长图

第 2 步之外的都不依赖 MCP：换机器、离线重出图、补昨天的图，直接 build 就行。
**同一份数据只取一次**——重跑到 build 为止，不会再去问一遍 MCP。

## 历史存档

三个数据文件，都是**资产不是缓存**，换机器/备份优先带走 `data/` 整个目录：

| 文件 | 内容 | 谁写 |
|---|---|---|
| `data/market-data.json` | 56 标的逐日明细（chg/ytd/close/pe/t），按日期存 | `update.py apply` |
| `data/temperature-history.json` | 三组等权温度的十年序列（画曲线用） | `update.py build` 自动补点 |
| `data/us-history.json` | 美股年度回溯点（2016–2025 每年末 12 只分位，含原始 `years` 明细） | 手工维护，一般不动 |

`data/temperature-history.json` 三条序列：

```json
{
 "updated": "2026-10-16",
 "series": {
  "a":  [["2016-12-30",55.14], ["2017-03-31",56.72], ...],
  "hk": [["2016-12-30",51.36,2], ["2017-03-31",66.69,2], ...],
  "us": [["2026-11-12",47.81,12], ...]
 }
}
```

- 每点 `[日期, 温度, 参与标的数]`；A股第三位固定 37，早期点只存 `[日期, 温度]` 两位（省掉），港股必须带第三位。
- 一个点一行，方便人工复核和版本管理。
- 这个文件是**资产不是缓存**：删了就回到「必须重取 1776 次查询」的状态。换机器或备份时优先带走它。
- 从旧看板反向补录：`node scripts/history.js import <看板html> data/temperature-history.json`，会扫描 HTML 里的 `TH` / `THH` 合并进来，不覆盖其他点。

## 分发打包（两级目录限制）

平台导入 Skill 包时**只接受两级目录**：`根目录/文件` 或 `根目录/二级目录/文件`。再深一层就报
「目录层级超限 — Skill 包仅支持两级目录结构」。所以 `data/` 下不能再建子目录。

```bash
python scripts/package.py            # → dist/wj-bogle-market-thermometer-<version>.zip
python scripts/package.py --list     # 先看会打进去哪些文件
```

它会读 `SKILL.md` 的 `version:` 自动命名，按下面的规则收文件，**层级越界直接报错退出**，
写盘后再回读一遍 zip 复核：

| 排除 | 原因 |
|---|---|
| `data/archive/` | 历史原始快照，内容已全部 migrate 进 `data/market-data.json`；留着会变成三级目录 |
| `data/backup/` `data/inbox/` | 运行时产物（备份、待入库裸数据），不该进分发包 |
| `__pycache__` `dist` `.git` | 构建 / 版本控制垃圾 |
| `audit.log` `*.pyc` `*.tmp` | 流水与临时文件 |

新增数据文件时**只能放 `data/` 根下**，不要开 `data/xxx/`。

## 文件索引

| 文件 | 什么时候读 |
|---|---|
| `references/mcp-setup.md` | **第一次用必读**：Wind / 东方财富妙想 MCP 的安装与验证，自建 Wind MCP 的工具映射与自算分位 |
| `references/data-sourcing.md` | 取数前必读：Wind 官方简称核对表、调用写法、校验锚点值、数据清洗规则 |
| `references/rendering.md` | 改页面时读：数组字段、温度计 SVG 规格、走势图参数、配色与字号基线 |
| `references/export.md` | 导出长图时读：三处注入、尺寸、翻车点 |
| `data/market-data.json` | 逐日明细库（增量取数的底账），`update.py` 读写 |
| `data/temperature-history.json` | 十年走势的数据底座，build 自动补点 |
| `data/us-history.json` | 美股十年走势的年度回溯点 + 各指数原始分位 |
| `scripts/update.py` | **增量取数入口**：status / plan / apply / migrate / build / all |
| `assets/page_template.html` | 主看板模板（改数据即用） |
| `scripts/targets.py` | 单一事实源：56 标的代码/名称/分组/ETF/924 基准价，改清单只改这里 |
| `scripts/check_env.py` | 环境自检：文件完整性、标的清单一致性、依赖、MCP 人工确认清单 |
| `scripts/runtime.py` | 运行时探测：node / playwright-core / 浏览器，跨平台，不写死路径 |
| `scripts/fetch.py` | 取数计划生成器：一键输出快照串 + 56 问 + snapshot 模板 |
| `scripts/package.py` | 打分发 zip：自动校验目录层级、读版本号、排除运行时产物 |
| `scripts/build.py` | 组装 HTML：读 targets + snapshot，写历史库、注入 PAVG |
| `scripts/history.js` | 历史温度：import / add / print / stat |
| `scripts/export_long.js` | 整页长图导出 |

## 交付时说什么

温度是估值位置的模糊刻度，不是点位预测，图注和话术里都要留这句。盈利在涨的时候同样的点位温度会自己降下来——横向对比历史极值时锚点已经变了，这点要提醒。

不构成投资建议。

## 更新日志

- **1.3.5 / 2026-11-14（当前定版）**：① 博格改读图顺序——把原来压在页脚的「30 度以下 开始买入（可提高仓位）／50 度以上 开始卖出（不可提高仓位）／开始买入 ≠ 直接满仓／开始卖出 ≠ 立刻清仓」四句，提到**三张十年走势图正下方**（`.trio` 之后、分项表格之前），单独成一条 `.rule`（**字号 18px**，2×2 网格左买右卖，上下留白 26/30）；「采样口径」整段从走势图下移到**页脚最前、编制方法之前**。页面元素一块没删，只调顺序 + 把 `.foot .rule` 样式提升为通用 `.rule`。② 四句按买卖方向上色：左列买入**红** `var(--up)` #d93a33、右列卖出**蓝** #2b7fd4，圆点跟随 `currentColor`（opacity .42）——**与走势图 30°/50° 参考线颜色正好相反，这是博格指定的**，别对调。③ 页头副标题改为「**A股指数** 37 只 · **港股指数** 7 只 · **美股指数** 12 只」。页高 2160×8150 → 2160×8340（CSS 4170）。
- **1.3.4 / 2026-11-13**：博格看过 1.3.3 后要「美股十年走势跟 A股、港股并排」——把 `THU` 三图并排**加回来**，但按 1.3.1 踩过的坑重调参数：`viewBox 301×270`（列宽 (944−40)/3）、`compact` 窄版、`step: 2` 隔年标年份、`edge: 46`，美股 11 点仍用 `k: 0.16` 防过冲。三张图顶部标题、统计条与上方三张温度卡对齐；页高 2160×8216 → 2160×8150（比 1.3.1 的 8108 略高，因为图高从 250 提到 270）。
- **1.3.3 / 2026-11-13**（已被 1.3.4 取代，留档说明为什么反复）：按博格要求把版式退回「11-12 首版」——删掉美股十年走势图（`THU` 数组、`histSvg3`、`histBar3`、`histTip3` 一并移除），A股 / 港股两张走势图恢复两栏大图（viewBox 455×310，`step: 2` 隔年标年份、`mr: 96` 给右侧 30°/50° 文案留位）。页高 2160×8108 → 2160×8216。**教训：版式偏好属于主观选择，改版前先问清楚要哪一版，别靠猜。**
- **1.3.2 / 2026-11-12**：修打包。平台只接受**两级目录**（根 / 二级 / 文件），`data/archive/` 造成三级嵌套被判「目录层级超限」——该目录已从分发包剔除（12 份快照早已 migrate 进 `market-data.json`），本地保留。新增 `scripts/package.py`：打包前校验层级、按 `SKILL.md` 的 `version:` 自动命名、排除 `backup` / `inbox` / `archive` / `__pycache__` / 审计日志，写盘后回读再校验一次。
- **1.3.1 / 2026-11-12**：A股 / 港股 / 美股三张十年温度走势图改为**三栏并排**（每图 viewBox 298×250，统计条改 2×2 网格、标题竖排、字号收敛），删掉美股通栏 section；页高 2160×9042 → 2160×8108。
- **1.3.0 / 2026-11-12**：① 取数改增量——新增 `scripts/update.py`（status / plan / apply / migrate / build / all）与明细库 `data/market-data.json`，按日期存 56 只逐日数据，`plan` 只列缺口、`apply` 允许半份、写入原子 + 自动备份 + 审计流水；`fetch.py` 降级为 plan 的薄壳；`check_env.py` 改为校验明细库覆盖度与「末点=等权均值」。② 页面新增「美股 十年温度走势」通栏图（`THU`），数据来自 `data/us-history.json` 的年度回溯点（2016–2025 每年最后一个交易日的 12 只分位）+ 日更点。
- **1.2.0 / 2026-11-12**：新增美股板块——12 只（标普500、纳斯达克100 + 10 个标普500 GICS 一级行业）分项温度，温度卡改为三列，页面新增美股表格；美股「924 以来」涨幅以 2024-09-24 **美东收盘**点位为基准，与 A股、港股同口径。
- **1.1.1**：可移植性改造。新增 `scripts/runtime.py` 统一探测 node / playwright-core / 浏览器（环境变量 → PATH → 常见安装位置，覆盖 Windows / macOS / Linux），`build.py`、`check_env.py`、`export_long.js` 不再写死本机绝对路径，`export_long.js` 也不再需要 `NODE_PATH` 和 Pillow；SKILL.md 与 `references/export.md` 的命令示例同步去掉机器相关路径。
- **1.1.0 / 2026-10-28**：补上「先决条件：金融数据 MCP」一节（Wind / 东方财富妙想两条路线、`references/mcp-setup.md` 安装指南）；把 44 个标的的页面名 / Wind 代码 / **代表 ETF（表格「相关标的」列）** / 924 基准价整表写进 SKILL.md，不再依赖临时搜索；新增 `scripts/check_env.py` 环境自检；`fetch.py` 开跑即提示 MCP 前置条件。
- **1.0.0**：定版。等权口径、44 标的、2160×6904 长图、历史库只补新点。
