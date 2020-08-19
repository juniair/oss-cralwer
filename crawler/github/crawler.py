import os, sys, json
import shutil
import requests
import urllib.parse
import datetime
import platform
from signal import *

import md5hasher
import GetRepoInfo
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from logger import getLogger, write_progress_log

from github import project_page as project_tasks

log = getLogger(filename="github_crawler.log")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = BASE_DIR + "/../../data"  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir" # sourceforge 프로젝트 다운로드 경로

class GithubCrawler(Crawler):
    def __init__(self):
        super(GithubCrawler, self).__init__(name="github")
        self.headers= {'Authorization': "token 1d85c431af3ddeaed5e36c9b1e2dd2956943c661"}
        self.maximum_delta = 730
        self.delta = 1
        self.page = 1
        self.sum_delta = 1
        self.keyword = "Java"
        self.PROGRESS_LOG_FILENAME = self.initialpath + "/progress_{}.json".format(self.name)
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

    def handler(self, signum, frame):
        print("signum=", signum)
        DataBase_Crawler_DB(crawlerName="sourceforge_re",
                            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    def write_progress_log(self):
        log.debug(self.PROGRESS_LOG_FILENAME)
        with open(self.PROGRESS_LOG_FILENAME, 'w') as progress:
            json.dump({'maximum_delta': self.maximum_delta,'delta': self.delta,'sum_delta': self.sum_delta,'page': self.page, 'keyword': self.keyword}, progress)

    def read_progress_log(self):
        log.debug(self.PROGRESS_LOG_FILENAME)
        if os.path.isfile(self.PROGRESS_LOG_FILENAME):
            with open(self.PROGRESS_LOG_FILENAME, 'r', encoding="utf-8") as self.progress:
                lastprogress = json.load(self.progress)
                self.maximum_delta = lastprogress['maximum_delta']
                self.delta = lastprogress['delta']
                self.sum_delta = lastprogress['sum_delta']
                self.page = lastprogress['page']
                self.keyword = lastprogress['keyword']
        else:
            with open(self.PROGRESS_LOG_FILENAME, 'w') as progress:
                json.dump({
                    'maximum_delta': self.maximum_delta,
                    'delta': self.delta,
                    'sum_delta': self.sum_delta,
                    'page': self.page, 
                    'keyword' : self.keyword}, progress)

    def preCrawling(self):
        log.debug(os.getcwd())
        self.read_progress_log()
    

    def search_project_page(self, start, end):
        url = "https://api.github.com/search/repositories?q=language:{3}+created:{0}..{1}&order=asc&per_page=100&page={2}"\
            .format(start, end, str(self.page), urllib.parse.quote(self.keyword))
        log.warning("[crawler_github] " + url + " : Searching...")
        data = None
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                text = response.text
                data = json.loads(text)
                # check next page exist. if not, break.
            if 'next' in response.links.keys(): 
                self.page += 1
        except Exception as e:
            log.error(str(e))
        
        return data 


    def rename_directory(self, projectName, pid):
        org_path = os.getcwd()
        os.chdir(download_path)
        log.debug("rename_directory: current directory="+download_path+"/"+projectName)
        try:
            newdirname = str(pid)
            log.debug("Rename " + projectName + " > " + newdirname)
            if os.path.exists(projectName):
                if os.path.isdir(newdirname):
                    shutil.rmtree(newdirname)
                os.rename(projectName, newdirname)
        except Exception as e:
            log.error(str(e))
        os.chdir(org_path)
        
    def get_current_status(self):
        return {'maximum_delta': self.maximum_delta,'delta': self.delta,'sum_delta': self.sum_delta,'page': self.page, 'keyword': self.keyword}

    def crawlingAction(self):
        current = datetime.datetime.utcnow()

        initialPath = os.getcwd()
        log.warning("crawlingAction : initialPath="+initialPath)

        # Github 조회리스트
        keyword_list = ["Java", "C++", "C#", "C", "JavaScript", "Python", "Ruby", "PHP", "Objective-C", "Kotlin", "Swift"
                        "Scala", "Vue", "Haskell", "ActionScript", "Clojure", "Perl", "Swift", "Visual Basic"]

        # 최종 기록된 키워드 부터 
        checked_keyword_index = keyword_list.index(self.keyword.strip())
        for gitkeyword in keyword_list[checked_keyword_index:]:
            self.keyword = gitkeyword

            log.debug("=================Now Keyword : " + self.keyword)

            current_path = initialPath
            while self.sum_delta <= self.maximum_delta:
                DataBase_Crawler_DB(
                    crawlerName="github_re",
                    crawlerStatus='1').crawler_db_insert()
                target = current - datetime.timedelta(days=self.sum_delta)
                start = str(target).split('.')[0].replace(' ', 'T')
                target2 = target + datetime.timedelta(days=self.delta)
                end = str(target2).split('.')[0].replace(' ', 'T')
                # page = 1
                while True:
                    dictionary = self.search_project_page(start, end)
                    if dictionary is None: 
                        log.warning("[crawler_github] Error or No Result")
                        break

                    #  Project information print
                    for item in dictionary['items']:
                        project_tasks.get_release_info.delay(item, current_path, self.get_current_status())

                self.sum_delta += self.delta
                #다음날짜 탐색시 1페이지부터 탐색하도록
                self.page = 1
                self.write_progress_log()

                print("sum_delta : " + str(self.sum_delta))
                os.chdir(initialPath)

            # 다음 키워드 검색을 위하여 초기화
            self.sum_delta = 1
            self.page = 1

        #완료 후 초기화
        self.maximum_delta = 730
        self.sum_delta = 1
        self.page = 1
        self.keyword = keyword_list[0]
        
        self.write_progress_log()

        DataBase_Crawler_DB(
            crawlerName="github_re",
            crawlerStatus='0').crawler_db_insert()
        # signal_handler(signal.SIGTERM, None)

if __name__ == "__main__":
    crawler = GithubCrawler()
    crawler.crawling()