import os
import sys
import datetime
import re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent / "conf"))

import numpy as np
import pandas as pd
import configparser

import folium
from selenium import webdriver


class op_folium():
    
    def __init__(self, conf="/conf/config.ini", offset_lat=35.681300, offset_long=139.76704):
        dt_now = str(datetime.datetime.now())
        dt_now = re.sub('[ -/:-@\[-~]', '', dt_now)
        
        config = configparser.ConfigParser()
        config.read(conf, encoding="utf-8")
        self.html = config["MAP"]["html"]
        self.url = config["MAP"]["url"]
        self.png = config["MAP"]["png"].replace("#datetime", dt_now)
        self.station_path = config["MAP"]["station_path"]
        self.railway_path = config["MAP"]["railway_path"]
    
        self.delay_railways = []
        self.station_df = self.fetch_station_df()
        self.m = folium.Map(
                    location = [offset_lat, offset_long],
                    tiles = "stamenterrain",
                    zoom_start = 11
                )

        
    # 予め定義したシートから駅一覧の取得
    def fetch_station_df(self):
        station_df = pd.read_csv((self.station_path), index_col=0)
        railways = pd.read_csv((self.railway_path), index_col=0)["owl:sameAs"].unique()
        selected_df = pd.DataFrame()
        for railway in railways:
            tmp_df = station_df[station_df["odpt:railway"]==railway]
            selected_df = pd.concat([selected_df, tmp_df])
        mask = selected_df[["geo:lat", "geo:long"]].dropna(how="any", axis=0).index
        selected_df = selected_df.loc[mask]
        return selected_df
    
    
    # 遅延路線の追加
    def add_delay_railways(self, railways:list):
        railway_df = pd.read_csv(self.railway_path)
        railway_dict = railway_df.set_index("dc:title")["owl:sameAs"].to_dict()
        
        if isinstance(railways, str):
            if railways in railway_dict.keys():
                self.delay_railways.append(railway_dict[railways])
            elif railways in railway_dict.values():
                self.delay_railways.append(railways)
            else:
                pass
        
        for railway in railways:
            if railway in railway_dict.keys():
                self.delay_railways.append(railway_dict[railway])
            elif railway in railway_dict.values():
                self.delay_railways.append(railway)
            else:
                pass
        self.delay_railways = list(set(self.delay_railways))
        
        
    # 路線をマップに反映
    def draw_railway(self):
        railways = self.station_df["odpt:railway"].unique()
        for railway in railways:
            railway_df = self.station_df[self.station_df["odpt:railway"]==railway]
            railway_df = railway_df.sort_values("odpt:stationCode")
            for i, (j, row) in enumerate(railway_df.iterrows()):
                station = row["dc:title"]
                locations = [row["geo:lat"], row["geo:long"]]
                
                if i == 0:
                    before_locations = locations
                else:
                    now_locations = [before_locations, locations]
                    before_locations = locations
                    
                    if railway in self.delay_railways:
                        folium.PolyLine(
                            locations=now_locations,
                            color="red",
                        ).add_to(self.m)
                    else:
                        folium.PolyLine(
                            locations=now_locations,
                            color="green",
                        ).add_to(self.m)
    
    # HTMLファイル、image作成
    def create_png(self):
        self.m.save(outfile=self.html)
    
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(options=options)

        driver.get(self.url)
        w = driver.execute_script("return document.body.scrollWidth;")
        h = driver.execute_script("return document.body.scrollHeight;")
        driver.set_window_size(w,h)

        driver.save_screenshot(self.png)
        driver.quit()
        
