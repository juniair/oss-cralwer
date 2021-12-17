# -*- coding: utf-8 -*-
import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import multiprocessing
import csv
from os import cpu_count
import json
import codecs
from signal import *

# import custom modules.
from utils import FileHelper, common, logger
from repository.IndexRepository import *
from repository.CrawlerRepository import *
from repository.LicenseRepository import *

from utils.license.oss_license import OpenSourceLicense

from utils.exception.Error import LicenseUpdateError

# manager = multiprocessing.Manager()
# evt = manager.Event()

# PROCESS_POOL = False
# # system event 처리


# def handler(signum, frame):
#     evt.set()
#     logger.debug("stop by interrupt signum={}".format(signum))
#     if PROCESS_POOL:
#         logger.debug("terminating sub processes....")
#         PROCESS_POOL.close()
#         PROCESS_POOL.terminate()
#         PROCESS_POOL.join()
#         logger.debug("terminated sub processes!")

#     sys.exit(signum)


# for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
#     signal(sig, handler)


FileHelper.try_make_dir(common.BATCH_LOG_PATH)


class LicenseController():

  def __init__(self):
    self.__logger = logger.getLogger(filename="{}.log".format(self.__class__.__name__), log_file_path=common.BATCH_LOG_PATH)
    self.__crawlerRepository = CrawlerRepository(logger=self.__logger)
    self.__indexRepository = IndexRepository(logger=self.__logger)
    self.__licenseRepository = LicenseRepository(logger=self.__logger)
    logger.log = self.__logger
    history_path = common.getenv("HISTORY_PATH", "/HDD2/alice_project/alice_crawler/batch/history")

    FileHelper.try_make_dir(dirPath=history_path)

    history_file_name = common.getenv("HISTORY_INDEX_FILE_NAME", "update_index_file.txt")
    self.__history_full_path = ("%s/%s" %  (history_path, history_file_name))
    FileHelper.try_make_file(filePath=history_path, fileName=history_file_name, release_id=1055154469)
    for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, self.handler)

  def handler(self, signum, frame):
      self.__logger.info("signum=", signum)
      sys.exit(0)


  def updated_file_license(self, start_file_id: int = None, end_file_id: int = None):
    start_index_file_id = start_file_id if start_file_id is not None else int(FileHelper.read_last_release_id(self.__history_full_path))

    end_index_file_id = end_file_id if end_file_id is not None else self.__indexRepository.get_last_index_file_id()
    
    if end_index_file_id <= start_index_file_id:
      self.__logger.info("It is all updated_file_license.")
      return

    total_size = end_index_file_id - start_index_file_id
    total_page = (total_size // 10000) + 1 if 0 < (total_size % 10000) else (total_size // 10000)
    pool_count = int((total_page // 1100) + 1)
    procesee_args = []

    next_page = 1
    try:
      self.__logger.info("license_updating...")
      for i in range(pool_count):
        page = (start_index_file_id // 10000) + (i * 1100)
        next_page = self.__update_file_license_process(page)
      
    except LicenseUpdateError as e:
      next_page = e.error_page

    next_index_file_id = start_index_file_id + (next_page * 10000)

    if (end_index_file_id <= next_index_file_id):
      self.__logger.warning("license update problems. Checkpoint restart index_file_id.")
      next_index_file_id = end_index_file_id
    else:
      self.__logger.info("license update complate. Checkpoint restart index_file_id.")

    

    

  def __update_file_license_process(self, page):

    start_page = page if page else 1
    limit_page = page + 1100
    while start_page <= limit_page:
      try:
        self.__logger.debug("get_files_from_index_file_table page=%d", start_page)

        rows = self.__indexRepository.get_files_from_index_file_table(start_page)
        if len(rows) == 0:
          break


      
        for row in rows:
          self.__logger.info("check file:file_id({}) unit_id({}) release_id({}) {}".format(
                  row.file_id, row.unit_id, row.release_id, row.file_path))

          file_infos = self.__indexRepository.get_file_infos(row.file_id)
          # if file_infos and len(file_infos) > 0: continue # 이미 라이선스 체크한 파일인 경우는 pass

          release_info = self.__crawlerRepository.get_release_info(row.release_id)

          if release_info is None: 
            self.__logger.info("release info: None")
            continue
          else:
            self.__logger.info("release info:release_id({}) pid({}) release_ver({}) {}".format(
                        release_info.release_id,
                        release_info.pid,
                        release_info.release_ver,
                        release_info.file_dir))

          # 대상 파일 소스의 존재 여부 체크
          file_path = FileHelper.make_file_path(row.unit_id)
          if FileHelper.is_file(common.CODE_BASE_PATH, file_path):
            project_info = self.__crawlerRepository.get_project_info(release_info.pid)
            self.__logger.info("project info:pid({}), {}, license({}), url({}), crawler({})".format(
                      project_info.pid,
                      project_info.project_name,
                      project_info.license,
                      project_info.project_url,
                      project_info.crawler_name))

            # 프로젝트의 라이선스 정보 조회
            project_license_id = self.__licenseRepository.get_license_id(project_info.license)

            # 파일의 라이선스 정보 체크
            file_license = self.__licenseRepository.find_file_license(file_path)
            file_license_id = self.__licenseRepository.get_license_id(file_license)
            self.__logger.info("license={} {}".format(file_license, file_license_id))
            self.__logger.debug("""%d > %s, %s, %s, %s, %s""" % (
              row.file_id,
              project_info.project_name,
              project_license_id,
              project_info.project_url,
              release_info.release_ver,
              file_license_id
            ))

            if file_infos is None or len(file_infos) == 0:
              self.__indexRepository.upsert_license_data(
                          row.file_id,
                          project_info.project_name,
                          project_license_id,
                          project_info.project_url,
                          release_info.release_ver,
                          file_license_id
                      )
            elif file_infos[0].file_license_id != file_license_id \
                  or (file_infos[0].file_license_id == '' and file_license_id == '88888'):
              self.__indexRepository.upsert_license_data(
                          row.file_id,
                          project_info.project_name,
                          project_license_id,
                          project_info.project_url,
                          release_info.release_ver,
                          file_license_id
                      )
          else:
            self.__logger.info("{}/{} is not found.".format(common.CODE_BASE_PATH, file_path))
        start_page += 1
      except Exception as e:
        self.__logger.error(e)
        raise LicenseUpdateError(e.__str__(), start_page)
          
        

      

    return start_page  



  def __del__(self):
    self.__indexRepository = None


if __name__ == "__main__":
  controller = LicenseController()

  controller.updated_file_license()