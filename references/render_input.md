# 对话内选择与正式看板渲染契约

只使用当前平台的领星 MCP。第一阶段在运行 Skill 的同一对话内完成，不生成筛选 HTML、选择文件或本地服务。规范化报告 JSON 和最终 HTML 写在 Skill 包外、当前执行者可写的本次运行目录；不得把源 ID、报告、凭据或真实看板提交到公开仓库。Python 3.8+ 标准库渲染脚本不连接 MCP，广告接口由 Agent 调用。

## 第一阶段：授权清单与对话内三项选择

先调用 `ad_auth_shops` 并验证全部授权 Profile。按用户所在时区计算本次真实的四个日期窗口：`7天`、`14天`、`本月`、`上月`。在当前对话内用平台原生选择控件或文字选项收集**统计日期、国家、店铺**，不显示独立站点筛选。国家、店铺选项必须来自当前授权响应，允许各自选“全部”；店铺选项标明所属国家，若同名同国授权记录无法区分，不擅自选择其中一个。

用户提交三项后，Agent 校验日期是四个固定值之一、国家与内部站点代码一一对应、店铺属于所选国家且唯一可辨。选“全部国家”时内部 `site` 和 `country` 均为空字符串；选“全部店铺”时内部 `profileRef` 为 `null`。不得把界面预设值当作已提交，不得在提交前读取搜索词报告。用户在启动指令中已明确给出完整有效条件时，可直接视为本次提交。缺失或冲突只在同一对话内追问，不跳转浏览器，也不要求下载、上传或粘贴文件。

## 第二阶段：所选范围的完整报告

Agent 用对话中提交的选择重新核对当前授权清单，取得所选 Profile 集合。只对所选日期窗口 × 命中的每个 Profile 调用完整分页的商品推广搜索词报告；广告组合关联、数值清洗和停止条件按 [数据契约](data_contract.md)。不得把未选日期或店铺的数据写进正式输入。按下列形状写报告输入；示意值不可作为真实数据：

```json
{
  "timezone":"Asia/Shanghai",
  "dateWindows":[
    {"key":"7天","start":"2026-11-11","end":"2026-11-17"},
    {"key":"14天","start":"2026-11-04","end":"2026-11-17"},
    {"key":"本月","start":"2026-11-01","end":"2026-11-17"},
    {"key":"上月","start":"2026-10-01","end":"2026-10-31"}
  ],
  "selectedWindow":"上月",
  "selectedScope":{"date":"上月","site":"US","country":"美国","profileRef":"当前所选 Profile ID"},
  "profiles":[{"profileRef":"当前所选 Profile ID","site":"US","country":"美国","currency":"USD","shop":"当前授权店铺显示名"}],
  "coverage":[{"profileRef":"当前所选 Profile ID","window":"上月","status":"ok"}],
  "rows":[{"window":"上月","profileRef":"当前所选 Profile ID","query":"客户搜索词",
    "portfolioStatus":"unassigned","portfolioRef":null,
    "campaignRef":"本次活动 ID","campaign":"活动名称","group":"广告组名称",
    "clicks":20,"spends":12.5,"cvr":5.0}]
}
```

`selectedScope` 的 `date`、`site`、`country` 必须等于对话中确认的选择及其内部站点映射；若店铺选“全部”，`profileRef` 为 `null`，`profiles` 包含全部命中的授权 Profile。若选单店铺，`profileRef` 为其真实 ID，`profiles` 仅含该店铺。`coverage` 对每个所选 Profile 恰有一条；`ok` 为确有明细，`zero` 为经全分页确认无明细，失败不可写 `zero`。`rows` 保留全部非总计明细，不去重、不提前聚合、不截 Top10，且每行属于所选窗口与 Profile。所有 Profile 均零记录时停止。渲染器把源身份重映射为无源信息临时键，页面不含源 ID。

`query` 仅为客户搜索词。`clicks` 为非负整数；`spends` 和 `cvr` 缺失或不可解析时传 `null`，不得补零。`cvr` 为确认后的百分数值，5 表示 5%。`portfolioStatus=assigned` 时必须有真实 `portfolioRef` 和核验后的 `portfolio` 名称；`unassigned` 只用于已证明未加入组合的活动。活动 ID 仅用于区分同名实体；缺失可传 `null`，活动名缺失可传空字符串，不能臆造。货币必须有可靠来源或明确的站点货币标识。

```text
python <skill-dir>/scripts/render_dashboard.py --input <report-input-json> --output <final-html>
python <skill-dir>/scripts/render_dashboard.py --input <report-input-json> --output <final-html> --check
```

正式 HTML 生成后必须通过 `--check`，再在同一对话提供文件链接；文件是完整离线 HTML，不依赖运行时服务。页面只含所选日期窗口的数据，若需其他窗口须在当前对话重新选择并运行。模板指纹或逐字节校验失败时停止，不能手改 HTML 补救。
