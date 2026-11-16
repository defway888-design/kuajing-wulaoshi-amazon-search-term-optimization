# 两阶段渲染与按钮回传契约

只使用当前平台的领星 MCP。输入、运行中选择、状态及 HTML 均写在 Skill 包外、当前执行者可写的本次新建运行目录。不得把源 ID、报告、凭据或看板提交到公开仓库。Python 3.8+ 标准库脚本不连接 MCP；广告接口由运行中的 Agent 调用。

## 第一阶段：授权清单与三项筛选

先调用 `ad_auth_shops` 并验证全部授权 Profile。计算本次真实的四个日期窗口（`7天`、`14天`、`本月`、`上月`），按下列形状写授权输入；示意值不可作为真实输入：

```json
{
  "timezone":"Asia/Shanghai",
  "initialWindow":"上月",
  "dateWindows":[
    {"key":"7天","start":"2026-11-11","end":"2026-11-17"},
    {"key":"14天","start":"2026-11-04","end":"2026-11-17"},
    {"key":"本月","start":"2026-11-01","end":"2026-11-17"},
    {"key":"上月","start":"2026-10-01","end":"2026-10-31"}
  ],
  "profiles":[{"profileRef":"当前授权 Profile ID","site":"US","country":"美国","shop":"当前授权店铺显示名"}]
}
```

`profileRef` 仅用于 Agent 内部身份核对；渲染器把它重映射为 `p1` 等临时键，页面不含源 ID。第一阶段输入不得包含 `coverage` 或 `rows`，不得预查搜索词报告。国家显示名和站点映射必须经核实且一一对应；同一站点或同一国家名称不能映射到多个不同值。站点代码仅供内部查询与校验，不生成独立筛选卡片。

```text
python <skill-dir>/scripts/render_dashboard.py --phase selection --input <auth-input-json> --output <selection-html>
python <skill-dir>/scripts/render_dashboard.py --phase selection --input <auth-input-json> --output <selection-html> --check
python <skill-dir>/scripts/selection_bridge.py --input <auth-input-json> --page <selection-html> --choice <choice-json> --final <final-html> --status-file <status-json> --ready <ready-url-file>
```

桥接脚本在 `127.0.0.1` 的动态端口启动，并将 URL 写入 `<ready-url-file>`。在当前运行环境的浏览器打开该 URL，不能以 `file://` 打开第一阶段页面。Agent 保持本次任务运行并等待内部选择文件出现；若平台不允许持续运行本地服务和等待用户点击，说明交互回传能力不足并停止，不能假装按钮已启动第二阶段。用户无需下载或上传文件。

点击“运行并生成看板”后，页面以 `POST /run` 提交 `{date,site,country,store}`：用户只选择日期、国家和店铺，`site` 由国家选项内部的代码派生，不能独立选择。服务仅接受同源提交，校验日期、国家／站点映射和店铺归属。空 `site`/`country` 表示全部国家／站点，空 `store` 表示当前国家范围内全部店铺。选择写入 Agent 内部 `<choice-json>`；这个文件不由用户处理。页面轮询 `/status`。失败时 Agent 将 `{"state":"error","message":"实际失败原因"}` 写入 `<status-json>`，由页面显示。

## 第二阶段：所选范围的完整报告

Agent 读取内部选择文件，在本次授权清单中核对临时店铺键，取得所选 Profile 集合。只对所选日期窗口 × 命中的每个 Profile 调用完整分页的商品推广搜索词报告；广告组合关联、数值清洗和停止条件按 [数据契约](data_contract.md)。不得把未选日期或店铺的数据写进正式输入。按下列形状写报告输入；示意值不可作为真实数据：

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

`selectedScope` 的 `date`、`site`、`country` 必须等于按钮提交值；若店铺选“全部”，`profileRef` 为 `null`，`profiles` 包含全部命中的授权 Profile。若选单店铺，`profileRef` 为其真实 ID，`profiles` 仅含该店铺。`coverage` 对每个所选 Profile 恰有一条；`ok` 为确有明细，`zero` 为经全分页确认无明细，失败不可写 `zero`。`rows` 保留全部非总计明细，不去重、不提前聚合、不截 Top10，且每行属于所选窗口与 Profile。所有 Profile 均零记录时停止。

`query` 仅为客户搜索词。`clicks` 为非负整数；`spends` 和 `cvr` 缺失或不可解析时传 `null`，不得补零。`cvr` 为确认后的百分数值，5 表示 5%。`portfolioStatus=assigned` 时必须有真实 `portfolioRef` 和核验后的 `portfolio` 名称；`unassigned` 只用于已证明未加入组合的活动。活动 ID 仅用于区分同名实体；缺失可传 `null`，活动名缺失可传空字符串，不能臆造。货币必须有可靠来源或明确的站点货币标识。

```text
python <skill-dir>/scripts/render_dashboard.py --phase final --input <report-input-json> --output <candidate-html>
python <skill-dir>/scripts/render_dashboard.py --phase final --input <report-input-json> --output <candidate-html> --check
```

正式 HTML 先生成到临时文件并通过 `--check`；之后将其发布到服务参数指定的 `<final-html>`，最后把 `{"state":"ready"}` 写入 `<status-json>`。只有两个条件都满足，服务的 `/status` 才返回就绪，让浏览器打开 `/final`。正式文件本身是完整离线 HTML，不依赖桥接服务；另在对话中给出该文件链接。页面只含所选日期窗口的数据，若需其他窗口须重新运行第一阶段。两阶段均使用同一包内母版；模板指纹或逐字节校验失败时停止，不能手改 HTML 补救。
