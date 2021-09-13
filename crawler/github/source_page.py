#-*- coding: utf-8 -*-

import os
import re
import io
import sys
import json
import platform
import tarfile
import zipfile
import requests
import shutil
import logging
from bs4 import BeautifulSoup

from worker.github import app

from logger import getLogger
from crawler import CrawlingInfo
import VCSDownloader
from GetRepoInfo import GetRepoInfo
from common import getenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir" # sourceforge 프로젝트 다운로드 경로

log = logging.getLogger(__name__) # getLogger(filename="github_crawler.log")

@app.task(autoretry_for=(Exception,))
def get_source_code(projectInfo, clone_url, git_id,  pid, current_path, progress_status):
    log.debug(projectInfo)
    projectInfo.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    projectInfo.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**projectInfo)

    result = git_clone(crawlingInfo, clone_url, git_id, pid, current_path, progress_status) # item, remote_repo_revision
    return result

def git_clone(crawlingInfo, clone_url, git_id, pid, current_path, current_status):  # item, remote_repo_revision,
    # print("Clone URL : " + item['clone_url'])
    command = "git clone {0} {1}".format(clone_url, crawlingInfo.projectName + '_' + str(git_id))
    
    log.debug("get release list from repository :"+clone_url)
    try:
        log.debug(command)
        remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
    except Exception as e:
        log.error(e)
        remote_repo_revision = "0"
    log.debug(remote_repo_revision)
    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
        log.warning(crawlingInfo.projectName+" has no revision information")
        return False

    # 서버상 물리적 위치 
    file_dir = download_path

    # (git_hash, revision_name)형태 배열 재구성
    revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
    for rev in revision_list:
        os.chdir(current_path) # move project directory

        git_hash = rev[0]
        release_ver = rev[1]
        revision = release_ver.split('/')[-1] # refs/tag or refs/head 를 제외한 이름
        rel_createdOn = ""
        if revision == '': revision = 'UnKnown'
        log.debug("change revision directory :"+revision)
        
        # 리비젼 데이터를 다운로드 했는지 체크하여 다운로드 했다면 pass
        if crawlingInfo.project_file_db_exists(revision) is not False:
            log.info('{0}:{1} is downloaded. '.format(crawlingInfo.projectName, revision))
            continue
        # revision 디렉토리에 소스코드가 cloning되도록 command를 수정
        # revision 디렉토리 생성하는 코드는 주석처리 -> 정상 동작 확인 후 삭제 예정
        command = "git clone {0} {1}".format(clone_url, revision)
        # try:
        #     os.chdir(revision)
        # except:
        #     os.makedirs(revision)
        #     os.chdir(revision)
        
        downresult = 0
        try:
            log.warning('[crawler_github] found {0}:{1} project. trying to cloning/pull...'.format(crawlingInfo.projectName, revision))
            downresult = VCSDownloader.download(command)
            log.warning('[crawler_github] complete download {0}:{1}'.format(crawlingInfo.projectName.replace(' ', '-'), revision))
        except Exception as e:
            log.error(str(e))
        if downresult >= 1:
            # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
            try:
                rel_createdOn = GetRepoInfo.ResetHardGit(command, git_hash, release_ver)
                fileInfo = [file_dir, revision, rel_createdOn]
                log.debug(fileInfo)
                # DB 부분은 테스트로 제외
                crawlingInfo.project_file_db_insert(fileInfo)
            except Exception as e:
                log.error(str(e))
 
    return (downresult >= 1)
    