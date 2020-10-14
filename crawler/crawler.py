import abc
import platform
import re
import signal
import subprocess
import traceback
import logging, logging.config, logging.handlers
import os
import json
import sys
from copy import deepcopy
import requests
import psycopg2
import hashlib
from datetime import datetime
from GetRepoInfo import *
import VCSDownloader, md5hasher

from sshtunnel import SSHTunnelForwarder

from logger import getLogger
from common import getenv

from base_db import CrawlerDB

# global db_string
# # Server
# # db_string = "dbname='crawler' user='postgres' host='localhost' password='1234'"

# # local
# db_string = "dbname='crawler' user='postgres' host='localhost' port='15432' password='12345678'"

log = logging.getLogger(__name__) # getLogger(filename="sourceforge_crawler.log")

def dequote(str):
    if (len(str) > 0) and (str.find("'") != -1 or str.find('"') != -1):
        # 임시 싱글쿼테이션 오류
        str = str.replace("'", " ")
    return str


class OpenSourceInfo(object):
    def __init__(self,
                 projectName="",
                 projectUrl="",
                 summary="",
                 homepageUrl="",
                 createdOn="",
                 developer="",
                 category="",
                 programmingLanguage=[],
                 License="",
                 crawlerName="",
                 project_ver="UnKnown",
                 hasing=""):  # 0: stop 1:runnig
        self.projectName = dequote(projectName)
        self.projectUrl = projectUrl
        self.projectUrlHash = md5hasher.hashing(projectUrl)
        self.summary = summary
        self.homepageUrl = homepageUrl
        self.createdOn = str(createdOn)
        self.developer = developer
        self.category = category
        self.programmingLanguage = programmingLanguage
        self.License = License
        self.nameMargin = ""
        self.crawlerName = crawlerName
        self.project_ver = project_ver
        self.hasing = hasing
    
    def toJson(self):
        # data = deepcopy(self.__dict__)
        # del data["projectUrlHash"] # 생성자에서 만들어지는 멤버이기 때문에 삭제
        return json.dumps(self.__dict__)

    def __repr__(self):
        return self.toJson()


