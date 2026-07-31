# 宝妈指数 · 实时数据大屏系统

基于真实市场舆情数据的散户情绪指数可视化大屏系统。

## 核心功能

- **多源真实数据采集**：从东方财富股吧、Google News、网易财经、同花顺、雪球社区等9大数据源采集真实市场舆情
- **宝妈指数计算**：基于小白占比、小白强度、情绪极端度、热度信号四维模型计算各板块情绪指数（0-100）
- **实时数据大屏**：28个行业板块指数可视化（覆盖7大分类），支持折线图、雷达图、仪表盘等多种图表展示
- **行情联动分析**：ETF价格与情绪指数相关性分析，涨停池/龙虎榜异动数据追踪
- **自动采集更新**：系统启动自动触发数据采集，每30分钟增量+全量结合自动拉取
- **数据真实性校验**：完整的数据溯源、指纹校验、新鲜度检测机制

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn + AIO SQLite |
| 前端 | Vue 3 + Pinia + Element Plus + ECharts |
| 数据采集 | AKShare + Playwright + RSS / HTTP |
| 实时通信 | WebSocket 主动推送 |
| 缓存 | 内存 TTL + LRU 双层缓存 |

## 安装与运行

### 环境要求

- Python 3.10+
- Node.js 18+

### 后端启动

```bash
# 1. 安装依赖（在项目根目录执行，依赖由 pyproject.toml 统一管理）
pip install -r requirements.txt

# 2. 启动服务
cd backend
python main.py
```

后端服务默认运行在 `http://localhost:8000`

API 文档：`http://localhost:8000/docs`

> 💡 也可使用一键启动脚本：Linux/macOS/Codespaces 执行 `bash scripts/start_backend.sh`，Windows 执行 `scripts\start_backend.bat`。

### 在 GitHub Codespaces 上运行后端

本项目已配置 `.devcontainer/devcontainer.json`，可在 GitHub Codespaces 中一键启动完整的后端开发环境，无需本地安装任何依赖。

**启动步骤：**

1. 打开 GitHub 仓库页面（`https://github.com/liu-123-hub/baomazhishu`）
2. 点击绿色 **Code** 按钮 → 切换到 **Codespaces** 标签 → 点击 **`+` Create codespace on master**
3. 等待 Codespaces 自动构建（首次约 2-3 分钟，会自动安装 Python 3.11 + 项目依赖）
4. 构建完成后，在 VS Code 终端执行：

   ```bash
   bash scripts/start_backend.sh
   ```

5. 看到 `系统已启动` 提示后，Codespaces 会自动转发 8000 端口并在浏览器打开公网访问 URL

**Codespaces 环境说明：**

| 项目 | 配置 |
|------|------|
| Python 版本 | 3.11（官方 devcontainers 镜像） |
| 端口转发 | 8000（FastAPI 后端，自动公开） |
| 依赖安装 | `postCreateCommand` 自动执行 `pip install -e .[test]` |
| VS Code 扩展 | Python、Pylance、Black Formatter、YAML 自动安装 |
| 数据库 | SQLite（`backend/dashboard.db`，运行时自动创建） |

> ⚠️ Codespaces 免费额度有限（个人账户每月 120 核心小时），长时间不使用请手动停止或删除 Codespace 以节省额度。

### 前端启动

```bash
# 1. 安装依赖
cd frontend-vue
npm install

# 2. 开发模式
npm run dev

# 3. 生产构建
npm run build
```

前端默认运行在 `http://localhost:5173`

## 快速上手

1. **启动后端**：后端启动时会自动执行首次全量数据采集
2. **访问大屏**：浏览器打开前端地址，查看实时指数大屏
3. **板块浏览**：点击左侧板块分类，查看各行业宝妈指数详情
4. **趋势分析**：查看历史趋势折线图，对比多板块指数走势
5. **行情联动**：查看ETF价格与情绪指数的相关性分析

## 主要API

| 接口 | 说明 |
|------|------|
| `GET /api/v1/dashboard/overview` | 大盘概览数据 |
| `GET /api/v1/dashboard/sector-detail?code=xxx` | 板块详情 |
| `GET /api/v1/dashboard/line-chart?sectors=xxx&days=7` | 折线图数据 |
| `GET /api/v1/dashboard/history?code=xxx&days=30` | 历史趋势 |
| `GET /api/v1/dashboard/market-data` | 行情数据（ETF+基准指数） |
| `GET /api/v1/dashboard/etf-correlation?sector=xxx` | ETF相关性 |
| `GET /api/v1/dashboard/capital-flow` | 市场异动概览 |
| `GET /api/v1/system/health` | 健康检查 |
| `GET /api/v1/system/collection-status` | 采集状态 |
| `WebSocket /api/v1/ws-test/ws` | 实时数据推送 |

## 项目结构

```
mom-index/
├── backend/              # FastAPI 后端服务
│   ├── app/
│   │   ├── routers/      # API 路由
│   │   ├── database.py   # 数据库操作
│   │   ├── data_service.py # 数据服务层
│   │   ├── cache.py      # 缓存模块
│   │   ├── websocket.py  # WebSocket 管理
│   │   └── auto_collector.py # 自动采集
│   └── main.py           # 启动入口
├── frontend-vue/         # Vue 3 前端
│   └── src/
│       ├── views/        # 页面视图
│       ├── components/   # 组件
│       ├── stores/       # Pinia 状态
│       └── api/          # API 封装
├── collectors/           # 数据采集器
├── analyzer/             # 分析与指数计算
├── data/                 # 数据文件目录
└── pipeline.py           # 主流程入口
```
