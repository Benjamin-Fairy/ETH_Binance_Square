import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from pathlib import Path

# ======================================================
# Global configuration
# ======================================================
# rcParams['font.family'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
# rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = Path("./figures")
OUTPUT_DIR.mkdir(exist_ok=True)

EMA_FAST = 20
EMA_SLOW = 50
ATR_PERIOD = 14
STOP_LOSS_ATR = 1.2
TAKE_PROFIT_ATR = 2.0
MAX_HOLD_BARS = 48


# ======================================================
# Utility
# ======================================================
def get_recent_days_safe(df, days):
    if df.empty:
        return df
    end = df.index.max()
    start = end - pd.Timedelta(days=days)
    return df.loc[start:end]


# ======================================================
# Data loading & preparation
# ======================================================
def load_klines(files):
    data = []
    for f in files:
        with open(f, "r", encoding="utf-8-sig") as fp:
            data.extend(json.load(fp))

    df = pd.DataFrame(
        data,
        columns=[
            "open_time","open","high","low","close","volume",
            "close_time","quote_volume","trade_num",
            "taker_buy_volume","taker_buy_quote","ignore"
        ]
    )

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df[["open","high","low","close","volume"]] = df[
        ["open","high","low","close","volume"]
    ].astype(float)

    return df.set_index("open_time").sort_index()


def resample_ohlcv(df, rule="15min"):
    return df.resample(rule).agg({
        "open":"first","high":"max","low":"min",
        "close":"last","volume":"sum"
    }).dropna()


def add_indicators(df):
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()

    df["EMA20"] = df["close"].ewm(span=EMA_FAST).mean()
    df["EMA50"] = df["close"].ewm(span=EMA_SLOW).mean()

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs()
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(ATR_PERIOD).mean()
    return df


# ======================================================
# EMA pullback backtest (unchanged)
# ======================================================
def backtest_ema_pullback(df):
    position = False
    entry_price = None
    entry_time = None
    entry_bar = None
    stop_loss = None
    take_profit = None

    trades = []

    for i in range(EMA_SLOW + 2, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not position:
            trend_ok = row["EMA20"] > row["EMA50"]
            pullback = prev["close"] < prev["EMA20"] and row["close"] > row["EMA20"]

            if trend_ok and pullback:
                position = True
                entry_price = row["close"]
                entry_time = row.name
                entry_bar = i
                stop_loss = entry_price - STOP_LOSS_ATR * row["ATR"]
                take_profit = entry_price + TAKE_PROFIT_ATR * row["ATR"]

        elif position:
            hold_bars = i - entry_bar

            if (
                row["low"] <= stop_loss or
                row["high"] >= take_profit or
                hold_bars >= MAX_HOLD_BARS
            ):
                exit_price = row["close"]
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": row.name,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": exit_price - entry_price
                })
                position = False

    return pd.DataFrame(trades)


# ======================================================
# Price chart (NO trade markers at all)
# ======================================================
def plot_price_only(df, days, filename, title):
    df_plot = get_recent_days_safe(df, days)
    fig, ax = plt.subplots(figsize=(16, 8))

    bar_width = pd.Timedelta(minutes=10)

    for t, r in df_plot.iterrows():
        color = "green" if r["close"] >= r["open"] else "red"
        ax.plot([t, t], [r["low"], r["high"]], color=color)
        ax.bar(
            t,
            r["close"] - r["open"],
            bottom=r["open"],
            width=bar_width,
            color=color
        )

    ax.plot(df_plot.index, df_plot["MA20"], label="MA20", alpha=0.5)
    ax.plot(df_plot.index, df_plot["MA60"], label="MA60", alpha=0.5)

    ax.set_title(title)
    ax.legend()
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close(fig)


# ======================================================
# 7-day backtest summary (separate figure)
# ======================================================
def plot_backtest_summary(trades, filename):
    if trades.empty:
        print("No trades in 7-day window.")
        return

    trades = trades.copy()
    trades["cum_pnl"] = trades["pnl"].cumsum()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(trades["exit_time"], trades["cum_pnl"], linewidth=2)

    stats_text = (
        f"Trades: {len(trades)}\n"
        f"Win rate: {(trades['pnl'] > 0).mean():.2%}\n"
        f"Total PnL: {trades['pnl'].sum():.2f}\n"
        f"Avg PnL: {trades['pnl'].mean():.2f}"
    )

    ax.text(
        0.02, 0.98,
        stats_text,
        transform=ax.transAxes,
        va="top",
        bbox=dict(facecolor="white", alpha=0.85)
    )

    ax.set_title("ETH-USDT 15m – 7 Days Backtest Result")
    ax.set_ylabel("Cumulative PnL")
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close(fig)


# ======================================================
# Main
# ======================================================
if __name__ == "__main__":
    files = sorted(glob.glob(
        "./ETH_Price_JSON/ETHUSDT_1min_*.json"
    ))

    df = add_indicators(resample_ohlcv(load_klines(files)))

    # -------- 7 days --------
    df_7d = get_recent_days_safe(df, 7)
    trades_7d = backtest_ema_pullback(df_7d)
    plot_price_only(
        df,
        7,
        OUTPUT_DIR / "ETH_USDT_7d_price.png",
        "ETH-USDT 15m – Last 7 Days"
    )

    plot_backtest_summary(
        trades_7d,
        OUTPUT_DIR / "ETH_USDT_7d_backtest.png"
    )

    # -------- 60 days --------
    plot_price_only(
        df,
        60,
        OUTPUT_DIR / "ETH_USDT_60d_price.png",
        "ETH-USDT 15m – Last 60 Days"
    )

    # -------- Full history --------
    plot_price_only(
        df,
        (df.index.max() - df.index.min()).days + 1,
        OUTPUT_DIR / "ETH_USDT_full_price.png",
        "ETH-USDT 15m – Data collected to date"
    )

    print("All price charts (without trade markers) and 7-day backtest summary generated.")
