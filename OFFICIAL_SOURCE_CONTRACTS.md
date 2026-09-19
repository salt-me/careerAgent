# 官方 JSON 招聘源接入

除 Greenhouse、Lever、Ashby、已启用的百度公开 SSR 页面、拼多多公开接口，以及 Shopee、JoinQuant、NVIDIA 的公开 Moka 分页接口外，CareerAgent 支持通过声明式合同接入企业自己公开的 JSON 招聘源。

1. 从 `career_agent/data/official_source_contracts.example.json` 复制一份本地合同文件。
2. 仅填写企业官网公开提供的 JSON 地址；不得使用登录后接口、受保护接口或绕过反爬的请求。
3. 用 `field_map` 映射职位 ID、标题和官方投递 URL；这三项缺一不可。
4. 只有人工确认该 feed 可完整枚举“当前开放职位”时，才同时将 `authoritative` 和 `full_enumeration_verified` 设为 `true`。
5. 设置环境变量 `CAREER_AGENT_OFFICIAL_SOURCE_CONTRACT_PATH` 指向该本地 JSON 文件，重启正式入口后它会加入每日同步和来源健康监控。

未满足第 4 条时，连接器是非权威源：同步失败或职位暂时未返回都不会自动归档现有岗位。
