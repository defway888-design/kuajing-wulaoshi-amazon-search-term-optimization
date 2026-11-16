# 全帐号客户搜索词离线看板版式

本文件只固化版式与用户指定的备货看板配色，不保存任何参考页面的数据、绝对路径或运行参数。运行时无须访问其他对话。页面与浏览器标签的标题完全为“跨境吴老师AMAZON广告搜索词优化看板”；标题下无副标题或说明行。

## 页面顺序

1. 顶部品牌标题块；可展开“数据说明”放在标题块之外，说明所选日期、时区、授权覆盖数、空报告数、SP 口径、点击降序和跨币种限制。
2. 一整行或响应式多行的五张筛选卡片：站点、国家、店铺、广告活动名称、广告组名称；另有“重置筛选”。卡片的标签、控件高度、间距、边线统一，长选项截断但展开后可读全名。
3. 全量客户搜索词区：显示当前筛选下搜索词总数、可搜索／滚动的全部搜索词列表。默认第一词为点击最多的词。每项显示搜索词、点击量、点击加权转化率；花费按站点／币种分列，不能给混币总额。列表必须可滚动或虚拟化，但不能只载入 Top10；搜索定位不改变点击降序口径。
4. 选中词的活动明细区：显示“当前筛选：<搜索词>”，按当前筛选范围内的 Profile／站点分组。每个站点内按活动点击量降序显示花费柱与点击加权 CVR 线／点；仅一个活动时只画点。含不同币种时分开图轴或分面，不混画金额。活动名称和必要的广告组名称可展开／悬停看全，内部 ID 不显示。
5. “当前关键词优化建议”：按实际情况展示主推并倾斜候选、保留测试、降低出价／限流候选、暂停／活动级否定候选、数据待核对。建议标明当前筛选范围和店铺／站点；归因未核实的暂停候选只提示暂缓执行。

不搬运备货看板的补货量、库存、FBA 商品卡、CSV 下载或运营参数模块，也不新增订单、销售、ACOS、ROAS 等指标。

## 指定配色

下列色值直接固化自用户指定对话中的紫粉备货看板。只使用这套配色及其已列出的透明度／渐变，不沿用旧版蓝白主题；业务图线可从该套强调色中选择。

```css
:root {
  --page:#3a147b; --panel:#9f78bf; --pink:#df5d9c;
  --text:#ffffff; --ink:#1a1230; --blue:#1595f9;
  --yellow:#f4fb20; --orange:#ff7a1a; --purple:#7a00a8;
  --gray:#766985; --line:rgba(255,255,255,.24);
}
html,body { background:#3a147b; }
body {
  color:#ffffff;
  background:radial-gradient(circle at 10% 8%,rgba(255,120,220,.35),transparent 28%),
             linear-gradient(135deg,#40208b 0%,#801d8e 43%,#e22075 100%);
}
.title-tile { background:linear-gradient(145deg,#5a247c,#782d8e); }
.tile { background:linear-gradient(145deg,rgba(183,126,193,.96),rgba(224,91,157,.94)); }
.panel { background:rgba(183,126,193,.88); }
.panel.pink { background:rgba(220,96,158,.90); }
.tile,.panel { border:1.5px solid #13071e; border-radius:13px; box-shadow:0 2px 0 rgba(0,0,0,.22); }
.filter-label { color:#2a1050; }
.filter-trigger,.filter-search {
  border:1px solid #3f1a58; border-radius:7px;
  background:rgba(255,255,255,.94); color:#261133;
}
.filter-menu { background:#fff; color:#261133; border:1px solid #3f1a58; }
.filter-option:hover,.filter-option:focus-visible { background:#f3d7ee; }
.filter-option[aria-selected="true"] { background:#ead0ef; }
.action-button { background:#5f2385; color:#fff; border:1px solid #251035; }
.action-button:hover { background:#752a9e; }
```

花费柱用 `#1595f9`，CVR 线和圆点用 `#ff7a1a`，主推／正向提示用同源的 `#39d98a`，测试用 `#1595f9`，暂停用 `#ff5b42`，待核用 `#766985`；高亮可用 `#f4fb20`。背景、面板、筛选控件、文字和按钮不使用其他主题色。文字与背景保持足够对比，颜色不可作为唯一状态提示。

## 对齐与交互

- 全局 `box-sizing:border-box`；字体为 Microsoft YaHei、PingFang SC、Arial、sans-serif。页面最大宽 1360px 居中。容器使用 Grid/Flex、`minmax(0,1fr)`、`min-width:0`、`overflow-wrap:anywhere`，数字用 `font-variant-numeric:tabular-nums`；不靠空格或固定字符数对齐。
- 五张筛选卡片桌面端等宽排列；空间不足时自动换行成 3＋2 或 2＋2＋1，手机端单列。筛选浮层不得被父容器裁切；按钮和搜索框最小高 38px。站点与国家联动，选项及时收窄，失效选择清除。键盘可操作、焦点可见。
- 搜索词列表与图表各自滚动，页面本身不横向溢出。图表按活动数扩展内容宽度，长活动名可换行或截断但完整名称可获得。没有数据时清空旧图和建议，显示明确空状态。
- 花费柱与每个 CVR 圆点均有自绘提示框，显示完整活动名、必要的店铺／站点、点击量、原币花费、点击加权 CVR；小圆点使用至少约 16px 半径透明命中区域。鼠标悬停和键盘聚焦显示相同数值；离开、切词、改筛选或滚动时隐藏。不要只依赖 SVG `title`。
- 所有搜索词、店铺、活动、广告组名称通过 `textContent` 或等效转义插入，防止破坏 HTML。内嵌数据时转义 `</script>` 等终止序列。文件不发网络请求，脱机筛选即时完成；大量记录可分批渲染／虚拟滚动，但数据全集必须在单文件内。

交付前检查桌面与窄屏、最长名称、五筛选交集与重置、筛选后全量重排、跨币种视图、零结果、鼠标与键盘提示框、断网打开。不得串行、错列、文字覆盖、字体不齐、坐标碰撞或页面整体横向滚动。无法实际渲染时如实说明验证上限。

