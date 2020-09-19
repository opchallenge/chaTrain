import pytest

import os
import sys
import shutil
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "conf"))

import configparser
import pandas as pd

from src import create_map


class TestCreateMap(object):
    
    def setup_method(self):
        self.op = create_map.op_folium(conf="/app/tests/test_config.ini")
        os.makedirs("./tmp", exist_ok=True)
               
    def test_load_config(self):
        # fetch_config
        config = configparser.ConfigParser()
        config.read("/app/tests/test_config.ini", encoding="utf-8")
        
        assert self.op.html == config["MAP"]["html"]
        assert self.op.url == config["MAP"]["url"]
        #assert self.op.png == config["MAP"]["png"]
        assert self.op.station_path == config["MAP"]["station_path"]
        assert self.op.railway_path == config["MAP"]["railway_path"]
    
    def test_fetch_station_df(self):
        station_df = self.op.fetch_station_df()
        
        assert isinstance(station_df, pd.DataFrame)
        assert "dc:title" in station_df.columns
        assert "odpt:stationCode" in station_df.columns
        assert "odpt:railway" in station_df.columns
        assert "geo:lat" in station_df.columns
        assert "geo:long" in station_df.columns
        
    def test_add_delay_railways(self):
        delay_railways_en = ["odpt.Railway:JR-East.ChuoSobuLocal",
                             "odpt.Railway:JR-East.Musashino"]
        delay_railways_jp = ["中央・総武各駅停車",
                             "武蔵野線"]
        
        assert self.op.delay_railways == []
        
        self.op.add_delay_railways(delay_railways_en)
        assert set(self.op.delay_railways) == set(delay_railways_en)
        
        self.op.delay_railways = []
        self.op.add_delay_railways(delay_railways_jp)
        assert set(self.op.delay_railways) == set(delay_railways_en)
        
        self.op.delay_railways = []
        self.op.add_delay_railways(delay_railways_en[0])
        assert self.op.delay_railways == [delay_railways_en[0]]
        
    def test_create_png(self):
        self.op.create_png()

        assert os.path.exists(self.op.html)
        assert os.path.exists(self.op.png)
    
    def teardown_method(self):
        shutil.rmtree("./tmp")