import platform
import re
import os
import requests
import json
import sys
import signal
import shutil
import time
import logging
from signal import *

from bitbucket import project_page, source_page

import md5hasher
import GetRepoInfo
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from logger import getLogger, write_progress_log
from common import get_http_headers, get_tor_proxy, getenv


log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/bitbucketDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_bitbucket.json"

class BitbucketCrawler(Crawler):
    def __init__(self):
        super(BitbucketCrawler,self).__init__(name="bitbucket")
        self.last_seen_info = ''
        self.url = "https://api.bitbucket.org/2.0/repositories?pagelen=10"

        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        # DataBase_Crawler_DB(
        #     crawlerName="bitbucket_re",
        #     crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'last_url': self.url, 'last_seen_info': self.last_seen_info}, progress)

    def read_progress_log(self):
        try:
            with open(PROGRESS_LOG_FILENAME,'r') as progress:
                lastprogress = json.load(progress)
                self.url = lastprogress['last_url']
                self.last_seen_info = lastprogress['last_seen_info']
        except:
            self.write_progress_log()

    def preCrawling(self):
        self.read_progress_log()

    def crawlingAction(self):
        try:
            DataBase_Crawler_DB(
                crawlerName="bitbucket_re",
                crawlerStatus='1').crawler_db_insert()

            # file_dir = download_path
            # print("file_dir : " + file_dir)
            initialPath = download_path
            log.debug("initialPath="+initialPath)
            
            while True:
                # 프로젝트 리스트 get
                log.debug("get {}".format(self.url))
                response = requests.get(self.url, headers=get_http_headers(), proxies=get_tor_proxy())
                text = response.text
                if text == "": 
                    log.warning("[crawler_bitbucket] Error or No Result")
                    break
                
                data = json.loads(text)

                if len(data["values"]) == 0:
                    log.warning("There is no project.")
                    break
                
                skip = True
                current_path = initialPath
                os.chdir(current_path)
                for item in data['values']:
                    projectName = "{}_{}".format(item['name'], item['workspace']['slug'])
                    if any([(self.last_seen_info == ''),(projectName == self.last_seen_info)]):
                        skip = False

                    if skip:
                        continue

                    log.debug("call project_page.get_release_info({})".format(projectName))
                    print("call project_page.get_release_info({})".format(projectName))
                    project_page.get_release_info.delay(item, current_path)
                    
                    self.last_seen_info = projectName
                    self.write_progress_log()

                    # break # test
                if data.get("next"):
                    self.url = data['next']
                    self.last_seen_info = ''
                else:
                    log.warning("[crawler_bitbucket] There is no next url!!!")
                    break
                self.write_progress_log()

                # break # test
            os.chdir(initialPath)
            self.write_progress_log()
        except Exception as e:
            log.error(e)
            
        DataBase_Crawler_DB(
            crawlerName="bitbucket_re",
            crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    crawler = BitbucketCrawler()
    crawler.crawling()