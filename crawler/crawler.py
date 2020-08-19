import abc
import platform
import re
import signal
import subprocess

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

from common import getenv

from base_db import CrawlerDB

# global db_string
# # Server
# # db_string = "dbname='crawler' user='postgres' host='localhost' password='1234'"

# # local
# db_string = "dbname='crawler' user='postgres' host='localhost' port='15432' password='12345678'"


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
        # try:
        #     value = self.projectName, self.developer
        #     query = "SELECT pid, project_name FROM dpa_crawler_project_name_tb WHERE project_name = '%s' AND developer = '%s'" % value
        #     crawler_db.execute(query)
        #     result = crawler_db.fetchall()
        #     if len(result) > 0:
        #         self.pppid = result[0].pid
        #         return self.pppid
        # except Exception as e:
        #     print(e)

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
            crawler_db.execute(query, ((value)))
            print("project_tb       : done")
            value = self.crawlerName, self.projectName
            query = "SELECT max(pid) as p FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            self.pppid = result[0].p

            value = self.pppid, self.projectName, self.developer
            query = '''
                INSERT INTO dpa_crawler_project_name_tb(pid,project_name, developer) VALUES( %s, %s, %s)
                ON CONFLICT (pid)
                DO UPDATE SET
                    (project_name, developer) = (EXCLUDED.project_name, EXCLUDED.developer)
            '''
            crawler_db.execute(query, ((value)))
        except Exception as e:
            print(e)
            value = self.crawlerName, self.projectName
            query = "SELECT max(pid) as p FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            self.pppid = result[0].p

        return self.pppid

        # try:
        #     if self.developer == []:
        #         self.developer = {}

        #     print(self.projectName)
        #     conn = psycopg2.connect(db_string)
        #     conn.autocommit = True
        #     cur = conn.cursor()
        #     value = self.projectName, self.developer
        #     query = "SELECT pid, project_name FROM dpa_crawler_project_name_tb WHERE project_name = '%s' AND developer = '%s'" % value
        #     cur.execute(query)
        #     pid = cur.fetchall()
        #     ppid = pid[0][-1]
        #     if self.developer == {}:
        #         self.developer = []
        #     if (ppid != True):
        #         if self.createdOn != "":
        #             self.createdOn = self.createdOn.strftime("%Y-%m-%d")
        #         else:
        #             self.createdOn = None

        #         conn = psycopg2.connect(db_string)
        #         cur = conn.cursor()
        #         value = self.crawlerName, self.projectName, self.projectUrl, self.summary, self.homepageUrl, self.createdOn, self.category, self.License, self.programmingLanguage, self.project_ver
        #         query = '''
        #         INSERT INTO dpa_crawler_project_tb(crawler_name, project_name, project_url, summary, homepage_url, created_DT, category, license, programming_lang, project_ver) 
        #         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        #         ON CONFLICT (project_name, crawler_name, project_url)
        #         DO UPDATE SET
        #             (summary, homepage_url, created_DT, category, license, programming_lang, project_ver)
        #             = (EXCLUDED.summary, EXCLUDED.homepage_url, EXCLUDED.created_DT, EXCLUDED.category, EXCLUDED.license, EXCLUDED.programming_lang, EXCLUDED.project_ver)
        #         '''
        #         cur.execute(query, ((value)))
        #         conn.commit()
        #         print("project_tb       : done")
        #         value = self.crawlerName, self.projectName
        #         query = "SELECT max(pid) FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
        #         cur.execute(query)
        #         pid = cur.fetchall()
        #         self.pppid = int(pid[0][0])
        #         print("pid              : " + str(self.pppid))

        #         try:
        #             value = self.pppid, self.projectName, self.developer

        #             query = '''
        #                 INSERT INTO dpa_crawler_project_name_tb(pid,project_name, developer) VALUES( %s, %s, %s)
        #                 ON CONFLICT (pid)
        #                 DO UPDATE SET
        #                     (project_name, developer) = (EXCLUDED.project_name, EXCLUDED.developer)
        #             '''
        #             cur.execute(query, ((value)))
        #             conn.commit()
        #             value = self.crawlerName, self.projectName
        #             query = "SELECT max(pid) FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name ='%s'" % value
        #             cur.execute(query)
        #             pid = cur.fetchall()
        #             self.pppid = int(pid[0][0])
        #             print("project_name_tb  : done")

        #             return (self.pppid)
        #         except Exception as e:
        #             query = "SELECT max(pid) FROM dpa_crawler_project_tb WHERE crawler_name = '%s'" % self.crawlerName
        #             cur.execute(query)
        #             pid = cur.fetchall()
        #             self.pppid = int(pid[0][0])
        #             print(e)
        #             print("project_name_TB  : error")
        #             return (self.pppid)

        #     else:
        #         value = self.crawlerName, self.projectName
        #         query = "SELECT max(pid) FROM dpa_crawler_project_tb WHERE crawler_name = '%s' and project_name = '%s'" % value
        #         cur.execute(query)
        #         pid = cur.fetchall()
        #         self.pppid = int(pid[0][0])
        #         print("already it existed 1")
        #         return (self.pppid)

        # except Exception as e:
        #     print(e)
        #     conn = psycopg2.connect(db_string)
        #     conn.autocommit = True
        #     cur = conn.cursor()
        #     val = self.projectName
        #     query = "select pid from dpa_crawler_project_name_tb where project_name = '%s'" % val
        #     cur.execute(query)
        #     pid = cur.fetchall()
        #     ppid = int(pid[0][0])
        #     print("already it existed 2")
        #     return (ppid)

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

            fileInfo[0] = os.path.join(fileInfo[0], self.projectName) # fileInfo[0] + self.projectName + "/"
            if len(fileInfo) > 3:
                if self.crawlerName == "eclipse_re":
                    fileInfo[0] = os.path.join(fileInfo[0], fileInfo[3]) # fileInfo[0] + fileInfo[3] + "/"
            fileInfo[0] = os.path.join(fileInfo[0], fileInfo[1]) # fileInfo[0] + fileInfo[1]
            try:
                fileInfo[2] = datetime.strptime(fileInfo[2], "%Y-%m-%d").date().strftime('%Y-%m-%d')
            except:
                fileInfo[2] = '1900-01-01' # unknown 값
            hashing = hashlib.md5(fileInfo[0].encode())
            self.hashing = str(hashing).split("@ ")[1].split(">")[0]
            DOWNLOAD_DT = datetime.now().strftime('%Y-%m-%d')

            value = int(ppid), fileInfo[0], fileInfo[1], fileInfo[2], DOWNLOAD_DT, self.hasing
            query = """
            INSERT INTO dpa_crawler_release_tb(pid,file_dir, release_ver, release_dt, download_dt ,hashing) 
            VALUES( %s, '%s', '%s','%s', '%s', '%s')
            ON CONFLICT (pid, release_ver)
            DO UPDATE SET
                (release_ver, release_dt, download_dt, hashing)
                = (EXCLUDED.release_ver, EXCLUDED.release_dt, EXCLUDED.download_dt, EXCLUDED.hashing)
            """
            query = query % value
            print("insert release_tb : ", query)
            crawler_db.execute(query)
        except Exception as e:
            print(e)

        # try:
        #     # print(self.projectName)
        #     # fileInfo = [ file_dir, release_ver, rel_createdOn ]
        #     conn = psycopg2.connect(db_string)
        #     conn.autocommit = True
        #     cur = conn.cursor()
        #     val = self.crawlerName, self.projectName
        #     query = "SELECT max(pid) FROM dpa_crawler_project_tb WHERE crawler_name = '%s' AND project_name = '%s'" % val
        #     cur.execute(query)
        #     pid = cur.fetchall()
        #     ppid = int(pid[0][0])
        #     # fileInfo[0] = fileInfo[0] + str(ppid) + "/" #("\\" if platform.system() == "Windows" else "/")
        #     fileInfo[0] = fileInfo[0] + self.projectName + "/" # pid 값으로 폴더가 rename되지 않기 때문에 프로젝트 이름을 넣어서 생성
        #     # 이클립스는 project > title > release 로 디렉토리가 생성되서 fileInfo[4]추가
        #     if len(fileInfo) > 3:
        #         if self.crawlerName == "eclipse_re":
        #             fileInfo[0] = fileInfo[0] + fileInfo[3] + "/" #("\\" if platform.system() == "Windows" else "/")
        #     fileInfo[0] = fileInfo[0] + fileInfo[1]
        #     try:
        #         fileInfo[2] = datetime.strptime(fileInfo[2], "%Y-%m-%d").date().strftime('%Y-%m-%d')
        #     except:
        #         fileInfo[2] = '1900-01-01' # unknown 값
        #     self.hasing = hashlib.md5(fileInfo[0].encode())
        #     self.hasing = str(self.hasing).split("@ ")[1].split(">")[0]
        #     DOWNLOAD_DT = datetime.now().strftime('%Y-%m-%d')

        #     value = int(ppid), fileInfo[0], fileInfo[1], fileInfo[2], DOWNLOAD_DT, self.hasing
            
        #     # primary key의 경우는 unique/exclude 가 아니기 때문에 
        #     # ON CONSTRAINT [primary key 이름] 을 인덱스 대신에 추가 해야 한다.
        #     query = """
        #     INSERT INTO dpa_crawler_release_tb(pid,file_dir, release_ver, release_dt, download_dt ,hashing) 
        #     VALUES( %s, '%s', '%s','%s', '%s', '%s')
        #     ON CONFLICT (pid, release_ver)
        #     DO UPDATE SET
        #         (release_ver, release_dt, download_dt, hashing)
        #         = (EXCLUDED.release_ver, EXCLUDED.release_dt, EXCLUDED.download_dt, EXCLUDED.hashing)
        #     """
        #     query = query % value
        #     print("insert release_tb : ", query)
        #     cur.execute(query)
        #     conn.commit()
        #     print("release_tb  : done")
        # except Exception as e:
        #     print(e)
        #     print("release_tb  : error")
        #     raise e # 릴리스테이블에 정상적으로 데이터가 추가 되지 않으면 예외오류를 전파한다.

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
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            if len(result) > 0:
                self.pppid = result[0].p
                return (self.pppid)
            print(str(self.projectName) + " DB search error1")
        except Exception as e:
            print(e)
            print(str(self.projectName) + " DB search error2")
        return False

        # try:
        #     if self.developer == []:
        #         self.developer = {}
        #     conn = psycopg2.connect(db_string)
        #     cur = conn.cursor()
        #     value = self.projectName
        #     query = "select exists(select t1.pid from dpa_crawler_project_tb t1 join dpa_crawler_project_name_tb t2  on (t1.pid = t2.pid) WHERE t1.project_name = '%s')" % value
        #     cur.execute(query)
        #     chkDB = cur.fetchall()[0][0]
        #     #print(str(self.projectName) + " DB already exists : " + str(chkDB))

        #     if (chkDB == True):
        #         conn = psycopg2.connect(db_string)
        #         cur = conn.cursor()
        #         value = self.projectName, self.developer, self.crawlerName
        #         query = "select t1.pid from dpa_crawler_project_name_tb t1 inner join dpa_crawler_project_tb t2 using (pid) WHERE t1.project_name = '%s' AND t1.developer = '%s' AND t2.crawler_name = '%s'" % value
        #         cur.execute(query)
        #         pid = cur.fetchall()
        #         self.pppid = int(pid[0][0])
        #         return (self.pppid)
        #     else:
        #         print(str(self.projectName) + " DB search error1")
        #         return False
        # except Exception as e:
        #     print(str(self.projectName) + " DB search error2")
        #     print(str(e))
        #     return False
        # finally:
        #     conn.close()


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
        print(time)
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
            print("crawler_tb Done")
        except Exception as e:
            print(e)

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