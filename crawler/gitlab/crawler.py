#-*- coding: utf-8 -*-

import os, sys
import platform
import shutil
import logging
import requests
import json
import time
import md5hasher
from signal import *

from gitlab import project_page

from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from common import get_http_headers, get_tor_proxy, getenv

log = logging.getLogger(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gitlabDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_gitlab.json"

class GitlabCrawler(Crawler):
    MAX_PROJECT=10

    def __init__(self):
        super(GitlabCrawler,self).__init__(name="gitlab")
        self.page = "0"
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)
    
    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="gitlab_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'page':self.page}, progress)

    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as progress:
            lastprogress = json.load(progress)
            self.page = lastprogress['page']
            log.debug("reading page : " + self.page)

    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self):
        # Search All Project.
        url = "https://gitlab.com/api/v4/projects?per_page={}&page={}".format(self.MAX_PROJECT, self.page)
        log.warning("[crawler_gitlab] " + url + " : Searching...")
        # response = requests.get(url)
        response = requests.get(url, headers = get_http_headers())
        text = response.text

        lists = None
        try:
            lists = json.loads(text)

            # 다음 페이지 번호 체크
            # X-Next-Page: 2
            # X-Page: 1
            # X-Per-Page: 100
            # X-Prev-Page:
            self.page = response.headers['x-next-page']
            self.write_progress_log()
        except Exception as e:
            log.error(e)
            lists = []
        return lists

    def crawlingAction(self):
        initialPath = self.crawlDir # download_path
        log.debug(initialPath)

        DataBase_Crawler_DB(
            crawlerName="gitlab_re",
            crawlerStatus='1').crawler_db_insert()

        while True:
            os.chdir(initialPath)
            
            project_list = self.get_project_list()
            if len(project_list) == 0:
                break

            for item in project_list:
                log.warning("Download {}".format(item["name"]))
                project_page.get_project_info.delay(item, initialPath)
                # break # test

            if self.page is "":
                log.info("[crawler_gitlab] not exist next page!")
                break
            time.sleep(60*60*2) # wait for 2 hours
            log.debug("goto next page : " + self.page)

            # break # test
            
        log.debug('done, search {0} pages'.format(self.page))

        # progress reset
        self.page = "0"
        self.write_progress_log()

        os.chdir(initialPath)
        
        DataBase_Crawler_DB(
            crawlerName="gitlab_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = GitlabCrawler()
    crawler.crawling()