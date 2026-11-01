# 金融数据 MCP 安装指南（本 skill 的前置条件）

本 skill **自己不联网、不带行情数据**。它只负责「排取数计划 → 组装 HTML → 出长图」，44 个标的的估值分位数必须由外部的**金融数据 MCP** 提供。

没装 MCP 的典型症状：Step 1 拿不到任何数字，`snapshot_<日期>.json` 只能填 None，脚本能跑完但卡片和表格全是空值。

---

## 一、必须先具备的能力

| # | 能力 | 用途 | 是否可替代 |
|---|---|---|---|
| 1 | 指数行情快照：最新交易日 / 涨跌幅 / 年初至今 / 市盈率(TTM)，**一次可传 44 个代码** | 表格的「今年以来」「当日PE」、卡片核对 | 可降级为逐只查询，慢 44 倍 |
| 2 | 指数 PE(TTM) 的**近十年分位数**，且支持「指定指数 + 指定交易日」 | 温度本身，**不可缺** | 可自算（见 §2.3），但不能省 |
| 3 | 交易日历（可选） | Step 0 定基准日 | 看日历即可 |

> 只有能力 2 是真的硬门槛。分位数拿不到，这个 skill 就不成立。

---

## 二、方案 A · Wind（推荐，本 skill 默认按这套写）

本 skill 的取数问句按 **Wind 指数数据 MCP** 的两个工具写：

| 工具 | 作用 | 调用方式 |
|---|---|---|
| `get_index_price_indicators` | 指数行情快照 + PE(TTM) | `windcode` 传 44 个逗号分隔代码，`indexes` 指定字段 |
| `get_index_fundamentals` | 指数 PE(TTM) 及其近十年分位数 | 自然语言问句，**一指数一日期** |

### 2.1 走 WorkBuddy 连接器（最省事）

1. 打开左侧「专家 / 连接器」，在连接器市场搜 **Wind**（或让 agent 帮你搜）。
2. 授权你的 Wind 账号。
3. 授权完成后，工具列表里应出现 `wind-index-data` 系列（`get_index_price_indicators`、`get_index_fundamentals` 等）。
4. 回一句「查 000300.SH 在今天的 PE(TTM) 及其近10年分位数」，能返回一行数字就算通了。

### 2.2 自建 Wind MCP（有 Wind 终端、但没有现成连接器时）

前提：Windows 上装了 **Wind 金融终端**并已登录，`WindPy` 可用：

```python
from WindPy import w
w.start()
print(w.isconnected())   # 必须是 True
```

然后装一个开源的 Wind MCP（二选一）：

```bash
pip install wind-mcp          # 或 git clone https://github.com/QmQsun/Wind-MCP && pip install .
```

写进 `~/.workbuddy/mcp.json`（Windows：`C:\Users\<用户名>\.workbuddy\mcp.json`，**注意不是 `.mcp.json`**）：

```json
{
  "mcpServers": {
    "wind-mcp": {
      "command": "wind-mcp",
      "args": []
    }
  }
}
```

写完要在 WorkBuddy 的连接器页面对新服务器点一次「信任」才会加载。

### 2.3 自建 MCP 的工具映射（重要）

开源 Wind MCP 只暴露 `wind_wsd` / `wind_wss` 这类底层接口，没有现成的「指数 PE 分位数」工具。此时 Step 1 的两步要改成：

**快照（等价 get_index_price_indicators）：**

```python
# wind_wss
w.wss("801010.SI,801030.SI,000300.SH", "trade_date,close,pct_chg,ytd_pct_chg,pe_ttm",
      "tradeDate=20261028")
```

**分位数（等价 get_index_fundamentals，必须自算）：**

```python
# 1) 拉该指数近十年的逐日 PE(TTM)
d = w.wsd("000300.SH", "pe_ttm", "2016-10-28", "2026-10-28", "PriceAdj=CP")
# 2) 剔除空值，分位 = 当日 PE 在样本中的排位 / 样本数 × 100
sample = [x for x in d.Data[0] if x is not None and x == x]
today  = sample[-1]
pct    = sum(1 for x in sample if x <= today) / len(sample) * 100
```

注意三点：

