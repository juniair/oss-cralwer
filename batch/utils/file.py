# -*- coding: utf-8 -*-
import os


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
            print(
                "[try_make_dir] '{0}' is not exist. create '{0}'.".format(
                    dirPath)
            )
            os.makedirs(dirPath)
        return True
    except Exception as e:
        print("Error creating %s " % e.__repr__())
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
        print("[try_make_file] - {0} checking.".format(file_full_path))
        if not os.path.isfile(file_full_path):
            print(
                "[try_make_file] '{0}' is not exist. create '{0}'.".format(
                    file_full_path
                )
            )
            write_release_id(file_full_path)
        return True
    except Exception as e:
        print("[try_make_file] - {0}".format(e))
        if not os.path.isfile(file_full_path):
            os.remove(file_full_path)
        return False
