# -*- coding: utf-8 -*-

"""
크롤링 데이터를 clare에서 add와 index 작업을 위한 클래스 정의
"""
import os
import sys
import traceback
import subprocess
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from common import getenv
from base_db import CrawlerDB
from logger import getLogger

load_dotenv()


def write_release_id(file_full_path, release_id=1):
    print("write release_id({})\n".format(release_id))
    with open(file_full_path, "a") as f:
        f.write("%s\n" % release_id)


def read_last_release_id(file_full_path):
    last_line = None
    with open(file_full_path, "r") as f:
        for line in f.readlines():
            last_line = line
    return last_line


def try_make_dir(dirPath=None):
    try:
        if not os.path.isdir(dirPath):
            log.warning(
                "[try_make_dir] '{0}' is not exist. create '{0}'.".format(dirPath)
            )
            os.makedirs(dirPath)
        return True
    except Exception as e:
        log.error(str(e))
        return False


# - description : 파일 생성 시도 함수
# - parameters
#   * filePath : 파일 경로
#   * fileName : 파일명(기본값 : check_list.txt)
# - return
#   * True : 이미 파일이 존재하거나, 파일 생성에 성공
#   * False :  생성 도중 문제가 발생
def try_make_file(filePath=".", fileName="check_list.txt"):
    try:
        file_full_path = filePath + os.sep + fileName
        log.debug("[try_make_file] - {0} checking.".format(file_full_path))
        if not os.path.isfile(file_full_path):
            log.warning(
                "[try_make_file] '{0}' is not exist. create '{0}'.".format(
                    file_full_path
                )
            )
            write_release_id(file_full_path)
        return True
    except Exception as e:
        log.error("[try_make_file] - {0}".format(e))
        if not os.path.isfile(file_full_path):
            os.remove(file_full_path)
        return False


BATCH_LOG_PATH = getenv(
    "BATCH_LOG_PATH", "/HDD2/alice_project/alice_crawler/batch/log/batch"
)

log = getLogger(filename="batch.log", log_file_path=BATCH_LOG_PATH)


