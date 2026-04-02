import os

import requests
import  json
import datetime

import zstandard as zstd

header_content=json.loads(os.getenv('header_secret'))

def is_exist(filename):
    try:
        open(filename).close()
        return True
    except FileNotFoundError:
        return False


def timestamp_to_utc5(timestamp):
    utc_minus_5 = datetime.timezone(datetime.timedelta(hours=-5))
    utc_time = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    utc5_time = utc_time.astimezone(utc_minus_5)

    return utc5_time

def data_update(new_data):
    new_data_dict={}
    for i in new_data:
        date_time = timestamp_to_utc5(float(i["date"]))
        ftime=date_time.strftime("%Y-%m-%d")
        if ftime not in new_data_dict:
            new_data_dict[ftime]=[i]
        else:
            new_data_dict[ftime].append(i)

    for key, value in new_data_dict.items():
        data_path=f"data/ETH_data_{key}.json"
        id_path=f"dataid/ETH_data_id_{key}.json"
        history_data = []
        history_data_id = []
        if is_exist(data_path):
            with open(data_path, encoding="utf-8-sig") as fp:
                history_data=json.loads(fp.read())
        if is_exist(id_path):
            with open(id_path, encoding="utf-8-sig") as fp:
                history_data_id=json.loads(fp.read())
        for j in value:
            if j["id"] not in history_data_id:
                history_data_id.append(j["id"])
                history_data.append(j)

        with open(data_path, "w+", encoding="utf-8-sig") as fp:
            fp.write(json.dumps(history_data, indent=4, ensure_ascii=False))
        with open(id_path, "w+", encoding="utf-8-sig") as fp:
            fp.write(json.dumps(history_data_id, indent=4, ensure_ascii=False))


def get_new_data():
    tsession=requests.session()
    tsession.headers.update(header_content)
    for i in range(1,40):
        url=f"https://www.binance.com/bapi/composite/v4/friendly/pgc/content/queryByHashtag?hashtag=%23ETH&pageIndex={i}&pageSize=20&orderBy=LATEST"
        for _ in range(2):
            try:
                test2 = tsession.get(url)
                dctx = zstd.ZstdDecompressor()
                decompressed_data = dctx.decompress(test2.content, max_output_size=1048576)
                new_data = json.loads(decompressed_data.decode())['data']["feedData"]
                break
            except TypeError:
                continue
        print(f"Retrieved Data Count: {len(new_data)}")
        if not new_data:
            return
        print(f"The oldest message Date: {timestamp_to_utc5(float(new_data[-1]['date'])).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        data_update(new_data)


if __name__=="__main__":

    get_new_data()





