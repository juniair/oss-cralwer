# -*- coding: utf-8 -*-

import os
import json
import platform
import re
import shutil
import requests
import logging
from signal import *

from crawler import DataBase_Crawler_DB, Crawler
from common import getenv, get_http_headers, get_tor_proxy
from launchpad import project_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/launchpadDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_launchpad.json"

class LanchpadCrawler(Crawler):
    def __init__(self):
        super(LanchpadCrawler,self).__init__(name="launchpad")
        self.url = "https://api.launchpad.net/1.0/projects?ws.size=100&ws.op=latest"
        
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame) :
        DataBase_Crawler_DB(
            crawlerName="launchpad_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'w') as self.progress:
            json.dump({'url': self.url}, self.progress)
    
    def read_progress_log(self):
        with open(PROGRESS_LOG_FILENAME, 'r') as self.progress:
            lastprogress = json.load(self.progress)
            self.url = lastprogress['url']
        
    def preCrawling(self):
        try:
            self.read_progress_log()
        except FileNotFoundError:
            self.write_progress_log()


    def check_next_page(self):
        # 10회 재시도 실패하면 다음 페이지로 이동
        with open(PROGRESS_LOG_FILENAME, 'r') as self.progress:
            nextLink = json.load(self.progress)
            linkList = str(nextLink['url']).split('&')
        log.debug(linkList)
        if len(linkList) >= 3:
            temp0 = linkList[1].split('=')
            temp1 = linkList[2].split('=')
            temp2 = linkList[3].split('=')
            temp1[1] = str(int(temp1[1]) + int(temp0[1]))
            temp2[1] = str(int(temp2[1]) + int(temp0[1]))
            linkList[2] = '='.join(temp1)
            linkList[3] = '='.join(temp2)
            self.url = "&".join(linkList)
            self.write_progress_log()
            log.warning('[crawler_launchpad] connection Error > next Pages')
            return True
        else:
            log.error('[crawler_launchpad] connection Error1')
            return False

    def crawlingAction(self):
        DataBase_Crawler_DB(
                crawlerName="launchpad_re",
                crawlerStatus='1').crawler_db_insert()
        while True:
            log.warning('[crawler_launchpad] ' + self.url + ' Searching...')
            i = 0
            # Maximum 10 time retry.
            isconnected = False
            dictionary = None
            initialPath = download_path

            # 이전 작업 코드
            for i in range(1, 11):
                try:
                    response = requests.get(self.url, headers=get_http_headers(), proxies=get_tor_proxy())
                    text = response.text
                    dictionary = json.loads(text)
                    isconnected = True
                    break
                except Exception as e:
                    log.error(e)
                    log.error('[crawler_launchpad] timeout. retrying... count = {0}'.format(i))

            if dictionary == None:
                log.error("There is no data. retry...")
                continue

            # Conncetion failed 10 times, terminate it.
            if not isconnected:
                if self.check_next_page(): continue
                log.error('[crawler_launchpad] connection Error2')
                break

            log.debug('[crawler_launchpad] response received.')

            # i = 0
            for entry in dictionary['entries']:
                os.chdir(initialPath)
                log.warning(entry)
                project_page.get_project_info.delay(entry, initialPath)

                # i += 1
                # if i == 60:
                #     break # test

            # break # test
            if dictionary.get('next_collection_link') == None: break
            
            self.url = dictionary['next_collection_link']
            self.write_progress_log()

        DataBase_Crawler_DB(
            crawlerName="launchpad_re",
            crawlerStatus='0').crawler_db_insert()
        self.url = "https://api.launchpad.net/1.0/projects?ws.size=100&ws.op=latest"
        self.write_progress_log()

if __name__ == "__main__":
    crawler = LanchpadCrawler()
    crawler.crawling()
