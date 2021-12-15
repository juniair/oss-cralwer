# -*- coding: utf-8 -*-
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
from db.base_db import CrawlerDB, IndexDB

manager = multiprocessing.Manager()
evt = manager.Event()

PROCESS_POOL = False




class LicenseController():

  def __init__(self):
    self.__crawlerDB = CrawlerDB()
    self.__indexDB = IndexDB()
    self.__logger = logger.getLogger(filename="{}.log".format(self.__class__.__name__), log_file_path=common.BATCH_LOG_PATH)
    
    history_path = common.getenv("HISTORY_PATH", "/HDD2/alice_project/alice_crawler/batch/history")

    FileHelper.try_make_dir(dirPath=history_path)

    history_file_name = common.getenv("HISTORY_INDEX_FILE_NAME", "update_index_file.txt")
    self.__history_full_path = ("%s/%s" %  (history_path, history_file_name))
    FileHelper.try_make_file(filePath=history_path, fileName=history_file_name, release_id=1055154469)

    for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
      signal(sig, self.__handler)

  def __handler(self, signum, frame):
    evt.set()
    self.__logger.debug("stop by interrupt signum={}".format(signum))
    if PROCESS_POOL:
        self.__logger.debug("terminating sub processes....")
        PROCESS_POOL.close()
        PROCESS_POOL.terminate()
        PROCESS_POOL.join()
        self.__logger.debug("terminated sub processes!")

    sys.exit(signum)




  def updated_file_license(self, start_file_id: int = None, end_file_id: int = None):
    start_index_file_id = start_file_id if start_file_id is not None else int(FileHelper.read_last_release_id(self.__history_full_path))

    end_index_file_id = end_file_id if end_file_id is not None else self.__get_last_index_file_id()
    
    if end_index_file_id <= start_index_file_id:
      self.__logger.info("It is all updated_file_license.")
      return
    """
        size = 10000
        start = (page - 1) * size
        sql = "select * from piu_index_file_tb order by file_id desc limit {} offset {}".format(
        size, start)
        """
    total_size = end_index_file_id - start_index_file_id
    total_page = (total_size // 10000) + 1 if 0 < (total_size % 10000) else (total_size // 10000)
    pool_count = int((total_page // 1100) + 1)
    procesee_args = []
    for i in range(pool_count):
      page = (start_index_file_id // 10000) + (i * 1100)
      procesee_args.append((page, evt))
      

    print(procesee_args)

    print("Total size: %d, page: %d" % (total_size, total_page))
    
  
  def __get_last_index_file_id(self) -> int:
    query = """
    SELECT MAX(file_id) AS last_file_id
      FROM piu_index_file_tb
    """

    self.__indexDB.execute(sql=query)
    result = self.__indexDB.fetchone()
    print(result.last_file_id)
    return int(result.last_file_id)




  def __del__(self):
    self.__crawlerDB.close()
    self.__indexDB.close()



if __name__ == "__main__":
  controller = LicenseController()

  controller.updated_file_license(end_file_id=1065852560)