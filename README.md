# 宝妈指数 · 市场情绪实时监控系统

基于真实市场舆情数据的散户情绪指数可视化大屏。无 LLM 依赖，规则驱动，结果可复现。

## 核心功能

- **多源数据采集**：9 大数据源（东方财富股吧、小红书、雪球社区、Google News、网易财经、东方财富资讯、同花顺财经、AKShare 行情 & 异动）
- **宝妈指数模型**：11 项新手信号 + 6 项专业信号加权计算，映射为 0–100 情绪指数，数值越高散户化程度越强
- **40+ 板块覆盖**：T1–T4 成长梯队 / V1–V3 价值防御 / DEF 防御资产，共 7 大分类
- **实时数据大屏**：iOS 风格 UI，综合指数卡片 + 板块排行 + 历史走势折线图 + WebSocket 主动推送
- **自动采集更新**：启动即触发全量采集，每 30 分钟增量 + 全量结合自动刷新
- **数据校验机制**：溯源指纹、新鲜度检测、源健康度监控

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn + AIO SQLite |
| 前端 | Vue 3 + Pinia + Vue Router + ECharts + Vite + PWA |
| 数据采集 | AKShare + HTTP / RSS |
| 实时通信 | WebSocket 广播推送 |
| 缓存 | 内存 TTL + LRU 双层缓存 |
| 打包发布 | PyInstaller + UPX（Windows EXE） |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 一键启动（推荐）

```bash
# 安装依赖
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 后台启动前后端
python start.py start

# 查看状态 / 日志 / 停止
python start.py status
python start.py logs -f
python start.py stop
```

### 手动启动

```bash
# 后端（http://localhost:8000）
cd backend && python main.py

# 前端（http://localhost:5173）
cd frontend && npm run dev
```

API 文档：`http://localhost:8000/docs`

## 主要 API

| 接口 | 说明 |
|------|------|
| `GET /api/v1/dashboard/overview` | 大盘概览 |
| `GET /api/v1/dashboard/sector-detail?code=xxx` | 板块详情 |
| `GET /api/v1/dashboard/line-chart?sectors=xxx&days=7` | 折线图数据 |
| `GET /api/v1/dashboard/history?code=xxx&days=30` | 历史趋势 |
| `GET /api/v1/dashboard/market-data` | 行情数据（ETF + 基准指数） |
| `GET /api/v1/dashboard/etf-correlation?sector=xxx` | ETF 相关性 |
| `GET /api/v1/dashboard/capital-flow` | 市场异动概览 |
| `GET /api/v1/system/health` | 健康检查 |
| `GET /api/v1/system/collection-status` | 采集状态 |
| `WebSocket /ws` | 实时数据推送 |

## 项目结构

```
baomazhishu/
├── backend/              # FastAPI 后端
│   └── app/
│       ├── routers/      # API 路由
│       ├── database.py   # 数据库
│       ├── data_service.py # 数据服务层
│       ├── cache.py      # 缓存
│       ├── websocket.py  # WebSocket 管理
│       └── auto_collector.py # 自动采集
├── frontend/             # Vue 3 前端
│   └── src/
│       ├── views/        # 页面视图
│       ├── components/ios/ # iOS 风格组件
│       ├── stores/       # Pinia 状态
│       └── core/         # API 封装
├── collectors/           # 数据采集器（9 个数据源）
├── analyzer/             # 指数计算与规则分析
├── data/                 # 数据文件
├── tests/                # 测试
├── start.py              # 一键启动脚本
├── build_release.bat     # 发布打包脚本
└── pyproject.toml        # 项目配置
```

## 发布打包

Windows 下构建独立 EXE：

```bash
build_release.bat
```

输出目录：`dist\MomIndex\`，运行 `run.bat` 启动。
