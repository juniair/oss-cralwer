# -*- coding: utf-8 -*-

import os
import re
import json
import logging
import subprocess

from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from common import get_http_headers, get_tor_proxy, getenv
import VCSDownloader
from GetRepoInfo import GetRepoInfo
from worker.gitlab import app

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gitlabDir" # sourceforge 프로젝트 다운로드 경로

@app.task(autoretry_for=(Exception,))
def get_source_code(project_info, clone_url, tags, default_branch, pid, current_path):
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)
    result = clone_source_code(crawlingInfo, clone_url, tags, default_branch, pid, current_path)
    return result

def clone_source_code(crawlingInfo, clone_url, tags, default_branch, pid, current_path):
    
    command = "git clone {0} {1}".format(clone_url, crawlingInfo.projectName.replace(' ', '-'))
    try:
        remote_repo_revision = []
        for rel_item in tags:
            remote_repo_revision.append(rel_item["target"])
            remote_repo_revision.append(rel_item["name"])
        if len(remote_repo_revision) > 0:
            # tag list에 master branch를 추가
            remote_repo_revision = remote_repo_revision + GetRepoInfo.get_master_branch(command, default_branch)
        else:
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command, default_branch)
    except:
        remote_repo_revision = GetRepoInfo.getReleaseVersion(command, default_branch)

    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
        return False

    file_dir = download_path
    revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
    for rev in revision_list:
    # while downcnt < len(remote_repo_revision):
        log.debug("current_path="+current_path)
        os.chdir(current_path)

        git_hash = rev[0]
        revision = rev[1].split("/")[-1]

        # 특수문자 replace
        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
        rel_createdOn = ""

        command = "git clone {0} {1}".format(clone_url, revision)
        # 이미 해당 리비젼을 받았으면 pass
        if crawlingInfo.project_file_db_exists(revision) is not False:
            log.warning("{} has {} revision!!!".format(crawlingInfo.projectName, revision))
            continue
        # try:
        #     os.chdir(revision)
        # except:
        #     os.mkdir(revision)
        #     os.chdir(revision)

        downresult = 0
        try:
            downresult = VCSDownloader.download(command)
        except Exception as e:
            log.error("Download Error! "+command)
            log.error(e)

        if downresult >= 1:
            # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
            try:
                rel_createdOn = GetRepoInfo.ResetHardGit(command,  git_hash, revision)
                fileInfo = [file_dir, revision, rel_createdOn]
                log.debug(fileInfo)
                crawlingInfo.project_file_db_insert(fileInfo)
                log.info("downloaded {}, {}".format(crawlingInfo.projectName, revision))
            except Exception as e:
                log.error(e)

    return True
