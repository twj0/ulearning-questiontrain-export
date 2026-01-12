# 二次编码的 HTML 实体问题

## 问题描述

用户反馈导出的题目中存在未解码的 HTML 实体字符，如：
- `&ldquo;` (左双引号 ")
- `&rdquo;` (右双引号 ")
- `&lt;` (小于号 <)
- `&gt;` (大于号 >)

## 原因分析

平台返回的数据中，部分 HTML 实体被**二次编码**。例如：
- 原始字符：`"`
- 一次编码：`&ldquo;`
- 二次编码：`&amp;ldquo;`

当代码只调用一次 `html.unescape()` 时：
- `&amp;ldquo;` → `&ldquo;`（停止，未完全解码）

正确的处理应该解码两次：
- `&amp;ldquo;` → `&ldquo;` → `"`

## 修复方案

在 `_strip_html` 函数中调用两次 HTML 实体解码。

### Python (formatter.py)

```python
# 修改前
s = html.unescape(s)

# 修改后
s = html.unescape(html.unescape(s))
```

### JavaScript (userscript.js)

```javascript
// 修改前
ta.innerHTML = s;
s = ta.value;

// 修改后
ta.innerHTML = s;
s = ta.value;
ta.innerHTML = s;
s = ta.value;
```

## 影响范围

- 题干 (`title`)
- 选项 (`item.title`)
- 问答题答案

## 相关文件

- `python/formatter.py` - `_strip_html()` 方法
- `UserScript/_userscript.js` - `stripHtml()` 函数
