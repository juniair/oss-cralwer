import platform
import re
import os
import requests
import json
import sys
import signal
import shutil
import time
import logging
import subprocess
from signal import *

from worker.bitbucket import app

import md5hasher
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from logger import getLogger, write_progress_log
from common import get_http_headers, get_tor_proxy, getenv
import VCSDownloader
from GetRepoInfo import GetRepoInfo

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/bitbucketDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_bitbucket.json"


@app.task(autoretry_for=(Exception,))
def get_source_code(project_info, scm, clone_url, tags_url,  pid, current_path):
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)

    result = clone_source_code(crawlingInfo, scm, clone_url, tags_url, pid, current_path)
    return result


def get_tag_info(tags_url):
    # mercurial 의 릴리즈버전 구분을 위하여 tags url 내용을 가져온다.
    # tagList엔 tip(head와 비슷)이 무조건 1개 들어가 있어서 len은 1이상이며
    # release 버전이 있다면 2이상이다.
    tagInfo = None
    try:
        tag_response = requests.get(tags_url)
        tagText = tag_response.text
        tagList = json.loads(tagText)
        tagInfo = []
        for item2 in tagList['values']:
            # if item2['name'] == "tip":
            #     continue
            tagInfo.append(item2['name'])
            tagInfo.append(item2['target']['date'].replace('T', ' ').split(' ')[0])
    except Exception as e:
        log.error(e)
        log.error("{0} is Tags Error".format(projectName))
    return tagInfo
        
def clone_source_code(crawlingInfo, scm, clone_url, tags_url,  pid, current_path):
    
    command = scm + " clone " + clone_url + ' ' + crawlingInfo.projectName.replace(' ', '-')

    try:
        if  scm == "hg":
            tagInfo = get_tag_info(tags_url)
            remote_repo_revision = tagInfo if tagInfo else "0"
        else:
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
    except Exception as e:
        log.error(e)
        remote_repo_revision = "0"

    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
        log.warning("{} : No revision !!!!".format(crawlingInfo.projectName))
        return False

    file_dir = download_path

    # (git_hash, revision_name)형태 배열 재구성
    revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
    for rev in revision_list:
        os.chdir(current_path)
        
        rel_createdOn = ''
        git_hash = ''
        if scm == "hg":
            release_ver = rev[0]
            revision =  release_ver.split('/')[-1]
            rel_createdOn = rev[1] if rev[1] is not '' else ''
        else:
            git_hash = rev[0]
            release_ver = rev[1]
            revision = release_ver.split('/')[-1] # refs/tag or refs/head 를 제외한 이름

        # 디렉토리명으로 사용할거라서 특수문자 제거
        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)

        # 소스코드를 리비젼 디렉토리에 저장
        command = scm + " clone " + clone_url + ' ' + revision
        log.debug(command)
        # 이미 해당 리비젼을 받았으면 pass
        if crawlingInfo.project_file_db_exists(revision) is not False:
            log.warning("{} has {} revision!!!".format(crawlingInfo.projectName, revision))
            continue

        downresult = 0
        try:
            downresult = VCSDownloader.download(command)
        except Exception as e:
            log.error("download Error !!!!!")
            log.error(e)

        log.info("downloaded {} : {}".format(crawlingInfo.projectName, revision))

        if downresult >= 1:
            if scm == "hg":
                # 릴리즈버전으로 update
                try:
                    os.chdir(revision)
                    p = subprocess.Popen(['hg', 'update', '-r', release_ver],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                    (result, error) = p.communicate()
                    resultLog = result.decode('utf-8').strip()
                    log.debug("hg update Complete! : {}:{}".format())
                    log.debug(resultLog)
                except Exception as e:
                    log.error(e)
                    log.error("hg update Error")
            elif scm == "git":
                # 릴리즈버전으로 reset 후 최근날짜가져오기
                rel_createdOn = GetRepoInfo.ResetHardGit(command, git_hash, revision)
            fileInfo = [file_dir, revision, rel_createdOn]
            log.debug(fileInfo)
            crawlingInfo.project_file_db_insert(fileInfo)

    return True
