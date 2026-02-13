# AI 基金分析助手

个人自用的基金数据看板与分析系统，提供持仓管理、净值跟踪、风险分析、规则建议和 AI 解释功能。

## 功能特性

### 核心功能

- **持仓管理** - 支持多基金持仓记录，FIFO 成本计算，加仓/减仓/清仓操作
- **净值跟踪** - 自动抓取基金净值数据，支持历史净值查询和趋势分析
- **收益分析** - 计算持仓收益率、波动率、最大回撤、夏普比率等指标
- **风险预警** - 内置规则引擎，支持集中度风险、再平衡建议等预警规则
- **AI 分析** - 集成 OpenAI 兼容 API，生成每日投资分析报告
- **数据可视化** - Streamlit 驱动的交互式数据看板

### 技术特点

- 纯 Python 技术栈，部署简单
- SQLite 轻量存储，无需外部数据库依赖
- Docker 容器化支持，一键部署
- 支持任意 OpenAI 兼容 LLM 接口

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 前端界面 | Streamlit |
| 数据库 | SQLite + SQLAlchemy |
| 数据分析 | Pandas, NumPy |
| 可视化 | Plotly |
| LLM | OpenAI 兼容 API |

## 快速开始

### 环境要求

- Python 3.11+
- pip 或 uv 包管理器

### 方式一：本地运行

```powershell
# 克隆仓库
git clone https://github.com/your-username/ai-fund-analyzer.git
cd ai-fund-analyzer

# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填写必要配置

# 初始化数据库
python scripts/init_db.py

# 启动服务
# 终端 1：启动后端
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2：启动前端
streamlit run app/ui/main.py --server.port 8501
```

### 方式二：一键启动脚本（Windows）

```powershell
# 首次启动（自动创建虚拟环境、安装依赖）
.\scripts\start.ps1

# 后续启动（跳过依赖安装）
.\scripts\start.ps1 -NoInstall

# 停止服务
.\scripts\stop.ps1
```

### 方式三：Docker 部署

```powershell
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

## 访问地址

| 服务 | 地址 |
|------|------|
| Streamlit UI | http://127.0.0.1:8501 |
| FastAPI API | http://127.0.0.1:8000 |
| 健康检查 | http://127.0.0.1:8000/health |
| API 文档 | http://127.0.0.1:8000/docs |

## 配置说明

### 环境变量

创建 `.env` 文件（可从 `.env.example` 复制）：

```env
# 应用配置
APP_NAME=AI基金分析助手
APP_VERSION=0.1.0

# 服务端口
API_HOST=127.0.0.1
API_PORT=8000
UI_PORT=8501

# 数据库配置（留空使用默认 SQLite）
DATABASE_URL=

# LLM 配置（支持 OpenAI 兼容接口）
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4
```

### LLM 配置优先级

1. `data/llm_config.json`（通过 UI 配置，优先级最高）
2. `.env` 文件配置

## 项目结构

```
ai-fund-analyzer/
├── app/
│   ├── api/              # FastAPI 路由层
│   │   └── main.py       # API 入口、健康检查、基金查询
│   ├── core/             # 核心配置
│   │   └── settings.py   # 环境变量和配置管理
│   ├── data/             # 数据层
│   │   ├── database.py   # SQLAlchemy 引擎、会话管理
│   │   └── models.py     # ORM 模型定义
│   ├── services/         # 业务服务层
│   │   ├── fund_service.py           # 基金信息管理
│   │   ├── holding_service.py        # 持仓管理（FIFO 成本计算）
│   │   ├── nav_service.py            # 净值数据管理
│   │   ├── metrics_service.py        # 指标计算
│   │   ├── rules_engine.py           # 规则引擎
│   │   ├── risk_analysis_service.py  # 技术指标分析
│   │   ├── llm_service.py            # LLM 调用封装
│   │   ├── report_service.py         # 日报生成
│   │   └── fund_data_fetcher.py      # 外部数据源抓取
│   ├── rules/            # 规则定义（预留扩展）
│   ├── llm/              # LLM 相关（预留扩展）
│   └── ui/
│       └── main.py       # Streamlit 主界面
├── scripts/
│   ├── start.ps1         # 一键启动脚本
│   ├── stop.ps1          # 停止服务脚本
│   └── init_db.py        # 数据库初始化
├── data/                 # 运行时数据目录
│   ├── app.db            # SQLite 数据库
│   └── llm_config.json   # LLM 配置
├── reports/              # 生成的分析报告
├── doc/                  # 项目文档
├── requirements.txt      # Python 依赖
├── Dockerfile            # Docker 构建文件
├── docker-compose.yml    # Docker Compose 配置
└── .env.example          # 环境变量示例
```

## 数据模型

| 模型 | 说明 |
|------|------|
| `Fund` | 基金基础信息（代码、名称、类型、经理、规模等） |
| `Holding` | 持仓记录（份额、成本、买入日期） |
| `NavHistory` | 净值历史（日期、单位净值、累计净值、涨跌幅） |
| `Transaction` | 交易流水（买入/卖出/分红，含交易后快照） |
| `Signal` | 规则触发记录（风险预警） |
| `Report` | AI 分析报告 |

## 服务层职责

| 服务 | 核心方法 |
|------|----------|
| fund_service | `get_fund_by_code()`, `get_or_create_fund()` |
| holding_service | `add_position()`, `reduce_position()`, `clear_position()`, `get_all_position_summaries()` |
| nav_service | `update_fund_nav()`, `get_nav_history()` |
| metrics_service | 收益率、波动率、最大回撤、夏普比率计算 |
| rules_engine | 集中度风险、再平衡建议等规则触发 |
| risk_analysis_service | MA 均线、RSI、动量等技术指标分析 |
| llm_service | OpenAI 兼容 API 调用封装 |
| report_service | `generate_daily_report()` |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| GET | `/api/fund/{code}` | 获取基金信息 |

## 开发约定

- 数据库操作使用 `get_db_context()` 上下文管理器
- 金额/份额使用 `Decimal` 类型确保精度
- 持仓成本计算采用 FIFO（先进先出）法
- 所有输出必须包含风险提示
- LLM 仅做解释，不直接决定买卖

## 风险提示

> **历史业绩不代表未来表现，基金投资有风险。系统输出仅为研究辅助，不构成投资建议。**

## License

MIT License - 仅供个人学习和研究使用。

## 贡献

本项目为个人自用项目，暂不接受外部贡献。如有问题或建议，欢迎提 Issue 讨论。
