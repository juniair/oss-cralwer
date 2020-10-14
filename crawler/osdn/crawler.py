# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import shutil
import requests
from bs4 import BeautifulSoup
import logging
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy
from osdn import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/osdnDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_osdn.json"

class OSDNCrawler(Crawler):

    def __init__(self):
        super(OSDNCrawler, self).__init__(name="osdn")
        self.page = 1
        self.url = ""
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="osdn_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)
    
    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'page': self.page}, progress)

    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as progress:
            lastprogress = json.load(progress)
            self.page = lastprogress['page']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except FileNotFoundError:
            self.write_progress_log()

    def get_project_list(self):
        self.url = "https://osdn.net/softwaremap/simple_list.php?page={0}".format(self.page)
        response = requests.get(self.url, headers=get_http_headers(), proxies=get_tor_proxy())

        # Escape Condition
        if response.status_code == 404: return []

        soup = BeautifulSoup(response.text, "html.parser")
        list_table = soup.select("table#project-simple-list-table")
        project_list = list_table[0].select("tbody tr") # thead 제외
        return project_list if project_list else []

    def crawlingAction(self):
        DataBase_Crawler_DB(
                crawlerName="osdn_re",
                crawlerStatus='1').crawler_db_insert()
        while True:
            project_list = self.get_project_list()
            if len(project_list) == 0:
                log.warning("There is no project.")
                break
            log.warning("----------page {0} start----------".format(self.page))
            initialPath = download_path
            os.chdir(initialPath)
            i=0
            for item in project_list:
                temp_text = item.get_text() # 전체 텍스트
                if any([
                    "(freshmeat)" in temp_text, # External Project, Freecode.com -> skip.
                    "(sfnet)" in temp_text, # External Project, SourceForge.com -> skip.
                    item.select("a.btn.btn-success") is None # if project haven't download button, skip.
                ]): 
                    log.error("It is external project or no download button.")
                    continue

                project_anchor = item.select_one("td.simple-list-name a")
                project_name = project_anchor.text.strip()
                project_url = "https://osdn.net{}".format(project_anchor.attrs['href'])
                log.warning([project_name, project_url])
                project_page.get_project_info.delay(project_url, project_name, initialPath)
                
                # i += 1
                # if i == 2:
                #     break # test

            self.page += 1
            os.chdir(initialPath)
            self.write_progress_log()
            # break # test

        DataBase_Crawler_DB(
            crawlerName="osdn_re",
            crawlerStatus='0').crawler_db_insert()
        self.page = 1


if __name__ == "__main__":
    crawler = OSDNCrawler()
    crawler.crawling()