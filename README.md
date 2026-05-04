# QuantTrading

个人美股量化（精简版）。回测 / 模拟盘 / 实盘共用同一套策略代码。

## 目录

```
QuantTrading/
├── strategies/   # 策略：一文件一策略
├── runners/      # 入口：backtest.py / paper.py / live.py
├── configs/      # YAML 配置（每策略一份）
├── data/         # yfinance 下载的行情缓存（gitignore）
└── tests/
```

## 快速开始

```powershell
cd F:\AAA_MyRepos\QuantTrading
uv venv
.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"

# 跑示例：双均线策略回测 SPY
python -m runners.backtest --config configs/ma_cross.yaml
```

第一次跑会从 yfinance 下载行情到 `data/`，输出累计收益、年化、最大回撤、夏普，并把 `summary.md`、`equity.png`、`equity.csv` 写到 `reports/backtest_<strategy>_<symbol>/`。

## 三种模式

| 模式 | 数据 | 下单 | 启动 |
|------|------|------|------|
| 回测 | yfinance 历史 | 本地撮合 | `python -m runners.backtest --config configs/ma_cross.yaml` |
| 模拟盘 | 实时行情 | Alpaca paper 账户 | `python -m runners.paper --config configs/ma_cross.yaml` |
| 实盘 | 实时行情 | Alpaca / IB 真实下单 | `python -m runners.live --config configs/ma_cross.yaml` |

策略代码完全相同，只换 runner。

## 写新策略

1. 复制 `strategies/ma_cross.py` 改名，实现：

    ```python
    def generate_signals(price: pd.Series, **params) -> pd.Series:
        """返回与 price 对齐的 -1/0/1 信号。"""
    ```

2. 加一个 `configs/<name>.yaml`：

    ```yaml
    strategy: <name>
    symbol: SPY
    start: 2018-01-01
    end: 2025-01-01
    params:
      fast: 20
      slow: 60
    ```

## 需要注册什么

- **回测**：什么都不用注册（yfinance 免费）
- **模拟盘**：[Alpaca](https://alpaca.markets/) 注册 → 免费 paper account → 拿 API key
- **实盘**：Alpaca 入金，或 Interactive Brokers 开户

把 key 填到 `.env`（参考 `.env.example`），代码 `os.getenv` 读。
