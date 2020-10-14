# -*- coding: utf-8 -*-

import os
import json
import sys
import platform
import shutil
import logging
import re
import requests
from bs4 import BeautifulSoup
import functools
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy

from gnu import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gnuDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_gnu.json"

class GNUCrawler(Crawler):
    def __init__(self):
        super(GNUCrawler, self).__init__(name="gnu")
        self.interval = 50
        self.page = 0
        self.item = 0
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="gnu_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, "w") as self.progress:
            json.dump({'page': self.page, 'item': self.item}, self.progress)
    
    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as self.progress:
            lastprogress = json.load(self.progress)
            self.page = lastprogress['page']
            self.item = lastprogress['item']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self):
        gnu_start_offset = 9 # 첫 9개가 프로젝트 데이터가 없다.
        pagenumbering = self.page * self.interval + self.item + gnu_start_offset
        pagenumbering2 = self.interval
        url = "https://savannah.gnu.org/search/?type_of_search=soft&words=*&offset={0}&max_rows={1}#results".format(pagenumbering,self.interval)
        log.warning(url)
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())

        soup = BeautifulSoup(response.text, "html.parser")
        project_rows = soup.select("table.box tr")[1:] # 0=header row
        project_list = list(filter(lambda x: all([
            x.select_one("td a").get_text().strip() != "",
            x.select("td")[1].get_text().strip() != ""
        ]), project_rows))

        return project_list

    def crawlingAction(self):
        initialPath = download_path

        DataBase_Crawler_DB(
                crawlerName="gnu_re",
                crawlerStatus='1').crawler_db_insert()
        while(True):
            projectLists = self.get_project_list()

            # Escape Condition
            if len(projectLists) <= 0:
                log.error("Not found. Last Page!")
                break

            i = 0
            for project in projectLists:
                # projectName
                project_name = project.select_one("td a").get_text().strip()
                project_name = re.sub('[\\\\/:*?\"<>|]', '_', project_name)

                # projectUrl
                project_url = project.select_one("td a").attrs["href"].replace("..", "https://savannah.gnu.org")
                # summary
                summary = project.select("td")[1].text
                log.warning(project_name)
                log.warning(project_url)
                # log.warning(summary[:30])
                project_page.get_project_info.delay({
                # project_page.get_project_info({
                    "project_name":project_name,
                    "project_url":project_url,
                    "summary":summary
                }, initialPath)

                # i += 1
                # if i == 30:
                #     break # test

            self.page += 1
            self.item = 0
            # os.chdir(crawlerDir)
            self.write_progress_log()
            # break # test

        DataBase_Crawler_DB(
            crawlerName="gnu_re",
            crawlerStatus='0').crawler_db_insert()
        self.page = 0
        self.item = 0
        # os.chdir(crawlerDir)
        self.write_progress_log()

if __name__ == "__main__":
    crawler = GNUCrawler()
    crawler.crawling()