class CrawlingInfo(object):
    def __init__(self,
                 projectName="",
                 projectUrl="",
                 summary="",
                 homepageUrl="",
                 createdOn="",
                 developer="",
                 category="",
                 programmingLanguage=[],
                 License="",
                 crawlerName="",
                 project_ver="UnKnown",
                 hasing=""):  # 0: stop 1:runnig
        self.projectName = dequote(projectName)
        self.projectUrl = projectUrl
        self.projectUrlHash = md5hasher.hashing(projectUrl)
        self.summary = summary
        self.homepageUrl = homepageUrl
        self.createdOn = createdOn
        self.developer = developer
        self.category = category
        self.programmingLanguage = programmingLanguage
        self.License = License
        self.nameMargin = ""
        self.crawlerName = crawlerName
        self.project_ver = project_ver
        self.hasing = hasing

    def toJson(self):
        # data = deepcopy(self.__dict__)
        # del data["projectUrlHash"] # 생성자에서 만들어지는 멤버이기 때문에 삭제
        return json.dumps(self.__dict__)

    def __repr__(self):
        return self.toJson()

    def toString(self):
        for i in range(50 - len(self.projectName)):
            self.nameMargin += " "
        return "[" + self.projectName + "]" + \
               self.nameMargin + \
               ("u" if self.projectUrl != "" else "_") + \
               ("s" if self.summary != "" else "_") + \
               ("h" if self.homepageUrl != "" else "_") + \
               ("o" if self.createdOn != "" else "_") + \
               ("d" if self.developer != [] else "_") + \
               ("c" if self.category != "" else "_") + \
               ("p" if self.programmingLanguage != "" else "_") + \
               ("l" if self.License != "" else "_")

    def project_db_insert(self):
        try:
            crawler_db = CrawlerDB() #(port=15432, password='12345678')
        except Exception as e:
            raise e

        if self.developer == []:
            self.developer = {}

        self.pppid = self.project_db_exists()
        if self.pppid:
            return self.pppid

        try:
            if self.createdOn != "":
                self.createdOn = self.createdOn.strftime("%Y-%m-%d")
            else:
                self.createdOn = None

            value = self.crawlerName, self.projectName, self.projectUrl, self.summary, self.homepageUrl, self.createdOn, self.category, self.License, self.programmingLanguage, self.project_ver
            query = '''
            INSERT INTO dpa_crawler_project_tb(crawler_name, project_name, project_url, summary, homepage_url, created_DT, category, license, programming_lang, project_ver) 
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (project_name, crawler_name, project_url)
            DO UPDATE SET
                (summary, homepage_url, created_DT, category, license, programming_lang, project_ver)
                = (EXCLUDED.summary, EXCLUDED.homepage_url, EXCLUDED.created_DT, EXCLUDED.category, EXCLUDED.license, EXCLUDED.programming_lang, EXCLUDED.project_ver)
            '''
            log.debug(query)
            log.debug(value)
            crawler_db.execute(query, ((value)))
            log.warning("project_tb {}      : done".format(self.projectName))
            value = self.crawlerName, self.projectName
            query = "SELECT max(pid) as p FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            self.pppid = result[0].p

            value = self.pppid, self.projectName, self.developer
            query = '''
                INSERT INTO dpa_crawler_project_name_tb(pid,project_name, developer) VALUES( %s, %s, %s)
                ON CONFLICT (project_name, developer)
                DO UPDATE SET
                    (project_name, developer, pid) = (EXCLUDED.project_name, EXCLUDED.developer, EXCLUDED.pid)
            '''
            log.debug(query)
            log.debug(value)
            crawler_db.execute(query, ((value)))
        except Exception as e:
            log.error(e)
            value = self.crawlerName, self.projectName
            query = "SELECT max(pid) as p FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
            log.error(query)
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            self.pppid = result[0].p

        return self.pppid


    def project_file_db_exists(self, release_ver):
        try:
            crawler_db = CrawlerDB() #(port=15432, password='12345678')
        except Exception as e:
            raise e
        try:
            value = self.projectName, self.crawlerName, release_ver
            query = '''
            select t1.pid as p1, t2.release_id as p2 
            from dpa_crawler_project_tb t1 inner join dpa_crawler_release_tb t2 on t1.pid = t2.pid 
            WHERE t1.project_name = '%s' AND t1.crawler_name = '%s' AND t2.release_ver = '%s'
            ''' % value
            log.debug(query)
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            if len(result) > 0:
                return result[0].p2
            log.error(" DB search error1 project={}, release_ver={}".format(self.projectName, release_ver))
        except Exception as e:
            log.error(e)
        return False

    def project_file_db_insert(self, fileInfo):
        try:
            crawler_db = CrawlerDB() #(port=15432, password='12345678')
        except Exception as e:
            raise e

        try:
            val = self.crawlerName, self.projectName
            query = "SELECT max(pid) as p FROM dpa_crawler_project_tb WHERE crawler_name = '%s' AND project_name = '%s'" % val
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            ppid = result[0].p

            release_ver = fileInfo[1] if fileInfo[1] is not None else 'UnKnown'
            fileInfo[0] = os.path.join(fileInfo[0], self.projectName) # fileInfo[0] + self.projectName + "/"
            if len(fileInfo) > 3:
                if self.crawlerName == "eclipse_re":
                    fileInfo[0] = os.path.join(fileInfo[0], fileInfo[3]) # fileInfo[0] + fileInfo[3] + "/"
            fileInfo[0] = os.path.join(fileInfo[0], release_ver) # fileInfo[0] + fileInfo[1]
            try:
                fileInfo[2] = datetime.strptime(fileInfo[2], "%Y-%m-%d").date().strftime('%Y-%m-%d')
            except:
                fileInfo[2] = '1900-01-01' # unknown 값
            hashing = hashlib.md5(fileInfo[0].encode('utf-8'))
            self.hashing = hashing.hexdigest() # str(hashing).split("@ ")[1].split(">")[0] <-- 왜 이런 코들를 썼을까?
            DOWNLOAD_DT = datetime.now().strftime('%Y-%m-%d')

            value = int(ppid), fileInfo[0], release_ver, fileInfo[2], DOWNLOAD_DT, self.hasing
            log.debug(value)
            query = """
            INSERT INTO dpa_crawler_release_tb(pid,file_dir, release_ver, release_dt, download_dt ,hashing) 
            VALUES( %s, '%s', '%s','%s', '%s', '%s')
            ON CONFLICT (pid, release_ver)
            DO UPDATE SET
                (release_ver, release_dt, download_dt, hashing)
                = (EXCLUDED.release_ver, EXCLUDED.release_dt, EXCLUDED.download_dt, EXCLUDED.hashing)
            """
            query = query % value
            log.debug(query)
            crawler_db.execute(query)
            return True
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            return False

    def project_db_exists(self):
        try:
            crawler_db = CrawlerDB() #(port=15432, password='12345678')
        except Exception as e:
            raise e
        
        if self.developer == []: self.developer = {}
        try:
            value = self.projectName, self.developer, self.crawlerName
            query = '''
            select t1.pid as p 
            from dpa_crawler_project_name_tb t1 inner join dpa_crawler_project_tb t2 on t1.pid = t2.pid 
            WHERE t1.project_name = '%s' AND t1.developer = '%s' AND t2.crawler_name = '%s'
            ''' % value
            log.debug(query)
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            if len(result) > 0:
                self.pppid = result[0].p
                return (self.pppid)
            log.error(" DB search error1 project={}".format(self.projectName))
        except Exception as e:
            log.error(e)
            log.error(" DB search error2 project={}".format(self.projectName))
        return False


