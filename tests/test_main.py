import pytest

import os
import shutil
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "conf"))

import configparser
import json

from src import main, create_map

config = configparser.ConfigParser()
config.read("/app/tests/test_config.ini", encoding='utf-8')
railways_map = create_map.op_folium(conf="/app/tests/test_config.ini")

def setup_module():
    os.makedirs("./tmp", exist_ok=True)

def test_from_config():
    test_config = main.from_config('/app/tests/test_config.ini')
    assert test_config == config


def test_manage_cache():
    empty = []
    railways = ['test1','test2','test3']
    assert main.manage_cache(cache='/app/conf/cache', mode='w', railways=empty)
    assert main.manage_cache(cache='/app/conf/cache', mode='r') == ['']
    assert main.manage_cache(cache='/app/conf/cache', mode='w', railways=railways)
    assert main.manage_cache(cache='/app/conf/cache', mode='r') == ['test1','test2','test3']


def test_fetch_response():
    main.fetch_response(os.environ['OP_CHALLENGE_CONSUMER_KEY'], res_json='test_response.json')
    assert os.path.exists('test_response.json')


def test_fetch_train_information():
    no_delay_json = json.load(open('test_no_delay.json','r'))
    delay_json = json.load(open('test_delay.json','r'))
    assert main.fetch_train_information(no_delay_json) == {}
    assert main.fetch_train_information(delay_json) == {'odpt.Railway:JR-East.ChuoRapid':'異常あり',
                                                       'odpt.Railway:JR-East.SaikyoKawagoe':'異常あり'}


def test_replace_railway():
    railways = ['odpt.Railway:JR-East.ChuoRapid',
                'odpt.Railway:JR-East.SaikyoKawagoe']
    assert main.replace_railway(railways, config['MAP']['railway_path']) == ['中央線快速','埼京線・川越線']


def test_create_flexmessage():
    railways_map = create_map.op_folium(conf="/app/tests/test_config.ini")
    railways_map.draw_railway()
    railways_map.create_png()
    assert main.create_flexmessage(config, railways_map)


    railways_map = create_map.op_folium(conf="/app/tests/test_config.ini")
    railways_map.add_delay_railways(['odpt.Railway:JR-East.ChuoRapid','odpt.Railway:JR-East.SaikyoKawagoe'])
    railways_map.draw_railway()
    railways_map.create_png()
    assert main.create_flexmessage(config, railways_map)


def teardown_module(self):
    shutil.rmtree("./tmp")
    
