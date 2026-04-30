# QuantTrading

个人量化交易系统骨架。**回测 / 模拟盘 / 实盘** 共用同一套策略代码，只切换执行后端。

## 目录速览

| 目录 | 作用 |
|------|------|
| `src/quant/core/` | 核心抽象：`Strategy` / `Broker` / `ExecutionEngine` / `Event` |
| `src/quant/data/` | 行情数据接入（akshare / tushare / qmt / ccxt …） |
| `src/quant/factors/` | 因子库 |
| `src/quant/strategies/` | 策略实现（**一策略一目录** + 自带 README） |
| `src/quant/backtest/` | 回测引擎 / vectorbt 适配 |
| `src/quant/execution/` | 下单层：`BacktestExec` / `PaperExec` / `LiveExec` |
| `src/quant/broker/` | 券商 API 封装 |
| `src/quant/risk/` | 风控（仓位、止损、限额） |
| `src/quant/portfolio/` | 组合层（多策略合成、净值） |
| `src/quant/monitor/` | 实盘监控 / 报警 |
| `src/quant/utils/` | 公共工具（日志、时间、IO） |
| `configs/` | YAML 配置：`base.yaml` ← `env/{env}.yaml` ← `strategies/{name}.yaml` ← CLI |
| `scripts/` | CLI 入口（不写业务，只拼对象） |
| `notebooks/` | 研究 & 复盘 |
| `data/` | 本地缓存（gitignore） |
| `reports/` | 回测/实盘报告（实盘 equity 不入 git） |
| `logs/` | 运行日志（gitignore） |
| `tests/` | pytest |

## 快速开始

```powershell
# 1. 创建虚拟环境（用 uv）
cd F:\AAA_MyRepos\QuantTrading
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e .

# 2. 复制 .env
copy .env.example .env

# 3. 跑一个示例回测
python -m scripts.run_backtest --strategy ma_cross

# 4. 模拟盘（接券商 sandbox 或本地实时撮合）
python -m scripts.run_paper --strategy ma_cross

# 5. 实盘（带二次确认）
python -m scripts.run_live --strategy ma_cross
```

## 三种运行模式

| 模式 | Broker | 行情 | 订单 |
|------|--------|------|------|
| `backtest` | `BacktestBroker` | 历史数据 | 历史撮合 |
| `paper` | `PaperBroker` | **真实实时行情** | 本地撮合，不真下单 |
| `live` | `LiveBroker`（QMT/IB/CCXT） | 真实实时行情 | **真实下单** |

策略代码不区分模式。切换只改 `--env` 或 `configs/env/*.yaml`。

## 开发约定

- 包根：`from quant.xxx import ...`（src layout）
- 配置覆盖顺序：`base.yaml` → `env/{env}.yaml` → `strategies/{name}.yaml` → CLI
- 密钥：写 `.env`，代码用 `os.getenv` 读，永不入 git
- 新策略：复制 `src/quant/strategies/ma_cross/` 改名即可
- 提交前：`pytest -q` + `ruff check .`
