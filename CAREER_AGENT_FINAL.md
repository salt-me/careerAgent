# CareerAgent：正式交付入口与架构

## 正式入口

本地开发与后续容器部署都使用同一个 ASGI 入口：

```powershell
.\.venv\Scripts\python.exe -m uvicorn career_agent.career_portal_complete_asgi:app --host 127.0.0.1 --port 8000
```

浏览器访问 `http://127.0.0.1:8000/`。其他 `career_portal_*_asgi` 文件均为兼容入口；完整入口支持 TXT/DOCX 简历解析、订阅命中预览和官方 JSON 源合同。

## 已完成的产品闭环

```text
公开招聘页 / 官方 ATS / 审核后的快照
        ↓ 每日增量同步、失败重试、状态归档、历史清理
PostgreSQL（本地暂用 SQLite） ←→ Qdrant 实时 / 历史双索引
        ↓
语义召回 → 关键词重排 → 最近核验加权 → 跨来源同岗合并
        ↓
岗位详情与官方链接 → 技能覆盖/缺口解释 → 收藏、投递阶段、订阅
```

- 岗位筛选：关键词、范围、届别、校招/实习/社招、地点、公司与岗位类别。
- 信息展示：服务端和浏览器双重清理富文本 JD，页面不再显示 HTML 标签或实体编码。
- 匹配：结构化技能词表、已覆盖/待补技能、准备动作和届别建议。分数仅表示可解释的准备度，不表示录用概率。
- 个人工作台：收藏、`saved/applied/assessment/interview/offer/rejected/archived` 投递阶段和搜索订阅，使用 SQLAlchemy 表，SQLite 与 PostgreSQL 均可用。
- 治理：原始 HTML、过短 JD、未核验开放岗位、来源健康、连续失败、48 小时未成功同步、跨来源同岗候选簇。
- 生命周期：权威公开 API 源可在连续缺失后归档；不具备完整枚举能力的页面源和审核快照永远是非权威源，不会因为一次未出现而关闭岗位。

## 中国官网来源策略

已启用的百度校园招聘 SSR 源只读取官网首屏公开渲染的职位，因此为非权威源。字节跳动、快手、京东、美团、腾讯、阿里、小米、网易、联想等官网都已进入 `official_china_catalog.py` 的审核队列，但不会在未验证公开数据合同前伪装成实时源。

每一个新来源的准入条件：

1. 只读取公司官网公开页面或官方 ATS 的公开接口；不绕过登录、反爬或受保护接口。
2. 有稳定的职位 ID、官方详情/投递链接和可辨别的开放状态。
3. 只有能够完整枚举当前职位的来源才允许 `authoritative=True` 并触发关闭检测。
4. 增加 fixture、连接器测试、一次手工健康探测后才写入生产环境变量。

## Docker Desktop 恢复后的部署

Docker 文件已准备：`docker-compose.career-portal-final.yml`、`Dockerfile.career-portal-final` 和 `DEPLOY_CAREER_PORTAL.md`。Docker Desktop 安装完成后，先复制 `.env.career-platform.live.example` 为本地环境文件并设置管理员令牌，再按部署文档启动 PostgreSQL、Qdrant 和应用容器。迁移后个人收藏/投递追踪表会一并建表。

## 当前诚实边界

- 本地个人工作台尚未做账户登录/多用户隔离；`profile_key=local` 只适合单人本地使用。
- 搜索采用向量候选集合上的词法重排，不是全库 BM25；需要更大规模时可增加 PostgreSQL FTS / Qdrant sparse vector。
- 订阅目前保存检索模板。真正的邮件/企业微信推送需要用户授权一个消息渠道，不能在未授权时自动外发。
- 未验证的官网不会被算作实时数据源，更不会执行自动归档。
