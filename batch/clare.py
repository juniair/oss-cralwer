# -*- coding: utf-8 -*-

"""
크롤링 데이터를 clare에서 add와 index 작업을 위한 클래스 정의
"""
import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import traceback
import subprocess
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta, tzinfo


# custom modules
from db.base_db import CrawlerDB
from utils import FileHelper, common, logger as loggerFactory
from utils.logger import getLogger
from repository.IndexRepository import *
from repository.CrawlerRepository import *


log = loggerFactory.getLogger(filename="batch.log", log_file_path=common.BATCH_LOG_PATH)
FileHelper.try_make_dir(common.BATCH_LOG_PATH)



class Clare:

    #{ CONSTRATOR
    def __init__(self, debug=False):
        self.__logger = log
        self.__indexRepository = IndexRepository(logger=log)
        self.__crawlerRepository = CrawlerRepository(logger=log)
        self.__debug = debug

        self.CSV_DOWNLOAD_PATH = common.getenv(
            "DOWNLOAD_PATH", "/HDD2/alice_project/alice_crawler/batch/csv", self.__debug
        )

        self.__logger.warning(
            "[init] csv diretory checking. path : {0}".format(
                self.CSV_DOWNLOAD_PATH)
        )
        FileHelper.try_make_dir(self.CSV_DOWNLOAD_PATH)

        self.HISTORY_PATH = common.getenv(
            "HISTORY_PATH",
            "/HDD2/alice_project/alice_crawler/batch/history",
            self.__debug,
        )

        # 인덱싱 히스토리 파일 보관 디렉토리 생성 시도
        self.__logger.warning(
            "[init] history diretory checking. path : {0}".format(
                self.HISTORY_PATH)
        )
        FileHelper.try_make_dir(self.HISTORY_PATH)

        # 인덱싱 히스토리 파일 생성 시도
        self.__HISTORY_FILE_NAME = common.getenv(
            "HISTORY_FILE_NAME", "check_list.txt", self.__debug
        )
        self.__history_file_path = self.HISTORY_PATH + os.sep + self.__HISTORY_FILE_NAME
        self.__logger.warning("[init] history file checking. path : {0}".format(self.__history_file_path))
        FileHelper.try_make_file(filePath=self.HISTORY_PATH, fileName=self.__HISTORY_FILE_NAME)
        
        self.__clare_log_path = common.getenv("CLARE_LOG_PATH","/HDD2/alice_project/alice_crawler/batch/log/clare",is_debug=self.__debug,)
        self.__logger.debug("try make clare_log_path")
        FileHelper.try_make_dir(self.__clare_log_path)

        # clare 작업시 발생하는 로그 파일명 설정
        # 일자별로 처리를 위해 확장자가 있으면 제거 하도록 변경
        self.__clare_add_log_name = common.getenv("CLARE_ADD_LOG_NAME", "clare_add", is_debug=self.__debug)
        if self.__clare_add_log_name.endswith(('.txt', '.log', 'text')):
            fname, ext = os.path.splitext(self.__clare_add_log_name)
            self.__clare_add_log_name = fname

        self.__clare_index_log_name = common.getenv("CLARE_INDEX_LOG_NAME", "clare_index", is_debug=self.__debug)
        if self.__clare_index_log_name.endswith(('.txt', '.log', 'text')):
            fname, ext = os.path.splitext(self.__clare_index_log_name)
            self.__clare_index_log_name = fname
    #} END CONSTRATOR

    #{ PROPERTY
    @property
    def __clare_log_file_date(self):
        return datetime.now().strftime("%Y-%m-%d")
    #} END PROPERTY


    #{ METHODS
    def run(self, release_id_range=[None, None], is_csv_mode=False):
        
       
        start_release_id = release_id_range[0]

        # Step 1. 파일에 기록한 마지막 release_id 값을 불러옴
        if start_release_id is None:
            self.__logger.debug("file path : {0}".format(self.__history_file_path))
            start_release_id = int(FileHelper.read_last_release_id(self.__history_file_path))


        # Step 3. DB에서 마지막 release_id 값 불러옴

        last_release_id = release_id_range[1]
        # 인자 값이 없으면 DB에서 조회
        if last_release_id is None:
            
            ppid = self.__crawlerRepository.get_max_release_id(start_release_id)
            if ppid is None:
                log.info("Do not new crawlering project.")
                return False
            else:
                last_release_id = int(ppid)

        # dpa_release_tb 테이블의 마지막 release_id 값이 작으면 작업 내역이 없으므로 리턴 처리
        if last_release_id <= start_release_id:
            log.info("indexing data not found.")
            return False

        log.info(
            "indexing release_id {0} ~ {1}".format(
                start_release_id, last_release_id)
        )
        try:        
            if not is_csv_mode:
                self.__logger.info("running clare add.")
                checkpoint_id = self.__clare_add_for_release_id(start_release_id, last_release_id)
                log.debug("write release_id({})\n".format(checkpoint_id))
                FileHelper.write_release_id(checkpoint_id)
                self.__logger.info("running clare index.")
                self.__clare_index_processing()
            else:
                # TODO: 기존 내역을 여기에 반영
                pass
            return True
        except Exception as e:
            self.__logger.error(e)
            return False

        

    def index(self):
        is_complete = True
        try:

            self.__clare_index_processing()
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            is_complete = False
        return is_complete

    # release_id로 add 작업
    def __clare_add_for_release_id(self, start_release_id, last_release_id):
        
        for release_id in range(start_release_id, last_release_id):
            try:
                data = self.__crawlerRepository.get_release_info(release_id=release_id)

                log_file_path = self.__clare_log_path + os.sep + self.__clare_add_log_name + "_{}.log".format(self.__clare_log_file_date)
                if data is None or FileHelper.has_dir(data.file_dir):
                    log.info("{} is not found.".format(release_id))
                    continue

                args = [
                    "java",
                    "-jar",
                    common.CLARE_JAR,
                    "add",
                    "-release_id",
                    release_id,
                    "-initdb",
                    "-codebase",
                    common.CODE_BASE_PATH,
                    "-v"
                ]
                (result, err) = self.__execute_engine(args, log_file_path)
                if (err is None):
                    FileHelper.remove_added_project(data.file_dir)
                else:
                    raise Exception("clare add(release_id: {}) failed.".format(str(release_id)))
            except Exception as e:
                log.error(e)
                return release_id

        return last_release_id            
        


    def clare_add_for_csv(self, start_release_id, last_release_id, file_full_path):

        export_utc_now = datetime.utcnow()
        time_gap = timedelta(hours=9)
        export_utc_now = export_utc_now + time_gap

        is_added = False
        is_complete = False

        try:
            while start_release_id < last_release_id:
                is_added = False
                # 시작할 release_id에서 100,000개 데이터 추출 데이터가
                # last_release_id보다 큰 경우 처리하지 말 것
                if (start_release_id + 100000) < last_release_id:
                    end_release_id = start_release_id + 100000
                else:
                    end_release_id = last_release_id

                csv_file_path = self.__export_csv_file(
                    crawler_db=crawler_db,
                    start_release_id=start_release_id,
                    end_release_id=end_release_id,
                    export_timestamp=export_utc_now.timestamp(),
                )

                if csv_file_path is not None:
                    args = [
                            "java",
                            "-jar",
                            common.CLARE_JAR,
                            "add",
                            "-csv",
                            file_full_path,
                            "-initdb",
                            "-codebase",
                            common.CODE_BASE_PATH,
                            ]
                    t = self.clare_add_for_csv(csv_file_path)
                    is_added = True

                if is_added:
                    # TODO: ADD 한 프로젝트 삭제
                    # CSV 파일 읽어서 삭제
                    FileHelper.remove_added_project_with_csv(csv_file=csv_file_path)
                    # 다음 release_id를 시작점으로 변경
                start_release_id = end_release_id
                time.sleep(60)
                is_complete = True
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            is_complete = False

            # 예외 발생시 다음 시작 순서를 체크 하기 위
            log.info(
                "[clare - run] running stop. restart release_id({0}) changed. ".format(
                    start_release_id
                )
            )

        if is_complete or is_added:
            is_complete = self.index()

        if is_complete:
            last_release_id = last_release_id + 1
            # Step 6. Clare add 작업이 끝나면 다음 시작할 release_id 기록
            FileHelper.write_release_id(file_full_path, last_release_id)

        return is_complete


    # clare.jar index 실행
    def __clare_index_processing(self):

        log_file_path = self.__clare_log_path + os.sep + self.__clare_index_log_name + "_{}.log".format(self.__clare_log_file_date)
        args = [
                "java",
                "-jar",
                common.CLARE_JAR,
                "index",
                "-initdb",
                "-codebase",
                common.CODE_BASE_PATH,
                "-v"
            ]

        self.__logger.info("[clare command] {0}".format(" ".join([str(elem) for elem in args])))
        try:
            (result, err) = self.__execute_engine(args, log_file_path)
        except Exception as e:
            log.error(e)

            
    
    # clare 엔진 실행 함수
    def __execute_engine(self, args, log_path):
        p = None
        err = None
        log.info("[clare command] {0}".format(" ".join([str(elem) for elem in args])))
        with open(log_path, "a") as f:
            (p, err) = subprocess.Popen(args, stdout=f, stderr=f).communicate()
        return (p, err)

    # csv 추출 함수
    def __export_csv_file(
        self, crawler_db, start_release_id, end_release_id, export_timestamp
    ):
        log.info(
            "[export_csv_file] - {0} ~ {1}".format(
                start_release_id, (end_release_id-1))
        )

        value = start_release_id, end_release_id

        query = """
            SELECT COUNT(release_id) AS c
              FROM dpa_crawler_release_tb
             WHERE %s <= release_id
                   AND release_id <= %s
                   AND file_dir IS NOT NULL
            """
        query = query % value

        log.warning("Check if extraction is possible")
        crawler_db.execute(query)
        result = crawler_db.fetchall()
        row_count = result[0].c

        csv_file_path = None
        if 0 < row_count:

            log.info("csv can be extracted.")

            query = """
            COPY (  SELECT release_id
                        ,file_dir
                    FROM dpa_crawler_release_tb
                    WHERE %s <= release_id
                    AND release_id < %s
                    AND file_dir IS NOT NULL
                ORDER BY release_id ASC)
            TO STDOUT
            WITH CSV
                DELIMITER ','
                FORCE QUOTE *
                ENCODING 'UTF-8'
            """

            query = query % value

            log.info(
                """
            [export csv file query] - 
            %s
            """
                % query
            )

            csv_file_name = "dpa_release_tb_data_{0}_to_{1}-{2}(UTC+9).csv".format(
                start_release_id, (end_release_id), export_timestamp
            )

            csv_file_path = self.CSV_DOWNLOAD_PATH + os.sep + csv_file_name

            with open(csv_file_path, "w", encoding="utf-8") as csv:
                log.info(
                    "[clare.export_csv_file] data export - {0} excute.".format(csv_file_path))
                crawler_db.copy_expert(sql=query, file=csv)
                log.info(
                    "[clare.export_csv_file] data export - {0} excuted.".format(csv_file_path))
        else:
            log.info("Unable to extract csv.")

        return csv_file_path
    #} END METHODS


if __name__ == "__main__":

    release_id_range = (None, None)
    try:
        clare = Clare()
        if 3 <= len(sys.argv):
            start_release_id = int(sys.argv[1])
            last_release_id = int(sys.argv[2])
            release_id_range = (start_release_id, last_release_id)
            clare.run(release_id_range)
        else:
            clare.run()
            error_msg = """
            Invalid release_id arguments.
            Usage: python main.py <start_release_id> <last_release_id>
            """
            raise ValueError(error_msg)
    except Exception as e:
        print(e)
        traceback.print_exc()
