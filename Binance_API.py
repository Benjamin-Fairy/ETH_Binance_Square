import json

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import pytz

ECT = pytz.timezone('America/New_York')
utc = pytz.timezone('UTC')


def get_binance_klines(symbol, interval, start_time, end_time):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": int(start_time.replace(tzinfo=utc).astimezone(ECT).timestamp() * 1000),
        "endTime": int(end_time.replace(tzinfo=utc).astimezone(ECT).timestamp() * 1000),
        "limit": 1000
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    # print(response.json())
    return response.json()


def fetch_all_minute_data(symbol, start_date, end_date):
    all_data = []
    interval = timedelta(minutes=1000)
    start_time = datetime.strptime(start_date, "%Y-%m-%d")
    end_time = datetime.strptime(end_date, "%Y-%m-%d")

    while start_time < end_time:
        next_time = start_time + interval
        if next_time > end_time:
            next_time = end_time

        print(f"Fetching {start_time} → {next_time}")
        data = get_binance_klines(symbol, "1m", start_time, next_time)
        all_data.extend(data)
        start_time = next_time
        time.sleep(0.5)

    df = pd.DataFrame(all_data, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume",
        "CloseTime", "QuoteAssetVolume", "NumberOfTrades",
        "TakerBuyBase", "TakerBuyQuote", "Ignore"
    ])

    df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df["CloseTime"] = pd.to_datetime(df["CloseTime"], unit="ms")
    df = df[["OpenTime", "Open", "High", "Low", "Close", "Volume"]]
    df[["Open", "High", "Low", "Close", "Volume"]] = df[
        ["Open", "High", "Low", "Close", "Volume"]
    ].astype(float)

    return all_data, df


if __name__ == "__main__":
    symbol = "ETHUSDT"
    now_in_UTC_5 = datetime.now(ECT).strftime("%Y-%m-%d")
    past_in_UTC_5 = (datetime.now(ECT) + timedelta(days=-1)).strftime("%Y-%m-%d")
    start_date = past_in_UTC_5
    end_date = now_in_UTC_5

    json_data, df = fetch_all_minute_data(symbol, start_date, end_date)

    with open(f"ETH_Price_JSON/{symbol}_1min_{start_date}_to_{end_date}.json","w+",encoding="utf-8-sig") as fp:
        fp.write(json.dumps(json_data))

    csv_name = f"ETH_Price_CSV/{symbol}_1min_{start_date}_to_{end_date}.csv"
    df.to_csv(csv_name, index=False, encoding="utf-8-sig")

    print(f"\nRetrieved data: {len(df)}, saved to: {csv_name}")
