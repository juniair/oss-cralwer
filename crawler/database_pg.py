import psycopg2
import md5hasher
from datetime import datetime

global  db_string
db_string = "dbname='crawler' user='postgres' host='localhost' password='1234'"

class DataBase_Project_DB :
    def __init__(self,
        crawlerName = "",
        projectName="",
        projectUrl="",
        summary="",
        homepageUrl="",
        createdOn="",
        developer=[],
        category="",
        programmingLanguage=[],
        License=""):
        self.crawlerName = crawlerName
        self.projectName=projectName
        self.projectUrl=projectUrl
        self.projectUrlHash=md5hasher.hashing(projectUrl)
        self.summary=summary
        self.homepageUrl=homepageUrl
        self.createdOn=createdOn
        self.developer=developer
        self.category=category
        self.programmingLanguage=programmingLanguage
        self.License=License
        return

    def project_db_insert(self):
        try:
            if self.createdOn != "":
                self.createdOn = self.createdOn.strftime("%Y-%m-%d")
            conn = psycopg2.connect(db_string)
            cur = conn.cursor()

            value = self.crawlerName,self.projectName,self.projectUrl,self.summary,self.homepageUrl,self.createdOn,self.developer,self.category,self.License,self.programmingLanguage
            query = "INSERT INTO PROJECT_DB(crawler_name, project_name, project_url, summary, homepage_url, created_on, developer, category, license, programming_lang) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(query, ((value)))
            conn.commit()
            print("project_db   done")
        except :
            print("project_db   error")


class DataBase_Project_File_DB :
    def __init__(self,
        projectName="",
        file_dir= "",
        project_ver = "",
        hasing = ""):
        self.projectName = projectName
        self.file_dir = file_dir
        self.project_ver = project_ver
        self.hasing = hasing
        return

    def project_file_db_insert(self):
        try :
            #print(self.projectName)
            conn = psycopg2.connect(db_string)
            conn.autocommit = True
            cur = conn.cursor()
            value = self.projectName
            query = ("SELECT pid FROM PROJECT_DB WHERE project_name = '%s'" %value)
            cur.execute(query)
            pid = cur.fetchall()
            ppid = pid[0][0]
            value = int(ppid), self.file_dir, self.project_ver, self.hasing
            query = "INSERT INTO PROJECT_FILE_DB(pid,file_dir, project_ver, hashing) VALUES( %s, %s, %s, %s)"
            cur.execute(query, ((value)))
            conn.commit()
            print("project_file_db_insert done")
        except:
            print("project_file_db_insert error")

class DataBase_Crawler_DB :
    def __init__(self,
        crawlerName = "",
        crawlerStatus = ""): #0: stop 1:runnig
        self.CrawlerName = crawlerName
        self.CrawlerStatus = crawlerStatus
        return

    def crawler_db_insert(self):
        now = datetime.now()
        time = now.strftime("%Y-%m-%d %H:%M:%S")
        print(time)
        try :
            conn = psycopg2.connect(db_string)
            conn.autocommit = True
            cur = conn.cursor()
            value = self.CrawlerName, self.CrawlerStatus, time
            query = "INSERT INTO CRAWLER_DB(crawler_name, crawler_status, update_time) VALUES(%s,%s,%s)"
            cur.execute(query, (value))
            conn.commit()
            print("crawler_db_insert done")

        except:
            conn = psycopg2.connect(db_string)
            conn.autocommit = True
            cur = conn.cursor()
            value = self.CrawlerStatus, time, self.CrawlerName,
            query = "UPDATE CRAWLER_DB SET crawler_status = %s, update_time = %s where crawler_name = %s"
            cur.execute(query, (value))
            conn.commit()
            print("crawler_db_insert error")




