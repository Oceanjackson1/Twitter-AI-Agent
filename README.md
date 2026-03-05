# Twitter AI Agent (CryptoEye)

基于 Telegram 的多功能加密货币监控与分析机器人 (CryptoEye Agent)。集成了推特监控、实时加密新闻聚合以及 DeepSeek AI 深度分析功能，支持中英双语。

## 核心功能

### 📰 新闻与资讯追踪
- **实时新闻 (`/news`)** — 获取最新的加密货币市场新闻，支持按数量或关键词直接搜索
- **精准搜索 (`/search_news`)** — 按关键词精确检索新闻
- **币种新闻 (`/coin_news`)** — 获取特定币种相关新闻
- **高分推荐 (`/hot_news`)** — AI 评分 70+ 的核心重大新闻精选
- **交易信号 (`/signal`)** — 按做多 (Long) / 做空 (Short) / 中性 (Neutral) 筛选信号新闻
- **全网信源 (`/sources`)** — 查看当前系统接入的所有新闻来源

### 🐦 推特深度监控
- **用户资料 (`/tw_user`)** — 获取目标推特用户基本资料
- **最新推文 (`/tw_tweets`)** — 获取用户最新推文及互动数据
- **推文搜索 (`/tw_search`)** — 按关键词搜索推文
- **已删除推文 (`/tw_deleted`)** — 获取被用户删除的敏感推文
- **KOL 粉丝 (`/tw_kol`)** — 分析用户的 KOL 粉丝
- **关注事件 (`/tw_followers`)** — 监控关注 / 取关动作，追踪聪明钱动向

### 🤖 AI 智能问答与分析 (DeepSeek)
- **自由问答 (`/ask`)** — 带短期记忆的 AI 问答，支持上下文连续对话
- **深度分析 (`/analyze`)** — 指定币种或话题，生成 AI 深度分析报告
- **每日简报 (`/briefing`)** — AI 生成每日市场总结

### 🔔 自动化监控任务
- **创建任务 (`/monitor`)** — 创建支持多账号的监控任务，可选择私聊、群组或 Webhook 推送
- **群组绑定 (`/monitor_bind`)** — 将监控推送绑定至 Telegram 群组
- **任务管理 (`/monitors`, `/unmonitor`)** — 查看或移除现有监控任务
- **CSV 导出 (`/export_csv`)** — 将监控任务的历史数据导出为 CSV 文件

### ⚙️ 账户与设置
- **双语切换 (`/lang`)** — 中文 / English 无缝切换
- **偏好配置 (`/settings`)** — 每日最大告警数、免打扰时段等个性化设置
- **个人档案 (`/me`)** — 查看账户状态与配置信息

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| Bot 框架 | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 22.5 |
| 数据库 | aiosqlite (异步 SQLite) |
| HTTP 客户端 | httpx |
| AI 引擎 | DeepSeek API |
| 数据源 | Twitter API + OpenNews API (ai.6551.io) |
| 容器化 | Docker + Docker Compose |

---

## 部署指南

### 1. 克隆项目

```bash
git clone https://github.com/Oceanjackson1/Twitter-AI-Agent.git
cd Twitter-AI-Agent
```

### 2. 配置环境变量

复制 `.env.example` 并填入密钥：

```bash
cp .env.example .env
```

必填项：

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENNEWS_TOKEN=your_opennews_api_token
TWITTER_TOKEN=your_twitter_api_token
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 3a. Docker 部署 (推荐)

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

### 3b. 本地运行

```bash
pip install -r requirements.txt
python main.py
```

控制台输出 `Bot initialized with bilingual command menus` 即表示启动成功。

---

## 目录结构

```
Twitter-AI-Agent/
├── bot/                  # Telegram Bot 核心逻辑
│   ├── commands/         # 命令处理器 (news, twitter, monitor, ai, account)
│   ├── callbacks/        # 内联键盘回调 (语言切换、翻页、监控配置)
│   └── application.py    # Bot 初始化、handler 注册、生命周期管理
├── db/                   # 异步 SQLite 数据层
│   ├── database.py       # 建表与连接管理
│   ├── user_repo.py      # 用户数据
│   ├── monitor_repo.py   # 监控订阅数据
│   ├── monitor_job_repo.py # 监控任务数据
│   ├── alert_repo.py     # 告警记录
│   └── ai_repo.py        # AI 对话记忆
├── services/             # 外部服务接口
│   ├── news_api.py       # OpenNews API 客户端
│   ├── twitter_api.py    # Twitter API 客户端
│   ├── deepseek.py       # DeepSeek AI 客户端
│   ├── monitor_service.py # 定时轮询监控服务
│   ├── csv_exporter.py   # CSV 导出服务
│   └── heartbeat.py      # Pixel Office 心跳上报
├── i18n/                 # 国际化 (中文 zh.py / 英文 en.py)
├── utils/                # 工具函数 (格式化、校验、进度条)
├── tests/                # 测试
├── scripts/              # 辅助脚本
├── config.py             # 环境变量加载
├── main.py               # 启动入口
├── Dockerfile            # Docker 镜像定义
├── docker-compose.yml    # Docker Compose 编排
└── requirements.txt      # Python 依赖
```

---

## License

MIT
