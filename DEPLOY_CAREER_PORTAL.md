# CareerAgent 最终门户部署

推荐运行入口：`career_agent.career_portal_complete_asgi:app`。

它包含 Greenhouse、Lever、Ashby 的显式白名单连接器，启用后的百度官方 2027 届校招页面、拼多多校招公开接口、联想中国官网公开职位接口，以及 Shopee、JoinQuant、NVIDIA 官方 Moka 招聘板块连接器，以及求职者门户、管理后台和每日同步调度。

## 1. 一次性的 Windows 前置

本机已启用 WSL2。请重启 Windows 一次，然后安装并启动 Docker Desktop；首次启动选择 WSL2 backend 并等待状态显示为 Running。

## 2. 准备环境文件

在项目根目录复制现有的 `.env.career-platform.example` 为 `.env.career-platform`，把 `CAREER_AGENT_ADMIN_TOKEN` 改为随机长字符串。该示例已启用百度的公开 SSR 校招页、拼多多校招公开分页接口、联想中国官网公开职位接口，以及 Shopee、JoinQuant、NVIDIA 官方 Moka 的完整分页招聘板块。联想和三家 Moka 来源按权威源处理；百度和拼多多仍为非权威源，绝不会因分页、抓取异常或职位暂时从列表消失而自动关闭职位。

不要把真实 `.env.career-platform` 提交到 Git。

## 3. 启动长期服务

```powershell
docker compose -f docker-compose.career-portal-final.yml up --build -d
docker compose -f docker-compose.career-portal-final.yml ps
```

访问：

- `http://localhost:8000/`：求职者搜索、岗位选择和简历匹配
- `http://localhost:8000/admin`：来源健康、质量报告、同步管理
- `http://localhost:8000/docs`：API 文档

## 4. 首次同步与验收

```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/admin/sync -H "X-Admin-Token: <你的令牌>"
```

每次成功同步后，官方来源中的开放岗位进入实时索引；连续两次成功同步都不再出现的 authoritative ATS 岗位会归档。联想、Shopee、JoinQuant 和 NVIDIA 的招聘板块都读取官网公开接口的完整分页列表，因此按 authoritative 处理；百度只读取官网首屏、拼多多尚未验收“列表消失即关闭”的生命周期语义，二者仍为 non-authoritative。

华为、OPPO、Bambu Lab、DJI、智元机器人、普渡科技、科大讯飞、Ubiquant 与腾讯音乐的官方招聘入口已登记在 `/api/career/source-catalog`。百度、拼多多、联想、Shopee、JoinQuant 和 NVIDIA 的公开板块已启用实际同步。个人中心、投递记录、内推码和带分享令牌的地址不会被写入采集配置；其余每个来源仍须完成公开列表、稳定职位 ID、分页和关闭语义的连接器验收后才会启用同步。