class Crawler:
    def __init__(self, name):
        self.name = name
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.initialpath = getenv("DOWNLOAD_PATH") # BASE_DIR + "/../data"
        self.crawlingList = []
        self.crawlDir = self.initialpath + "/" + name + "Dir"
        self.badge = '[crawler_' + self.name + '] '

        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signal, frame):
        os.chdir(self.initialpath)
        self.log.error(self.badge + 'Terminate, save progress information.')
            # progress.write(self.url)
        self.log.warning(self.badge + 'Bye!')
        sys.exit(0)

    @abc.abstractmethod
    def preCrawling(self):
        pass

    @abc.abstractmethod
    def crawlingAction(self):
        pass

    def make_working_directory(self):
        try:
            os.chdir(self.crawlDir)
        except:
            os.mkdir(self.crawlDir)
            os.chdir(self.crawlDir)
    
    def crawling(self):
        self.make_working_directory()

        self.preCrawling()
        
        self.crawlingAction()


class DataBase_Crawler_DB:
    def __init__(self,
                 crawlerName="",
                 crawlerStatus=""):  # 0: stop 1:runnig
        self.CrawlerName = crawlerName
        self.CrawlerStatus = crawlerStatus
        return

    def crawler_db_insert(self):
        now = datetime.now()
        time = now.strftime("%Y-%m-%d %H:%M:%S")
        log.debug(time)
        try:
            crawler_db = CrawlerDB() #(port=15432, password='12345678')
        except Exception as e:
            raise e
        try:
            value = self.CrawlerName, self.CrawlerStatus, time
            query = """
            INSERT INTO dpa_crawler_tb(crawler_name, crawler_status, update_time) 
            VALUES(%s,%s,%s)
            ON CONFLICT (crawler_name)
            DO UPDATE SET
                (crawler_status, update_time)
                = (EXCLUDED.crawler_status, EXCLUDED.update_time)
            """
            crawler_db.execute(query, (value))
            log.debug("crawler_tb Done")
        except Exception as e:
            log.error(e)

        # try:
        #     conn = psycopg2.connect(db_string)
        #     conn.autocommit = True
        #     cur = conn.cursor()
        #     value = self.CrawlerName, self.CrawlerStatus, time
        #     query = "INSERT INTO dpa_crawler_tb(crawler_name, crawler_status, update_time) VALUES(%s,%s,%s)"
        #     cur.execute(query, (value))
        #     conn.commit()
        #     print("crawler_tb Done")

        # except:
        #     conn = psycopg2.connect(db_string)
        #     conn.autocommit = True
        #     cur = conn.cursor()
        #     value = self.CrawlerStatus, time, self.CrawlerName,
        #     query = "UPDATE dpa_crawler_tb SET crawler_status = %s, update_time = %s where crawler_name = %s"
        #     cur.execute(query, (value))
        #     conn.commit()
        #     print("crawler_tb Time Updated")