# 固定模板渲染输入契约

领星 MCP 查询、字段核验、分页和广告组合关联按 [数据契约](data_contract.md) 完成后，再将本次结果规范化为 UTF-8 JSON。该 JSON 放在 Skill 包外、当前执行者有权写入的目录；其中允许暂存本次源 ID 供渲染器校验和重新映射，不能上传到公开仓库。渲染器不连接 MCP，也不补齐缺失业务数据。

## 顶层字段

```json
{
  "timezone": "Asia/Shanghai",
  "initialWindow": "上月",
  "dateWindows": [
    {"key":"7天","start":"2026-11-11","end":"2026-11-17"},
    {"key":"14天","start":"2026-11-04","end":"2026-11-17"},
    {"key":"本月","start":"2026-11-01","end":"2026-11-17"},
    {"key":"上月","start":"2026-10-01","end":"2026-10-31"}
  ],
  "profiles": [
    {"profileRef":"本次领星 Profile ID","site":"US","country":"美国","currency":"USD","shop":"授权店铺显示名"}
  ],
  "coverage": [
    {"profileRef":"本次领星 Profile ID","window":"7天","status":"ok"}
  ],
  "rows": [
    {"window":"7天","profileRef":"本次领星 Profile ID","query":"客户搜索词",
     "portfolioStatus":"unassigned","portfolioRef":null,
     "campaignRef":"本次领星活动 ID","campaign":"活动名称","group":"广告组名称",
     "clicks":20,"spends":12.5,"cvr":5.0}
  ]
}
```

上述值仅说明字段形状，不可直接用来生成正式看板。`coverage` 必须为**每个 Profile × 四个窗口**各有且仅有一条，`ok` 表示有真实明细，`zero` 表示经完整分页证实无明细；任一查询失败不能写 `zero`。`rows` 必须包含全部非总计明细，不能先聚合、去重或截取 Top10。每行的 `window`、`profileRef` 必须属于顶层清单，与 `coverage` 状态一致。

## 字段规则

- `profiles.profileRef`、`rows.campaignRef`、`rows.portfolioRef` 是本次源身份引用，只供渲染前区分同名实体。渲染器在输出中将 Profile 和活动映射为临时序号，并完全不写入源 ID。`site` 是站点代码；`country` 是经核实的国家显示名；`currency` 是可确定的币种代码或“站点货币”；`shop` 来自授权 `alias`。同一站点的国家与币种映射须一致。
- `query` 为报告 `query` 去首尾空格后的客户搜索词；`campaign`、`group` 分别为报告的活动、广告组名。缺失活动名可传空字符串，渲染器标记信息不完整；缺失活动 ID 用 `null`，不会将同名活动擅自合并。缺失广告组名用空字符串，不能虚构名称。
- `portfolioStatus` 只能是 `assigned` 或 `unassigned`。`assigned` 必须有本次真实组合 ID 的 `portfolioRef` 和经核验的 `portfolio` 名称；`unassigned` 仅在源数据明确证实活动未加入组合时使用，`portfolioRef` 必须为 `null`，无需 `portfolio`，页面统一显示“未加入广告组合”。字段缺失或关联失败不能记为 `unassigned`。
- `clicks` 是非负整数。`spends` 是同一 Profile 原币种的非负数；来源缺失或不可解析时传 `null`，不可填 0。`cvr` 传**百分数值**，例如 5 表示 5%；若领星已证实返回 0–1 比例，先乘 100；单位无法证实时停止 CVR 分析。缺失、越界或不可解析时传 `null`，不能填 0。数值均须有限且在 JavaScript 安全范围内。
- `dateWindows` 顺序严格为 `7天`、`14天`、`本月`、`上月`，每项使用本次执行日与时区计算的真实 `YYYY-MM-DD` 起止日。`initialWindow` 只允许四项之一；选定窗口无明细时，渲染器自动打开首个有明细的窗口。日期冻结于文件，不在浏览器打开时滚动。

`coverage` 只证明取数范围，不写入页面源 ID。JSON、HTML 都不得放进公开 Skill 包；本说明不指定任何操作系统绝对路径或创建者帐号数据。

## 唯一执行方式

在已安装本 Skill 且有 Python 3.8 或更高版本的运行环境中，将 `<skill-dir>` 换成当前安装位置，`<input-json>` 与 `<output-html>` 换成当前执行者自行选择的包外文件路径：

```text
python <skill-dir>/scripts/render_dashboard.py --input <input-json> --output <output-html>
python <skill-dir>/scripts/render_dashboard.py --input <input-json> --output <output-html> --check
```

两条命令都成功才交付。`--check` 逐字节核对现有 HTML 与固定模板、本次 Logo 和本次数据。任何错误均停止，不手改输出 HTML 补救；应修正已核实的输入或重新安装完整 Skill 包后再运行。
