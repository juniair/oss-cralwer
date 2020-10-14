import os, sys
import io
import re
import platform
import time
import logging
import json
from bs4 import BeautifulSoup
from functools import reduce
import shutil
import requests
import string
from signal import *

import zipfile_custom
import wget_proxy

from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from common import getenv, get_http_headers, get_tor_proxy

from codeplex import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/codeplexDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_codeplex.json"

class CodeplexCrawler(Crawler):
    def __init__(self):
        super(CodeplexCrawler, self).__init__(name="codeplex")
        self.index = ''

        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="codeplex_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'index': ''}, progress)

    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as progress:
            lastprogress = json.load(progress)
            self.index = lastprogress['index']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self, search_char='a'):
        search_url = "https://codeplexarchive-search.search.windows.net/indexes/codeplexarchive-index/docs?api-version=2016-09-01&api-key=44C8CF90A6561D9EC9A1BBA09250FEA1&$top=100&highlight=Title&search={0}%20{0}*".format(search_char)
        
        project_list = None
        try:
            response = requests.get(search_url, headers=get_http_headers(), proxies=get_tor_proxy())

            project_list = json.loads(response.text)
            
        except Exception as e:
            log.error(e)
            project_list = []
        return project_list

    def crawlingAction(self):
        current_path = download_path
        
        DataBase_Crawler_DB(
            crawlerName="codeplex_re",
            crawlerStatus='1').crawler_db_insert()

        #a~z까지 프로젝트명을 뽑아와서 정렬시킨 후 사이트에서 파싱한다.
        lower_alphabets = list(string.ascii_lowercase)
        for search_char in lower_alphabets:
            os.chdir(current_path)

            project_list = self.get_project_list(search_char)
            if len(project_list) == 0: 
                log.error("There is no project lists...")
                continue

            for item in project_list["value"]:
                projectName = item["ProjectName"]
                log.warning("Download {}...".format(projectName))
                project_page.get_project_info.delay(projectName, current_path)

                # break # test

            time.sleep(60*60*2)
                # break # test
        DataBase_Crawler_DB(
            crawlerName="codeplex_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = CodeplexCrawler()
    crawler.crawling()
