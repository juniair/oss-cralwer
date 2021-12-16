# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import psycopg2


from utils import FileHelper, common, logger as loggerFactory
from db.base_db import IndexDB, BaseDB



class IndexRepository:

  def __init__(self, db: BaseDB=None, logger: loggerFactory=None):
    self.__db = db if db is not None else IndexDB()     
    self.__logger = logger if logger is not None else loggerFactory.getLogger(filename="{}.log".format(self.__class__.__name__), log_file_path=common.BATCH_LOG_PATH)


  def get_last_index_file_id(self) -> int:

    self.__logger.info("Getting last index file id")

    query = """
    SELECT MAX(file_id) AS last_file_id
      FROM piu_index_file_tb
    """

    self.__db.execute(sql=query)
    result = self.__db.fetchone()
    return int(result.last_file_id)


  def get_files_from_index_file_table(self, page):
    size = 10000
    start = (page - 1) * size
    sql = """
      SELECT * 
        FROM piu_index_file_tb 
       WHERE file_id > %s
    ORDER BY file_id
       LIMIT %s""" % (start, size)
    self.__logger.info(sql)
    self.__db.execute(sql)
    result = self.__db.fetchall()
    return result

  def get_file_infos(self, file_id):
    sql = "select * from piu_index_file_infos_tb where file_id = %s"
    self.__logger.debug("check file_infos... file_id={}".format(file_id))
    self.__db.execute(sql, (file_id,))
    return self.__db.fetchall()

  def upsert_license_data(self, file_id, project_name, project_license_id, project_url, project_ver, license_id):
    '''
    테스트 : piu_index_file_infos_test
    라이브 : piu_index_file_infos_tb
    '''
    sql = '''
    INSERT INTO piu_index_file_infos_tb
               (file_id
               ,project_name
               ,project_license_id
               ,project_url
               ,project_ver
               ,file_license_id
               ,create_dt
               ,update_dt)
        VALUES(%s
              ,%s
              ,%s
              ,%s
              ,%s
              ,%s
              ,now()
              ,now())
   ON CONFLICT (file_id)
   DO UPDATE SET
            (project_license_id, file_license_id, project_ver, update_dt) 
            = (EXCLUDED.project_license_id, EXCLUDED.file_license_id, EXCLUDED.project_ver, EXCLUDED.update_dt) ;
    '''
    project_license_id = str(project_license_id)
    file_license_id = str(license_id)
    # project_license_id == license_id => license_id는 blank
    file_license_id = file_license_id if project_license_id != file_license_id else ''
    # project_ver 값도 UnKnown인 경우 blank
    project_ver = project_ver if project_ver.lower() != 'unknown' else ''
    try:
        # project의 라이선스도 '88888'은 공백으로 처리
        self.__logger.debug(sql % (file_id, project_name, (project_license_id if project_license_id != '88888' else ''),
              project_url, project_ver, (file_license_id if file_license_id != '88888' else '')))
        self.__db.execute(sql, (file_id, project_name, (project_license_id if project_license_id != '88888' else ''),
                  project_url, project_ver, (file_license_id if file_license_id != '88888' else ''),))
    except (Exception, psycopg2.DatabaseError) as e:
        self.__logger.error(e)

  # def upsert_license_data(self, file_id, project_name, project_license_id, project_url, project_ver, license_id, db):
  #     '''
  #     테스트 : piu_index_file_infos_test
  #     라이브 : piu_index_file_infos_tb
  #     '''
  #     sql = '''INSERT INTO 
  #         piu_index_file_infos_tb(file_id, project_name, project_license_id, project_url, project_ver, file_license_id, create_dt, update_dt)
  #         VALUES(%s, %s, %s, %s, %s, %s, now(), now())
  #         ON CONFLICT (file_id)
  #         DO UPDATE SET
  #             (project_license_id, file_license_id, project_ver, update_dt) 
  #             = (EXCLUDED.project_license_id, EXCLUDED.file_license_id, EXCLUDED.project_ver, EXCLUDED.update_dt) ;
  #     '''
  #     project_license_id = str(project_license_id)
  #     file_license_id = str(license_id)
  #     # project_license_id == license_id => license_id는 blank
  #     file_license_id = file_license_id if project_license_id != file_license_id else ''
  #     # project_ver 값도 UnKnown인 경우 blank
  #     project_ver = project_ver if project_ver.lower() != 'unknown' else ''
  #     try:
  #         # project의 라이선스도 '88888'은 공백으로 처리
  #         self.__logger.debug(sql % (file_id, project_name, (project_license_id if project_license_id != '88888' else ''),
  #               project_url, project_ver, (file_license_id if file_license_id != '88888' else '')))
  #         self.__db.execute(sql, (file_id, project_name, (project_license_id if project_license_id != '88888' else ''),
  #                   project_url, project_ver, (file_license_id if file_license_id != '88888' else ''),))
  #     except (Exception, psycopg2.DatabaseError) as e:
  #         self.__logger.error(e)

