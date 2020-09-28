# coding: utf-8

import os
import glob
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "conf"))
import configparser
import dbm
import json

import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (FlexSendMessage, ImageSendMessage, MessageEvent,
                            TextMessage, TextSendMessage)

import create_map

app = Flask(__name__)


def from_config(conf='/conf/config.ini'):
    config = configparser.ConfigParser()
    config.read(conf, encoding='utf-8')
    return config


def manage_cache(cache='/conf/cache', mode='r', railways=None):
    with dbm.open(cache, mode) as db:
        # キャッシュの読み込み
        if (mode == 'r'):
            railways = db['railway']
            return railways.decode().split(',')
        # キャッシュの書き込み
        elif (mode == 'w'):
            db['railway'] = ','.join(railways)
            return True
        else:
            return False


def fetch_response(consumer_key, res_json='/conf/response.json'):
    information_url = 'https://api-tokyochallenge.odpt.org/'\
                      'api/v4/odpt:TrainInformation?'\
                      'odpt:operator=odpt.Operator:JR-East'\
                      '&acl:consumerKey=' + consumer_key
    response = requests.get(information_url)

    with open(res_json, mode='w', encoding='utf-8') as f:
        f.write(str(response))

    return response.json()


def fetch_train_information(response):
    railway_info = pd.DataFrame(response)
    railway_info = railway_info[["odpt:railway","odpt:trainInformationText"]]
    railway_info.rename(columns={"odpt:railway": "railway",
                                 "odpt:trainInformationText": "status"},
                        inplace=True)
    railway_info["status"] = railway_info["status"].map(lambda x: x["ja"])

    # 異常路線を取得
    mask = railway_info['status'] != "平常運転"
    railway_info = railway_info[mask]

    # 異常路線が空の場合
    if len(railway_info) == 0:
        return {}
    
    railway_info.set_index('railway', drop=True, inplace=True)
    return railway_info['status'].to_dict()


def replace_railway(railways, railway_path):
    railway_df = pd.read_csv(railway_path)
    railway_df = railway_df.set_index("owl:sameAs")
    railway_dict = railway_df["dc:title"].to_dict()
    return [railway_dict[x] for x in railways]


def create_flexmessage(config, railways_map):
    railways = railways_map.delay_railways
    
    flexmessage = json.load(open(config['LINE']['flexmessage_json'],'r'))
    url = flexmessage["contents"]["hero"]["url"]
    dirname = os.path.dirname(url)
    basename = os.path.basename(railways_map.png)
    flexmessage["contents"]["hero"]["url"] = os.path.join(dirname, basename)
    
    if railways == []:
        tmp_dict = {"type": "text", "text": '遅延はありません'}
        flexmessage["contents"]["body"]["contents"].append(tmp_dict)
    else:
        tmp_dict = {"type": "text", "text": '遅延路線：'}
        flexmessage["contents"]["body"]["contents"].append(tmp_dict)

        # 変換
        railways = replace_railway(railways, config['MAP']['railway_path'])
        # メッセージ追加
        for railway in railways:
            tmp_dict = {"type": "text", "text": ' ' + railway}
            flexmessage["contents"]["body"]["contents"].append(tmp_dict)
    
    map_html = config['MAP']['html']
    with open(map_html, mode='r+', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        image_tag = soup.new_tag('meta',
                                 property="og:image",
                                 content=railways_map.png)
        title_tag = soup.new_tag('meta',
                                 property="og:title",
                                 content="TrainInformation")
        description_tag = soup.new_tag('meta',
                                       property="og:description",
                                       content="please tap this message")

        soup.find('head').append(image_tag)
        soup.find('head').append(title_tag)
        soup.find('head').append(description_tag)
        with open(map_html, 'w') as f:
            f.write(str(soup))

    container_obj = FlexSendMessage.new_from_json_dict(flexmessage)
    line_bot_api = LineBotApi(os.environ['LINE_ACCESS_TOKEN_TEST'])
    line_bot_api.broadcast(messages=container_obj)
    
    return True


def main():
    config = from_config()
    
    # 前回の画像削除
    for file in glob.glob('/app/html/*.png'):
        os.remove(file)

    # mapクラスオブジェクト作成
    railways_map = create_map.op_folium()

    before_delay_railways = manage_cache()
    res_delay_railways = fetch_response(os.environ['OP_CHALLENGE_CONSUMER_KEY'])
    now_delay_railways = fetch_train_information(res_delay_railways)

    # キャッシュ更新
    railways_diff = set(list(now_delay_railways.keys())) != set(before_delay_railways)
    if railways_diff:
        manage_cache(mode='w', railways=list(now_delay_railways.keys()))
    else:
        pass

    # 異常路線があるかどうか
    if len(now_delay_railways.keys()) > 0:
        railways_map.add_delay_railways(list(now_delay_railways.keys()))
    else:
        pass

    railways_map.draw_railway()
    railways_map.create_png()
    create_flexmessage(config, railways_map)


if __name__ == "__main__":
    main()