class Clare:
    def __init__(self, debug=False):
        self.debug = debug

        self.CSV_DOWNLOAD_PATH = getenv(
            "DOWNLOAD_PATH", "/HDD2/alice_project/alice_crawler/batch/csv", self.debug
        )

        log.warning(
            "[init] csv diretory checking. path : {0}".format(self.CSV_DOWNLOAD_PATH)
        )
        try_make_dir(self.CSV_DOWNLOAD_PATH)

        self.HISTORY_PATH = getenv(
            "HISTORY_PATH",
            "/HDD2/alice_project/alice_crawler/batch/history",
            self.debug,
        )

        log.warning(
            "[init] history diretory checking. path : {0}".format(self.HISTORY_PATH)
        )
        try_make_dir(self.HISTORY_PATH)

        self.HISTORY_FILE_NAME = getenv(
            "HISTORY_FILE_NAME", "check_list.txt", self.debug
        )

        log.warning(
            "[init] history file checking. path : {0}".format(
                self.HISTORY_PATH + os.sep + self.HISTORY_FILE_NAME
            )
        )
        try_make_file(filePath=self.HISTORY_PATH, fileName=self.HISTORY_FILE_NAME)

    def run(self, release_id_range=[None, None]):

        # Step 1. CSV 추출을 위한 DB 접근 시도
        try:
            crawler_db = CrawlerDB()  # (port=15432, password='12345678')
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            raise e

        start_release_id = release_id_range[0]

        # Step 2. 파일에 기록한 마지막 release_id 값을 불러옴

        file_full_path = self.HISTORY_PATH + os.sep + self.HISTORY_FILE_NAME
        if start_release_id is None:
            log.debug("file path : {0}".format(file_full_path))
            start_release_id = int(read_last_release_id(file_full_path))
            release_id_range[0] = start_release_id

        # Step 3. DB에서 마지막 release_id 값 불러옴

        last_release_id = release_id_range[1]
        # 인자 값이 없으면 DB에서 조회
        if last_release_id is None:
            # - 조건을 넣으면 쿼리 속도가 빨라지나?
            query = """
            SELECT MAX(release_id) as p
              FROM dpa_crawler_release_tb
             WHERE %s < release_id
            """
            query = query % start_release_id
            log.debug(query)
            crawler_db.execute(query)
            result = crawler_db.fetchall()
            ppid = result[0].p

            last_release_id = int(ppid)

            release_id_range[1] = last_release_id

        # dpa_release_tb 테이블의 마지막 release_id 값이 작으면 작업 내역이 없으므로 리턴 처리
        if last_release_id <= start_release_id:
            log.debug("restart csv")
            start_release_id = 1

        log.info(
            "indexing release_id {0} ~ {1}".format(start_release_id, last_release_id)
        )

        export_utc_now = datetime.utcnow()
        time_gap = timedelta(hours=9)
        export_utc_now = export_utc_now + time_gap

        try:
            while start_release_id < last_release_id:
                # 시작할 release_id에서 100,000개 데이터 추출 데이터가
                # last_release_id보다 큰 경우 처리하지 말 것
                if (start_release_id + 100000) < last_release_id:
                    end_release_id = start_release_id + 100000
                else:
                    end_release_id = last_release_id

                csv_file_path = self.export_csv_file(
                    crawler_db=crawler_db,
                    start_release_id=start_release_id,
                    end_release_id=end_release_id,
                    export_timestamp=export_utc_now.timestamp(),
                )

                csv_file_size = os.stat(csv_file_path).st_size

                if 0 < csv_file_size:
                    self.clare_add_processing(csv_file_path)

                # 다음 release_id를 시작점으로 변경
                start_release_id = end_release_id + 1
                time.sleep(60)
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            is_complete = False

            # 예외 발생시 다음 시작 순서를 체크 하기 위
            last_release_id = start_release_id
            log.info(
                "[clare - run] running stop. restart release_id({0}) changed. ".format(
                    start_release_id
                )
            )

        if is_complete:
            is_complete = self.index()

        if is_complete:
            # Step 6. Clare add 작업이 끝나면 다음 시작할 release_id 기록
            write_release_id(file_full_path, last_release_id)

        crawler_db.close()
        return is_complete

    def index(self):
        is_complete = True
        try:

            self.clare_index_processing()
        except Exception as e:
            log.error(e)
            traceback.print_exc()
            is_complete = False
        return is_complete

    def clare_add_processing(self, file_full_path):

        p = None

        log_path = getenv(
            "CLARE_LOG_PATH",
            "/HDD2/alice_project/alice_crawler/batch/log/clare",
            is_debug=self.debug,
        )

        try_make_dir(log_path)

        log_file_name = getenv(
            "CLARE_ADD_LOG_NAME", "clare_add.log", is_debug=self.debug
        )

        log_file_path = log_path + os.sep + log_file_name
        with open(log_file_path, "a") as f:
            clare_jar = getenv(
                "CLARE_FILE_NAME", "/HDD2/alice_project/alice_crawler/Clare-1.0.jar"
            )
            code_base_path = getenv(
                "CLEAR_CODE_BASE_DIR", "/HDD2/alice_project/codebase"
            )

            args = [
                "java",
                "-jar",
                clare_jar,
                "add",
                "-csv",
                file_full_path,
                "-initdb",
                "-codebase",
                code_base_path,
            ]
            log.info(
                "[clare command] {0}".format(" ".join([str(elem) for elem in args]))
            )
            p = subprocess.Popen(args, stdout=f, stderr=f).communicate()

        return p

    def clare_index_processing(self):

        p = None

        log_path = getenv(
            "CLARE_LOG_PATH",
            "/HDD2/alice_project/alice_crawler/batch/log/clare",
            is_debug=self.debug,
        )

        try_make_dir(log_path)

        log_file_name = getenv(
            "CLARE_INDEX_LOG_NAME", "clare_index.log", is_debug=self.debug
        )
        log_file_path = log_path + os.sep + log_file_name
        with open(log_file_path, "a") as f:
            clare_jar = getenv(
                "CLARE_FILE_NAME", "/HDD2/alice_project/alice_crawler/Clare-1.0.jar"
            )
            code_base_path = getenv(
                "CLEAR_CODE_BASE_DIR", "/HDD2/alice_project/codebse"
            )

            args = [
                "java",
                "-jar",
                clare_jar,
                "index",
                "-initdb",
                "-codebase",
                code_base_path,
            ]

            log.info(
                "[clare command] {0}".format(" ".join([str(elem) for elem in args]))
            )

            p = subprocess.Popen(args, stdout=f, stderr=f).communicate()

        return p

    def export_csv_file(
        self, crawler_db, start_release_id, end_release_id, export_timestamp
    ):

        query = """
        COPY (  SELECT release_id
                    ,file_dir
                FROM dpa_crawler_release_tb
                WHERE %s <= release_id
                AND release_id < %s
            ORDER BY release_id ASC)
          TO STDOUT
        WITH CSV
             DELIMITER ','
             FORCE QUOTE *
        """

        value = start_release_id, end_release_id

        query = query % value

        log.info(
            """
        [export csv file query] - 
        %s
        """
            % query
        )

        csv_file_name = "dpa_release_tb_data_{0}_to_{1}-{2}(UTC+9).csv".format(
            start_release_id, end_release_id, export_timestamp
        )

        csv_file_path = self.CSV_DOWNLOAD_PATH + os.sep + csv_file_name

        with open(csv_file_path, "w") as csv:
            log.info("[clare.add] data export - {0}".format(csv_file_path))
            crawler_db.copy_expert(sql=query, file=csv)

        return csv_file_path


if __name__ == "__main__":

    release_id_range = (None, None)
    try:
        if 3 <= len(sys.argv):
            start_release_id = int(sys.argv[1])
            last_release_id = int(sys.argv[2])
            release_id_range = (start_release_id, last_release_id)
            clare = Clare()
            clare.run(release_id_range)
        else:
            error_msg = """
            Invalid release_id arguments.
            Usage: python main.py <start_release_id> <last_release_id>
            """
            raise ValueError()
    except Exception as e:
        print(e)
        traceback.print_exc()
