#-*- coding: utf-8 -*-

import psycopg2
import psycopg2.extras
from common import getenv

class BaseDB(object):
    DATABASE_INFO = "host='127.0.0.1' user='postgres' port='{}'"
    def __init__(self, port=5432, password=None, database_info=None):
        self.conn = None
        self.cursor = None
        if database_info is None:
            database_info = self.DATABASE_INFO
        if port is None: port = 5432
        database_info = database_info.format(port)
        if password:
          database_info = "{} password='{}'".format(database_info, password)
        self.database_info = database_info
        self.connect()
    
    def __del__(self):
        self.close()

    def connect(self):
        if self.conn is None: self.conn = psycopg2.connect(self.database_info)
        self.conn.set_session(autocommit=True)
        if self.cursor is None: self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        return 
    
    def execute(self, sql, *args, **kwargs):
        if self.cursor is None: self.connect()
        self.cursor.execute(sql, *args, **kwargs)

    def fetchall(self):
        return self.cursor.fetchall()
    
    def fetchone(self):
        return self.cursor.fetchone()

    def close(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()


class ProjectDB(BaseDB):
    PROJECT_DATABASE = "host='127.0.0.1' dbname='project' user='postgres' port='{}'"

    def __init__(self, port=5432, password=None):
        self.PROJECT_DATABASE = getenv("PROJECT_DATABASE", self.PROJECT_DATABASE.format(port), True)
        super(ProjectDB, self).__init__(port=port, password=password, database_info=self.PROJECT_DATABASE)
    
class IndexDB(BaseDB):
    INDEX_DATABASE = "host='127.0.0.1' dbname='index' user='postgres' port='{}'"

    def __init__(self, port=5432, password=None):
        self.INDEX_DATABASE = getenv("INDEX_DATABASE", self.INDEX_DATABASE.format(port), True)
        super(IndexDB, self).__init__(port=port, password=password, database_info=self.INDEX_DATABASE)

class CrawlerDB(BaseDB):
    CRAWLER_DATABASE = "host='127.0.0.1' dbname='crawler' user='postgres' port='{}'"

    def __init__(self, port=5432, password=None):
        self.CRAWLER_DATABASE = getenv("CRAWLER_DATABASE", self.CRAWLER_DATABASE.format(port), True)
        super(CrawlerDB, self).__init__(port=port, password=password, database_info=self.CRAWLER_DATABASE)
    