# -*- coding: utf-8 -*-
import os
import sys
import json
import platform
import shutil
import logging
import requests
import re
import time
from bs4 import BeautifulSoup
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy
from eclipse import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/eclipseDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_eclipse.json"

class EclipseCrawler(Crawler):
    def __init__(self):
        super(EclipseCrawler, self).__init__(name="eclipse")
        self.page = 0
        self.item = 0
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="eclipse_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME,"w") as progress:
            json.dump({'page':self.page,'item':self.item},progress)

    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as progress:
            lastprogress = json.load(progress)
            self.page = lastprogress['page']
            self.item = lastprogress['item']
        
    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self):
        log.warning("page={}, items={}".format(self.page, self.item))
    #     print("[[page]]", self.page)
    #     pageSoup = BeautifulSoup(requests.get(
    #         "https://projects.eclipse.org/list-of-projects?combine=&page={0}".format(self.page)).text, "html.parser")

    #     projectListView = pageSoup.findAll(
    #         "div", {"class": "node-project"})[self.item:]
        url = "https://projects.eclipse.org/list-of-projects?combine=&page={0}".format(self.page)
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
        soup = BeautifulSoup(response.text, "html.parser")
        project_list = soup.select("div.node-project")

        return project_list[self.item:] if project_list else []
                
    def crawlingAction(self):
        initialPath = download_path
        log.debug(initialPath)

        DataBase_Crawler_DB(crawlerName="eclipse_re",crawlerStatus='1').crawler_db_insert()

        while(True):
            project_list = self.get_project_list()
            if len(project_list) == 0:
                log.warning("There is no project.")
                break
            
            for project in project_list:
                nameDOM = project.select_one("h4.name") # ("h4", {"class": "name"})
                projectName = nameDOM.text.strip().replace('/','')
                linkDOM = nameDOM.findAll("a")[0]
                # projectUrl
                projectUrl = linkDOM.attrs["href"]
                log.warning("{}:{}".format(projectName, projectUrl))

                # project_page.get_project_info(projectName, projectUrl, initialPath)
                project_page.get_project_info.delay(projectName, projectUrl, initialPath)
                os.chdir(initialPath)
                # break # test

            os.chdir(initialPath)
            self.page += 1
            self.item = 0
            self.write_progress_log()
            time.sleep(60*60*2) # wait 2 hours
            # break # test
        # progress 초기화
        self.page = 0
        self.item = 0
        self.write_progress_log()

        DataBase_Crawler_DB(
            crawlerName="eclipse_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = EclipseCrawler()
    crawler.crawling()
