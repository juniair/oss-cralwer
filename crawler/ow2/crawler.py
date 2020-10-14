# -*- coding: utf-8 -*-

import os
import sys
import json
import platform
import shutil
import logging
import requests
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy

from ow2 import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/ow2Dir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_ow2.json"


class OW2Crawler(Crawler):
    def __init__(self):
        super(OW2Crawler,self).__init__(name="ow2")
        self.page=1
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(slef, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="ow2_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'page':'1'},progress)

    def read_progress_log(self):
        with open('progress_ow2.json', 'r') as progress:
            lastprogress = json.load(progress)
            self.page = lastprogress['page']
        
    def preCrawling(self):
        try:
            self.read_progress_log()
        except FileNotFoundError:
            self.write_progress_log()

    def get_project_list(self):
        url = "https://gitlab.ow2.org/api/v4/projects?per_page=100&page={0}".format(self.page)
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
        lists = json.loads(response.text)

        self.page = response.headers['x-next-page']

        return lists

    def crawlingAction(self):
        initialPath = download_path
        DataBase_Crawler_DB(
                crawlerName="ow2_re",
                crawlerStatus='1').crawler_db_insert()
        while True:
            os.chdir(initialPath)
           
            # Search All Project
            project_list = self.get_project_list()

            i = 0
            for item in project_list:
                log.warning([item["name"], item["web_url"]])
                project_page.get_project_info.delay(item, initialPath)

                # i += 1
                # if i == 10:
                #     break # test

            # Terminate Condition Check.
            if any([self.page is "", len(project_list)==0]):
                log.warning("There is no project.")
                break
            
            self.write_progress_log()

            # break # test

        DataBase_Crawler_DB(
            crawlerName="ow2_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = OW2Crawler()
    crawler.crawling()
