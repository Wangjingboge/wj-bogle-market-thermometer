# 导出长图

## 环境

需要三样东西：**node**、**playwright-core**、**一个 Chromium 内核浏览器**。`scripts/export_long.js` 会自己找，不用在命令里写 `NODE_PATH`，也不用填浏览器路径。

先看探测结果：

```bash
python scripts/runtime.py
```

```
平台       win32
Python     3.13.12
node       C:\Program Files\nodejs\node.exe
node_mods  <含 playwright-core 的 node_modules>
Chrome     C:\Program Files\Google\Chrome\Application\chrome.exe
```

探测顺序都是「环境变量 → PATH → 常见安装位置（含 Playwright / nvm / Homebrew / Program Files）」：

| 依赖 | 环境变量 | 找不到时 |
|---|---|---|
| node | `THERMO_NODE` | 装 Node.js，或把已有 node 的绝对路径写进变量 |
| playwright-core | `THERMO_NODE_MODULES`（指向 node_modules 目录） | `npm i playwright-core` |
| 浏览器 | `THERMO_CHROME` | 装 Chrome；Windows 上会自动退到 Edge |

跑脚本：

```bash
node scripts/export_long.js <html绝对路径> <输出png> [视口宽=1080] [输出像素宽=视口宽×2]

# 标准产物：2160×6904 高清 PNG（第五个参数省略即为 2x）
node scripts/export_long.js out.html 市场温度计-2026-10-16.png
# 轻量版：1080×3452，只在要小体积时用
node scripts/export_long.js out.html 市场温度计-2026-10-16-1080.png 1080 1080
```

**默认就出高清图**（2026-10-19 定版）。第五个参数省略时按「视口宽 ×2」出图、`scale:'device'` 直接保留 2x 像素；显式传一个等于视口宽的值才走「2x 栅格化后降采样」的老路径。

## 脚本干了三件事

缺一件效果就不对。

1. **2 倍采样。** viewport 1080 + `deviceScaleFactor: 2` 渲染，小字按 2 倍分辨率栅格化。然后按输出像素宽分流：
   - `scale:'device'`（默认）→ 保留 2160×6904 原始像素。平台会二次编码成 JPEG，源图多一倍像素就有余量，压完仍锐；
   - `scale:'css'`（显式传 1080 时）→ 降采样回 1080，体积小，适合微信预览、发聊天框。
2. **注入 CSS 去掉网页外框。** 原页面有浅灰底、圆角、投影，直接截会像一张网页截图。

   ```css
   html,body{background:#FFFFFF !important;padding:0 !important;margin:0 !important;}
   .sheet{max-width:none !important;width:auto !important;border-radius:0 !important;
           box-shadow:none !important;margin:0 !important;padding:46px 46px 40px !important;}
   ```
3. **注入 JS 把交互提示改成静态语义。** 静态图里「悬停曲线可看具体日期」「点击表头可切换排序」是无效指令，删掉或改成「按行业温度降序」。

## 小红书的画质问题

博格反馈发小红书被压糊。原因有三层，对应三个解法：

1. **分辨率打平。** 上传 1080，平台可能按更长边重采样再 JPEG 编码，等于在原图上二次损伤。改成传 2160 宽，平台缩放时有 2 倍信息可用。
2. **浅灰小字最先牺牲。** JPEG 先啃低对比度细节。`td.c-idx` 从 `#b3bbc5` 提到 `#949daa`、`tnote` 从 `#a6aeb9` 提到 `#8d97a4`、`--muted` 从 `#8d97a4` 收到 `#7d8794`。看着只是「略深一点」，压完差距明显。别再往浅了调。
3. **长图比 3:4 吃亏。** 3452 高、比例 1:3.2，平台对超长图会额外降采样。真要最好效果是拆成 3:4 的多图（1242×1656×5 张），但那是另一套版式，不属于本 skill 的默认产物。

## 产物尺寸

标准产物：**2160 × 6904**，PNG 约 1.7MB，比例约 1:3.2。视口是 1080×3452，2x 像素。微信里翻三四下读完。

高度会随字号调整变化，不用追求固定值；但**CSS 高别超过 4000**（即高清图别超过 8000 像素），再长在小红书/朋友圈会被压得没法看，那种情况该拆图而不是缩字。

## 常见翻车点

| 症状 | 原因 | 解法 |
|---|---|---|
| 小字发虚、边缘毛 | 1x 直接截图 | 用 `deviceScaleFactor:2`，低分辨率场景再 `scale:'css'` |
| 小红书上传后字糊成一团 | 传的是 1080 轻量版 | 用默认（不带第五个参数）出的 2160 高清版 |
| 图里还带网页灰底和圆角 | 没注入去外框 CSS | 见上面第 2 条 |
| 出现「悬停可看…」这类提示 | 没做静态化替换 | 见上面第 3 条 |
| 表格右侧或温度计被裁 | 内容宽度 > 视口 | 减 padding 或缩组件，不要靠 `overflow` 硬切 |
| 字体变成系统黑体 | 本地 ttf 被 CORS 拦掉（仅小红书版会踩，长图用系统字体不受影响） | — |

## 交付前断言

脚本结束时会把尺寸打出来（直接读 PNG 头，不依赖 Pillow）：

```
saved 市场温度计-2026-10-16.png (2160, 6904)
```

期望宽度 2160（轻量版 1080），高度随内容浮动。想再核一遍可以：

```python
from PIL import Image
print(Image.open('市场温度计-长图.png').size)   # 期望 (2160, ~6904)；轻量版 (1080, ~3452)
```
