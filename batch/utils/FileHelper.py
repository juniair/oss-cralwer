# -*- coding: utf-8 -*-
import os
import csv
import shutil
from utils.logger import log


def write_release_id(file_full_path, release_id=1):
    log.debug("write release_id({})\n".format(release_id))
    with open(file_full_path, "a") as f:
        f.write("%s\n" % release_id)


def read_last_release_id(file_full_path):
    last_line = None
    with open(file_full_path, "r") as f:
        for line in f.readlines():
            last_line = line
    return last_line

# - description : 디렉토리 생성 시도 함수
# - parameters
#   * dirPath : 디렉토리 경로
# - return
#   * True : 이미 디렉토리가 존재하거나, 디렉토리 생성에 성공
#   * False :  생성 도중 문제가 발생


def try_make_dir(dirPath=None):
    try:
        if not os.path.isdir(dirPath):
            log.warning(
                "[try_make_dir] '{0}' is not exist. create '{0}'.".format(
                    dirPath)
            )
            os.makedirs(dirPath)
        return True
    except Exception as e:
        log.error("Error creating %s " % e.__repr__())
        return False


def make_file_path(unit_id):
    str_unit_id = str(unit_id)
    len_unit_id = len(str_unit_id)
    if len_unit_id - 3 <= 0:
        return "%04d" % int(unit_id)
    front_path = str_unit_id[-3:]
    back_path = make_file_path(str_unit_id[:len_unit_id-3])
    return "{}/{}".format(front_path, back_path)

# - description : 파일 생성 시도 함수
# - parameters
#   * filePath : 파일 경로
#   * fileName : 파일명(기본값 : check_list.txt)
# - return
#   * True : 이미 파일이 존재하거나, 파일 생성에 성공
#   * False :  생성 도중 문제가 발생
def try_make_file(filePath=".", fileName="check_list.txt", release_id=1):
    try:
        file_full_path = filePath + os.sep + fileName
        log.debug("[try_make_file] - {0} checking.".format(file_full_path))
        if not os.path.isfile(file_full_path):
            log.warning(
                "[try_make_file] '{0}' is not exist. create '{0}'.".format(
                    file_full_path,
                )
            )
            write_release_id(file_full_path, release_id)
        return True
    except Exception as e:
        log.error("[try_make_file] - {0}".format(e))
        if not os.path.isfile(file_full_path):
            os.remove(file_full_path)
        return False


def is_file(dir_path, file_path):
    '''
    /etc/clare/codebase 아래에 소스 코드 위치
    '''
    filename = "{}/{}".format(dir_path, file_path)
    log.info("is_file: {}".format(filename))
    return os.path.isfile(filename)

"""
csv 파일에서 작업이 된  파일 제거
"""
def remove_added_project(csv_file):
    added_project_info = {}

    with open(csv_file, 'r') as f:
        reader = csv.reader(f)

        for _, file_dir in reader:  # <- "for release_id, file_dir in reader"

            # added_project_info[release_id] = file_dir
            if not os.path.isdir(file_dir):
                log.info("[%s] is not found. because it is removed." %
                         file_dir)
                continue
            else:
                shutil.rmtree(file_dir)
                log.info("[%s] remove." % file_dir)
    # os.remove(csv_file)
