# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import shutil
import stat
import logging
import platform
from signal import *
import tarfile
import time

from common import getenv, get_http_headers, get_tor_proxy
from crawler import DataBase_Crawler_DB, Crawler
# import URLDownloader

from debian import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/debianDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_debian.json"

class DebianCrawler(Crawler):
    def __init__(self):
        super(DebianCrawler,self).__init__(name="debian")
        self.last_seen_info = ''
        self.page = 1
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="debian_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME,'w') as progress:
            json.dump({'last_seen_info':self.last_seen_info, "page":self.page}, progress)
    
    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME,'r') as progress:
            lastprogress = json.load(progress)
            self.last_seen_info = lastprogress['last_seen_info']
            self.page = lastprogress['page']
            log.warning("page="+self.page)

    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self):
        project_rows = None
        try:
            project_list_url = "https://salsa.debian.org/explore/projects?non_archived=true&page={}&sort=name_asc".format(self.page)
            log.warning(project_list_url)
            response = requests.get(project_list_url, headers=get_http_headers(), proxies=get_tor_proxy())
            # log.warning(response.text)
            soup = BeautifulSoup(response.text, 'html.parser')
            project_rows = soup.select(".project-row")
            # log.warning(project_rows)
        except Exception as e:
            log.error(e)
            log.error(get_tor_proxy())
            project_rows = []
        return project_rows

    def get_project_info(self, row):
        # log.warning(row)
        project_details = row.select_one("div.project-details")
        project_page_link = project_details.select_one("div.project-title > h2 > a").attrs["href"]
        project_full_name = project_details.select_one("span.project-full-name").get_text().replace("\n", "")
        project_description = project_details.select_one(".description")
        metadata_infos = project_details.select(".project-title > span")
        # log.warning(project_page_link)
        # log.warning(project_full_name)
        # log.warning(project_details.select_one(".description"))
        # log.warning(metadata_infos)
        if len(metadata_infos) == 2:
            project_license = metadata_infos[-1].get_text()
        else:
            project_license = ""
        return {
            "page_link": project_page_link,
            "full_name": project_full_name,
            "license": project_license.strip(),
            "description": project_description.get_text().strip() if project_description else ""
        }

    def crawlingAction(self):
        initialpath = download_path
        DataBase_Crawler_DB(
            crawlerName="debian_re",
            crawlerStatus='1').crawler_db_insert()
        
        while True:
            project_rows = self.get_project_list()
            if len(project_rows) == 0:
                break
            i = 0
            for row in project_rows:
                os.chdir(initialpath)
                project_info = self.get_project_info(row)

                log.warning(project_info)

                # project_page.get_project_info.delay(project_info, initialpath)
                project_page.get_project_info.delay(project_info, initialpath) # test

            # progress 초기화
            os.chdir(initialpath)
            self.last_seen_info = ''
            self.page += 1
            self.write_progress_log()
            time.sleep(60*60*2) # wait 2 hours
            # break # test

        self.page = 1
        self.write_progress_log()
        DataBase_Crawler_DB(
            crawlerName="debian_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = DebianCrawler()
    crawler.crawling()