- **自算的分位与 Wind 页面值不是同一个数**（页面用的是 Wind 自己的历史样本与算法），实测差异通常在 ±0.3 度以内，但**不要和历史库里已有的页面口径混着写**。要么整条序列都用自算，要么补点时接受这点小偏差并在图注里说明。
- 样本数 < 500 个交易日（约两年）的指数不进均值，规则同主文档硬规则 4。
- 一次只算一个指数，别写循环批量省事——口径乱了整条曲线报废。

---

## 三、方案 B · 东方财富妙想/妙享 MCP（没有 Wind 账号时）

妙想 MCP 依托 Choice 数据库，覆盖 A股/港股/美股/基金/指数，按积分计费。

### 3.1 官方入口

| 内容 | 地址 |
|---|---|
| 各客户端接入指南（含 WorkBuddy 图文步骤） | https://choice.eastmoney.com/mcp/guide |
| 安装说明原文（给 agent 读） | https://mxapi.eastmoney.com/mxds/doc/mcp-install.md |
| 服务端 | `https://mxapi.eastmoney.com/mxds/mcp`（StreamableHttp） |
| 认证 | HTTP Header `em_api_key: <你的 KEY>` |

### 3.2 WorkBuddy 里装（推荐三步）

1. 「专家 / 连接器」页 → 找 **妙想 MCP**（Preview）。
2. 点 MCP 加号 → 用**妙想 / Choice / 东方财富 APP 扫码**，或手机号授权登录。
3. 回到对话，在连接器里选中它 → 说「去试试」。

### 3.3 手写配置（连接器里找不到时）

Windows 路径 `C:\Users\<用户名>\.workbuddy\mcp.json`：

```json
{
  "mcpServers": {
    "mx-ds-mcp": {
      "type": "http",
      "url": "https://mxapi.eastmoney.com/mxds/mcp",
      "headers": {
        "em_api_key": "<EM_API_KEY>"
      }
    }
  }
}
```

- `em_api_key` 必须是**字面量字符串**，写 `${EM_API_KEY}` 这类占位符不会被展开。
- 写完还要在连接器页点「信任」，否则不加载。
- 其他客户端：Claude Code 写 `~/.claude.json`（或 `claude mcp add --scope user --transport http mx-ds-mcp https://mxapi.eastmoney.com/mxds/mcp --header "em_api_key: <KEY>"`），Cursor 写 `~/.cursor/mcp.json`（无需 `type` 字段）。
- KEY 属敏感凭证，别写进日志、别提交到 git。

### 3.4 用妙想跑这个 skill 的注意点

- 妙想是自然语言取数，**不一定直出「近十年分位」**。先试一句「查 000300.SH 在 2026-10-28 的市盈率PE(TTM)及其近10年分位数」；只返回 PE 不返回分位，就走 §2.3 的自算分位。
- 问句里必须写清「**指数代码 + 指数 PE(TTM) + 分位数 + 指定日期**」，否则容易返回个股或最新值。
- 仍然是**一指数一日期一问**，44 条一次并行发出，别让它自己合并成区间查询。

---

## 四、装完怎么验（两步，别跳）

```bash
python scripts/check_env.py          # 查文件完整性、标的清单、依赖
```

再到对话里问一句：

> 查 000300.SH 在 2026-10-28 的市盈率PE(TTM)及其近10年分位数

期望返回：`市盈率 ≈ 12.8`、`市盈率序号 / 市盈率最大序号`（如 1282 / 2428）、`分位数 ≈ 52.8`。三个都有，说明能力齐了。

---

## 五、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 工具列表里没有 `wind-index-data` / `mx-ds-mcp` | 写完配置没点「信任」，或没完成扫码授权 | 连接器页重新授权 / 点信任，必要时重开对话 |
| 44 条问句全返回空 | 基准日不是交易日（周末、节假日、当天未收盘） | 换成最近一个交易日 |
| 某个指数分位数是 0 或 100，且样本只有几十天 | 新指数历史太短被极值钉死 | 样本 < 500 交易日不进均值（硬规则 4） |
| 分位数整体比平时高 15–27 度 | 用了区间查询或多日期批量 | 改回「一指数一日期」，见硬规则 2 |
| 自建 Wind MCP 连不上 | Wind 终端没开 / 没登录 / Python 位数与 Wind 不匹配 | 先跑 `w.start(); w.isconnected()`，为 False 先修 WindPy |
| 妙想返回的是个股数据 | 问句没写「指数」 | 明确写「指数代码 XXX 的指数 PE(TTM) 分位」 |
