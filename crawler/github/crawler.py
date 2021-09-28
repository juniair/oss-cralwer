import os
import sys
import json
import random
import shutil
import requests
import urllib.parse
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import platform
import time
from signal import *

import md5hasher
import GetRepoInfo
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from logger import getLogger, write_progress_log
from common import get_http_headers, get_tor_proxy, getenv

from github import project_page as project_tasks

log = getLogger(filename="github_crawler.log")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir"  # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_github.json"


class GithubCrawler(Crawler):
    MAX_PROJECT = 100
    # Github 조회리스트
    LANGUAGE = [
        "Java",
        "C++",
        "C#",
        "C",
        "JavaScript",
        "Python",
        "Ruby",
        "PHP",
        "Objective-C",
        "Kotlin",
        "Scala",
        "Vue",
        "Haskell",
        "ActionScript",
        "Clojure",
        "Perl",
        "Swift",
        "Visual Basic",
        "go",
        "TypeScript",
        "Rust",
        "PowerShell",
        "ocaml",
    ]

    def __init__(self):
        super(GithubCrawler, self).__init__(name="github")
        self.headers = {
            "Authorization": "token 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"
        }
        self.maximum_delta = 730
        self.delta = 1
        self.page = 1
        self.sum_delta = 1
        self.keyword = "Java"
        self.PROGRESS_LOG_FILENAME = self.initialpath + "/progress_{}.json".format(
            self.name
        )
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame):
        print("signum=", signum)
        DataBase_Crawler_DB(
            crawlerName="github_re", crawlerStatus="0"
        ).crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        log.debug(self.PROGRESS_LOG_FILENAME)
        with open(self.PROGRESS_LOG_FILENAME, "w") as progress:
            json.dump(
                {
                    "maximum_delta": self.maximum_delta,
                    "delta": self.delta,
                    "sum_delta": self.sum_delta,
                    "page": self.page,
                    "keyword": self.keyword,
                },
                progress,
            )

    def read_progress_log(self):
        log.debug(self.PROGRESS_LOG_FILENAME)
        if os.path.isfile(self.PROGRESS_LOG_FILENAME):
            with open(self.PROGRESS_LOG_FILENAME, "r", encoding="utf-8") as progress:
                lastprogress = json.load(progress)
                self.maximum_delta = lastprogress["maximum_delta"]
                self.delta = lastprogress["delta"]
                self.sum_delta = lastprogress["sum_delta"]
                self.page = lastprogress["page"]
                self.keyword = lastprogress["keyword"]
        else:
            with open(self.PROGRESS_LOG_FILENAME, "w") as progress:
                json.dump(
                    {
                        "maximum_delta": self.maximum_delta,
                        "delta": self.delta,
                        "sum_delta": self.sum_delta,
                        "page": self.page,
                        "keyword": self.keyword,
                    },
                    progress,
                )

    def preCrawling(self):
        log.debug(os.getcwd())
        # 임의의 언어 선택
        self.keyword = random.choice(self.LANGUAGE)
        self.read_progress_log()

    def search_project_page(self, keyword, page, start_date, end_date):
        url = "https://api.github.com/search/repositories?q=language:{}+created:{}..{}&order=asc&per_page={}&page={}".format(
            urllib.parse.quote(keyword),
            start_date,
            end_date,
            self.MAX_PROJECT,
            str(page),
        )
        log.warning("[crawler_github] " + url + " : Searching...")
        data = None
        try:
            self.headers.update(get_http_headers())
            log.debug(self.headers)
            response = requests.get(url, headers=self.headers, proxies=get_tor_proxy())
            if response.status_code == 200:
                text = response.text
                data = json.loads(text)
                # check next page exist. if not, break.
            if "next" in response.links.keys():
                self.page += 1
        except Exception as e:
            log.error(str(e))
        # log.debug(data)
        return data

    def get_current_status(self):
        return {
            "maximum_delta": self.maximum_delta,
            "delta": self.delta,
            "sum_delta": self.sum_delta,
            "page": self.page,
            "keyword": self.keyword,
        }

    def crawlingAction(self):
        current = datetime.datetime.utcnow()

        initialPath = download_path  # os.getcwd()
        log.warning("crawlingAction : initialPath=" + initialPath)
        os.chdir(initialPath)

        # 조사 대상 언어를 복사하고 섞는다.
        # 크롤링을 비규칙적으로 해서 균등하게 되도록 하려는 목적.
        keyword_list = self.LANGUAGE.copy()
        random.shuffle(keyword_list)

        DataBase_Crawler_DB(
            crawlerName="github_re", crawlerStatus="1"
        ).crawler_db_insert()
        # 최종 기록된 키워드 부터
        checked_keyword_index = keyword_list.index(self.keyword.strip())
        for gitkeyword in keyword_list[checked_keyword_index:]:
            self.keyword = gitkeyword

            log.info("=================Now Keyword : " + self.keyword)

            current_path = initialPath

            # github search API는 최대 1,000건만 조회 가능함
            # github 사이트 오픈일부터 현재까지 월별 검색
            # 2008년        1년 * 11개월 * 1,000건 =  11,000건
            # 2009~2020년  12년 * 12개월 * 1,000건 = 144,000건
            # 2021년        1년 * 10개월 * 1,000건
            current_date = current.date()
            start_date = datetime.date(2008, 2, 1)
            while start_date < current_date:
                month_rage = calendar.monthrange(start_date.year, start_date.month)
                end_date = start_date.replace(day=month_rage[1])
                while True:
                    self.write_progress_log()
                    dictionary = self.search_project_page(
                        gitkeyword, self.page, start_date, end_date
                    )
                    if dictionary is None:
                        log.warning("[crawler_github] Error or No Result")
                        break

                    #  Project information print
                    for item in dictionary["items"]:
                        log.warning("call get_release_info : {}".format(item["name"]))
                        project_tasks.get_release_info.delay(
                            item, current_path, self.get_current_status()
                        )

                    time.sleep(60 * 60)  # wait for 60 minutes
                    # break # test

                start_date += relativedelta(months=1)
                # 다음 키워드 검색을 위하여 초기화
                self.sum_delta = 1
                self.page = 1
                time.sleep(60 * 5)  # wait reset api call count for 5 minutes.

            os.chdir(initialPath)

            time.sleep(60 * 60 * 2)  # wait for 2 hours
            # break # test

        # 완료 후 초기화
        self.maximum_delta = 730
        self.sum_delta = 1
        self.page = 1
        self.keyword = keyword_list[0]

        self.write_progress_log()

        DataBase_Crawler_DB(
            crawlerName="github_re", crawlerStatus="0"
        ).crawler_db_insert()
        # signal_handler(signal.SIGTERM, None)


if __name__ == "__main__":
    crawler = GithubCrawler()
    crawler.crawling()
