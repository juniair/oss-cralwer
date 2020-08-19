import pdb
import platform
import time

import zipfile_custom

from bs4 import BeautifulSoup
import io
import re
from functools import reduce
from crawler import *
import shutil
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="codeplex_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

#for sig in (SIGABRT, SIGFPE, SIGBREAK, SIGILL, SIGINT, SIGSEGV, SIGTERM):
for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)


class CodeplexCrawler(Crawler):
    def __init__(self):
        super(CodeplexCrawler, self).__init__(name="codeplex")
        self.index = ''

    def preCrawling(self):
        try:
            with open('progress_codeplex.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.index = lastprogress['index']
        except:
            with open('progress_codeplex.json', 'w') as progress:
                json.dump({'index': ''}, progress)

    def crawlingAction(self):
        initialpath = os.getcwd()
        # OS에 맞는 경로 설정
        while (True):
            #a~z까지 프로젝트명을 뽑아와서 정렬시킨 후 사이트에서 파싱한다.
            Result = list(map(lambda x: json.loads(requests.get("https://codeplexarchive-search.search.windows.net/indexes/codeplexarchive-index/docs?api-version=2016-09-01&api-key=44C8CF90A6561D9EC9A1BBA09250FEA1&$top=100&highlight=Title&search=" + x + "%20" + x + "*").text),
                      map(chr, range(97, 123))))
            ResultTitle = list(map(lambda y: list(map(lambda x: x['ProjectName'], y['value'])), Result))
            ReduceTitle = reduce(lambda x, y: x + y, ResultTitle)
            modifiedResult = sorted(list(set(ReduceTitle)),key=str.lower)

            skip = True
            for item in modifiedResult:
                DataBase_Crawler_DB(
                    crawlerName="codeplex_re",
                    crawlerStatus='1').crawler_db_insert()
                print(item)
                if (self.index == '') or (self.index == item):
                    skip = False

                if skip:
                    print("Skip")
                    continue
# projectName
                projectName = item
                lowerPN = item.lower()
# projectUrl
                projectUrl = "https://archive.codeplex.com/?p=" + projectName
                projectSoup = BeautifulSoup(requests.get(projectUrl).text, "html.parser")
                loadjs = "https://archive.codeplex.com/metadata/" + lowerPN + ".json"
                projectinfo = json.loads(requests.get(loadjs).text)
# summary
                summary = projectinfo['Description']
# category
                category = projectinfo['TagList']
# homepageUrl
                try:
                    homepageUrl = projectinfo['MovedLink']
                except:
                    homepageUrl = ""
# programmingLanguage
                try:
                    pl_pattern = re.compile('java(\w)*|c#|c\+\+|python|php|scala|kotlin|swift|vue|visual basic|\.NET|groovy|jsp|asp|pascal|javascript', re.I)
                    pl_search = pl_pattern.search(category)
                    programmingLanguage = pl_search.group()
                except:
                    programmingLanguage = ""
# version
                try:
                    htmlsource = projectinfo['HomeWiki']
                    ver_pattern = re.compile('(version|ver|v)(\s)?(\d[.]?)+', re.I)
                    ver_match = ver_pattern.match(htmlsource)
                    version = ver_match.group()
                except:
                    version = "UnKnown"
# developer
                developer = []
                # LastEdited
                try:
                    rel_createdOn = projectinfo['LastEdited'].replace('T', ' ').split(' ')[0]
                except:
                    rel_createdOn = ""
# Zipdownload
                URL = "https://codeplexarchive.blob.core.windows.net/archive/projects/" + projectName +"/" + projectName + ".zip"

                file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                    "\\codeplexDir\\" if platform.system() == "Windows" else "/codeplexDir/")
                print("file_dir : " + file_dir)

                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)

                try:
                    os.chdir(version)
                except:
                    os.mkdir(version)
                    os.chdir(version)

                local_filename = URL.split('/')[-1]
                r = requests.get(URL, stream=True)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                # codeplex의 zip파일이 압축해제 시 우분투서버에서 path 구분자가 / 가 아니라 \ 로 잡혀서 내장에서 따로 빼내서 커스텀함
                with zipfile_custom.ZipFile(local_filename) as z:
                    z.extractall()
                os.remove(local_filename)

                os.chdir('license')
                with open('license.json', 'r') as li:
# License
                    json_data = json.load(li)
                    try:
                        License = json_data["Name"]
                    except:
                        License = ""
# createdOn
                    try:
                        temp = json_data["StartDate"]
                        co_pattern = re.compile('\d{13}')
                        co_match = co_pattern.search(temp)
                        temp2 = co_match.group()[0:10]
                        createdOn = datetime.fromtimestamp(int(temp2))
                    except:
                        createdOn = ""

                self.crawlingList.append(CrawlingInfo(
                     crawlerName="codeplex_re",
                     projectName=projectName,
                     projectUrl=projectUrl,
                     summary=summary,
                     homepageUrl=homepageUrl,
                     createdOn=createdOn,
                     developer=developer,
                     programmingLanguage=programmingLanguage,
                     License=License,
                     category=category,
                     project_ver=version,
                ))
                os.chdir(initialpath)
                pid = self.crawlingList[-1].project_db_insert()

                revision = version

                fileInfo = [file_dir, revision, rel_createdOn]
                self.crawlingList[-1].project_file_db_insert(fileInfo)
                print("\r" + self.crawlingList[-1].toString())

                newdirname = str(pid)
                print(newdirname)
                try:
                    if os.path.isdir(newdirname):
                        shutil.rmtree(newdirname)
                        time.sleep(1)
                        os.rename(projectName, newdirname)
                    else:
                        os.rename(projectName, newdirname)
                except Exception as e:
                    print(e)
                    print('Rename Error')
                with open('../progress_codeplex.json', 'w') as progress:
                    json.dump({'index': item}, progress)

            DataBase_Crawler_DB(
                crawlerName="codeplex_re",
                crawlerStatus='0').crawler_db_insert()

crawler = CodeplexCrawler()
crawler.crawling()
