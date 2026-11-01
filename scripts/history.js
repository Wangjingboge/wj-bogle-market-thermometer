// 历史温度存档 —— 十年走势的数据底座
//
// 用法:
//   node history.js import <看板html> <history.json>          从看板抽 TH/THH 合并进存档
//   node history.js add <history.json> <a|hk> <日期> <温度> [标的数]
//   node history.js print <history.json> [a|hk]               打印成可直接贴回模板的 JS 数组
//   node history.js stat <history.json>                       看区间、点数、极值
//
// 设计约定：
//   - 同一日期以最后写入的为准（重取修正坏点时不用先删）
//   - 始终按日期升序保存，末点即最新
//   - A股每点的第三个数固定是 37；港股记当天实际参与平均的标的数
const fs = require('fs');
const path = require('path');

const [, , cmd, ...args] = process.argv;

function die(msg) { console.error(msg); process.exit(1); }

function load(file) {
  if (!fs.existsSync(file)) {
    return { updated: null, series: { a: [], hk: [] } };
  }
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  j.series = j.series || {};
  j.series.a = j.series.a || [];
  j.series.hk = j.series.hk || [];
  return j;
}

function save(file, db) {
  const dir = path.dirname(path.resolve(file));
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  // 归一：去重（后写覆盖）、按日期升序
  for (const k of ['a', 'hk']) {
    const map = new Map();
    for (const row of db.series[k]) {
      if (!Array.isArray(row) || row.length < 2) continue;
      const [d, v, n] = row;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) die(`日期格式不对: ${d}`);
      const val = Number(v);
      if (!(val >= 0 && val <= 100)) die(`温度越界(0-100): ${d} = ${v}`);
      map.set(d, [d, Math.round(val * 100) / 100, n === undefined ? undefined : Number(n)]);
    }
    db.series[k] = [...map.values()]
      .sort((x, y) => x[0].localeCompare(y[0]))
      .map(r => (r[2] === undefined ? [r[0], r[1]] : [r[0], r[1], r[2]]));
  }
  const last = ['a', 'hk'].map(k => db.series[k][db.series[k].length - 1]?.[0]).filter(Boolean).sort().pop();
  db.updated = last || db.updated;
  // 一个点一行，方便人工复核和 git diff
  const text = '{\n'
    + ` "updated": ${JSON.stringify(db.updated)},\n`
    + ' "series": {\n'
    + ['a', 'hk'].map(k =>
        `  "${k}": [\n` + db.series[k].map(r => '   ' + JSON.stringify(r)).join(',\n') + '\n  ]'
      ).join(',\n')
    + '\n }\n}\n';
  fs.writeFileSync(file, text, 'utf8');
  return db;
}

// 从看板 HTML 里扫出 const X = [...]，逐字符配对 ]，避免嵌套数组被正则截断
function sliceArray(src, name) {
  const i = src.indexOf(`const ${name} = [`);
  if (i < 0) return null;
  const from = src.indexOf('[', i);
  let depth = 0, end = -1;
  for (let k = from; k < src.length; k++) {
    if (src[k] === '[') depth++;
    else if (src[k] === ']') { depth--; if (depth === 0) { end = k; break; } }
  }
  const text = src.slice(from, end + 1)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
  return eval('(' + text + ')');
}

if (cmd === 'import') {
  const [html, file] = args;
  if (!html || !file) die('usage: node history.js import <board.html> <history.json>');
  const src = fs.readFileSync(html, 'utf8');
  const db = load(file);
  let cnt = 0;
  for (const [key, name] of [['a', 'TH'], ['hk', 'THH']]) {
    const arr = sliceArray(src, name);
    if (!arr) { console.warn(`跳过 ${name}：看板里没找到`); continue; }
    for (const row of arr) db.series[key].push(row);
    cnt += arr.length;
    console.log(`${name}: 导入 ${arr.length} 点`);
  }
  const out = save(file, db);
  console.log(`已合并到 ${file}：A股 ${out.series.a.length} 点 / 港股 ${out.series.hk.length} 点（本次读入 ${cnt}）`);
}

else if (cmd === 'add') {
  const [file, key, date, value, n] = args;
  if (!file || !key || !date || value === undefined) {
    die('usage: node history.js add <history.json> <a|hk> <YYYY-MM-DD> <温度> [标的数]');
  }
  if (!['a', 'hk'].includes(key)) die('系列只能是 a 或 hk');
  const db = load(file);
  db.series[key].push([date, Number(value), n === undefined ? undefined : Number(n)]);
  const out = save(file, db);
  const pts = out.series[key];
  console.log(`已写入 ${key} ${date} = ${value}，当前 ${pts.length} 点，末点 ${pts[pts.length - 1][0]}`);
}

else if (cmd === 'print') {
  const [file, key] = args;
  if (!file) die('usage: node history.js print <history.json> [a|hk]');
  const db = load(file);
  const keys = key ? [key] : ['a', 'hk'];
  for (const k of keys) {
    const name = k === 'a' ? 'TH' : 'THH';
    const rows = db.series[k];
    // 与模板里的书写风格保持一致：单引号日期、逗号后一个空格
    const fmt = r => `['${r[0]}', ${r[1]}${r[2] !== undefined ? ', ' + r[2] : ''}]`;
    const body = rows.map(r => '  ' + fmt(r)).join(',\n');
    console.log(`const ${name} = [\n${body},\n];`);
  }
}

else if (cmd === 'stat') {
  const [file] = args;
  if (!file) die('usage: node history.js stat <history.json>');
  const db = load(file);
  for (const k of ['a', 'hk']) {
    const rows = db.series[k];
    if (!rows.length) { console.log(`${k}: 空`); continue; }
    const vals = rows.map(r => r[1]);
    const hi = rows.reduce((a, b) => (b[1] > a[1] ? b : a));
    const lo = rows.reduce((a, b) => (b[1] < a[1] ? b : a));
    const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
    console.log(`${k.toUpperCase()}  ${rows.length} 点  ${rows[0][0]} → ${rows[rows.length - 1][0]}`);
    console.log(`   均值 ${mean.toFixed(2)}  最高 ${hi[1].toFixed(2)} (${hi[0]})  最低 ${lo[1].toFixed(2)} (${lo[0]})  末点 ${rows[rows.length - 1][1]}`);
  }
  console.log(`最近更新 ${db.updated}`);
}

else {
  console.log(`历史温度存档工具

  node history.js import <看板html> <history.json>          从看板抽 TH/THH 合并进存档
  node history.js add <history.json> <a|hk> <日期> <温度> [标的数]
  node history.js print <history.json> [a|hk]               打印成 JS 数组，贴回模板
  node history.js stat <history.json>                       区间 / 点数 / 极值`);
}
