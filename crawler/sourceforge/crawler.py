# -*- coding: utf-8 -*-

import os
import io
import sys
import platform
import re
import json
import time
import shutil
import tarfile
import zipfile
import requests
import logging
from signal import *
from bs4 import BeautifulSoup
import atexit

from logger import getLogger, write_progress_log
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
import URLDownloader
# from .. import project_tasks, download_tasks
from sourceforge import project_page as project_tasks
from common import get_http_headers, get_tor_proxy

## 메인 크롤러의 로그를 별도로 저장 하기 위해 아래 로거 설정을 사용
log = getLogger(filename="sourceforge_crawler.log")


class SourceForgeCrawler(Crawler):
    def __init__(self):
        super(SourceForgeCrawler, self).__init__(name="sourceforge")
        log.debug("SourceForgeCrawler Intialize....")
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

        # 마지막 수행정보를 저장하기 위한 변수들
        # default value, 1st category.
        self.LAST_SEARCH_CATEGORY = "development/development"
        self.LAST_SEARCH_PAGE = 0
        self.LAST_PROJECT_NUMBER = 0
        self.item = 0
        self.ver = 0
        self.pid = ""
        self.PROGRESS_LOG_FILENAME = self.initialpath + \
            "/progress_{}.json".format(self.name)

    def handler(self, signum, frame):
        log.debug("signum=", signum)
        DataBase_Crawler_DB(crawlerName="sourceforge_re",
                            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self, category="development/development", page='0', number='0'):
        log.debug(self.PROGRESS_LOG_FILENAME)
        write_progress_log(category, page, number, self.PROGRESS_LOG_FILENAME)

    def read_progress_log(self):
        log.debug(self.PROGRESS_LOG_FILENAME)
        if os.path.isfile(self.PROGRESS_LOG_FILENAME):
            with open(self.PROGRESS_LOG_FILENAME, 'r', encoding="utf-8") as self.progress:
                lastprogress = json.load(self.progress)
                self.LAST_SEARCH_CATEGORY = lastprogress['LAST_SEARCH_CATEGORY']
                self.LAST_SEARCH_PAGE = lastprogress['LAST_SEARCH_PAGE']
                self.LAST_PROJECT_NUMBER = lastprogress['LAST_PROJECT_NUMBER']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except FileNotFoundError:
            self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

    def crawlingAction(self):
        log.warning(self.badge + 'Hi!')
        initialPath = self.crawlDir # os.getcwd()
        os.chdir(initialPath)
        log.warning("crawlingAction : initialPath="+initialPath)

        # 소스포지 카테고리 크롤링에 사용할 전체 카테고리 (20개)
        category_list = ["development/development", "internet", "system-administration/system", "games/games",
                         "science-engineering/scientific", "communications", "multimedia/multimedia",
                         "business-enterprise/office", "home-education/education", "development/database",
                         "security-utilities/security", "development/formats-and-protocols", "desktop",
                         "other/nonlisted-topic/other", "development/editors", "mobileapps",
                         "terminals", "home-education/printing", "home-education/social-sciences",
                         "home-education/religion"]

        try:
            DataBase_Crawler_DB(
                crawlerName="sourceforge_re",
                crawlerStatus='1').crawler_db_insert()
            for sourceforgeCategory in category_list:
                # 이미 탐색한 카테고리가 있으면 스킵.
                index = category_list.index(sourceforgeCategory)
                compareIndex = category_list.index(
                    self.LAST_SEARCH_CATEGORY.strip())
                if compareIndex is not None and index < compareIndex:
                    continue
                self.LAST_SEARCH_CATEGORY = sourceforgeCategory

                # 카테고리 크롤링 개시
                self.category_crawling(sourceforgeCategory, initialPath)

                time.sleep(60*60) # 하나의 카테고리 검색이 끝나면 60분간 waiting
                # break # test
            DataBase_Crawler_DB(
                crawlerName="sourceforge_re",
                crawlerStatus='0').crawler_db_insert()
        except requests.ConnectionError as e:
            log.error(e)
            DataBase_Crawler_DB(
                crawlerName="sourceforge_re",
                crawlerStatus='0').crawler_db_insert()

        # DataBase_Crawler_DB(
        #     crawlerName="sourceforge_re",
        #     crawlerStatus='0').crawler_db_insert()
        # 정상 종료되면 프로그레스 초기화.
        self.LAST_SEARCH_CATEGORY = "development/development"
        self.LAST_SEARCH_PAGE = 0
        self.LAST_PROJECT_NUMBER = 0

    def category_crawling(self, category, initialPath):
        # https://sourceforge.net/directory/development/development/os:windows/?page=2
        url = "https://sourceforge.net/directory/" + category + "/os:windows/?page="
        
        # 이전 수행 페이지가 있는 경우 해당 값을 가져옴.
        if int(self.LAST_SEARCH_PAGE) == 0:
            page = 1
        else:
            page = int(self.LAST_SEARCH_PAGE)

        # page limit = 999
        PAGE_SEARCH_LIMIT = 999

        # 페이지 1부터 PAGE_SEARCH_LIMIT까지 스크래핑.
        while page <= PAGE_SEARCH_LIMIT:
            self.LAST_SEARCH_PAGE = page
            self.LAST_PROJECT_NUMBER = 0

            result = self.crawling_onepage(url + str(page), initialPath)

            # Category Find Terminate Condition check.
            if result == False: break
            page += 1
            self.write_progress_log(
                self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)
            
            time.sleep(60*20) # 한 페이지 크롤링 후 10분간 waiting
            # break # test


    # index 페이지를 기준으로 최대 25건의 데이터를 크롤링 하고 프로젝트 다운로드.
    # 1이면 정상종료, 0이면 비정상종료 (404, No Result)

    def crawling_onepage(self, url, initialPath):
        log.debug("crawling_onepage url="+url)
        # user-agent추가, tor proxy 경유 접속
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())

        # 404 Not Found
        if response.status_code == 404:
            log.error("requests.status_code = 404 : url="+url) 
            return False

        soup = BeautifulSoup(response.text, 'lxml')  # 성능 향상을 위해 lxml 파서 사용.

        # HTTP OK(200)이지만 내용이 없는 경우(No results found) 종료
        checkNoResult = soup.find(
            'section', {'class': "m-project-search-results"})

        if checkNoResult is None:
            log.error("requests.ConnectionError : url="+url) 
            return False

        result = checkNoResult.find('section', {'class': "project_info"})
        if result is not None and "No results found" in result.text:
            log.error("No results found : url="+url) 
            return False

        # 프로젝트 리스트 탐색
        prev_index = int(self.LAST_PROJECT_NUMBER)
        current_index = 0
        classList = soup.findAll('div', {'class': "result-heading-texts"})
        for classItem in classList:
            hrefList = classItem.findAll('a')
            for href in hrefList:
                current_index += 1
                # 기탐색된 프로젝트 스킵
                if current_index < prev_index:
                    self.LAST_PROJECT_NUMBER = (int(self.LAST_PROJECT_NUMBER) % 100) + 1
                    continue
                self.LAST_PROJECT_NUMBER = (
                    int(self.LAST_PROJECT_NUMBER) % 100) + 1
                # 프로젝트 기본정보 취득
                href_value = href.get('href')
                # self.printdetail(href_value, initialPath)
                progress_status = {
                    "LAST_PROJECT_NUMBER": self.LAST_PROJECT_NUMBER,
                    "LAST_SEARCH_CATEGORY": self.LAST_SEARCH_CATEGORY,
                    "LAST_SEARCH_PAGE": self.LAST_SEARCH_PAGE,
                    "PROGRESS_LOG_FILENAME": self.PROGRESS_LOG_FILENAME
                }
                project_tasks.get_project_info_from_sourceforge.delay(
                    href_value, initialPath, progress_status)

                log.debug("---------------"+href_value)
                self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

        return True


if __name__ == "__main__":
    crawler = SourceForgeCrawler()
    while(True):
        crawler.crawling()
        time.sleep(60*60)
