import os, sys
import platform
import re
import json
import subprocess
import shutil
import stat
import time
import logging
import requests
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy
from apache import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/apacheDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_apache.json"

class ApacheCrawler(Crawler):
    def __init__(self):
        super(ApacheCrawler, self).__init__(name="apache")
        self.last_seen_info = ''

        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="apache_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)
    
    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'last_seen_info': self.last_seen_info}, progress)
    
    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as progress:
            lastprogress = json.load(progress)
            self.last_seen_info = lastprogress['last_seen_info']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except:
            self.write_progress_log()

    def get_project_list(self):
        projects_url = "https://projects.apache.org/json/foundation/projects.json"
        response = requests.get(projects_url, headers=get_http_headers(), proxies=get_tor_proxy())
        project_list = json.loads(response.text)
        return project_list

    def crawlingAction(self):
        os.chdir(download_path)
        current_path = download_path

        try:
            DataBase_Crawler_DB(
                crawlerName="apache_re",
                crawlerStatus='1').crawler_db_insert()

            project_list = self.get_project_list()

            test_count = 0
            for index, project_info in project_list.items():
                log.warning("Download {}".format(index))

                # # test
                # if test_count < 4: 
                #     test_count += 1
                #     continue  # test

                project_page.get_project_info.delay(index, project_info, current_path)
                self.last_seen_info = index
                self.write_progress_log()

                time.sleep(10)
                
                # # test로 10개 프로젝트만 진행
                # test_count += 1
                # if test_count == 20:
                #     break # test

            os.chdir(current_path)
            self.last_seen_info = ''
            self.write_progress_log()
        except Exception as e:
            log.error(e)

        DataBase_Crawler_DB(
                crawlerName="apache_re",
                crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = ApacheCrawler()
    crawler.crawling()
