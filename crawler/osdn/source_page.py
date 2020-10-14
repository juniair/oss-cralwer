# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

from worker.osdn import app

from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
import VCSDownloader
from common import getenv, get_http_headers, get_tor_proxy

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/osdnDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_osdn.json"

@app.task(autoretry_for=(Exception, ))
def get_source_code(project_info, clone_url, pid, current_path):
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)
    result = get_clone_code(crawlingInfo, clone_url, pid, current_path)
    return result


def get_clone_code(crawlingInfo, clone_url, pid, current_path):
    initialPath = current_path
    sub_repository_count = len(clone_url)

    file_dir = download_path
    for url in clone_url:
        os.chdir(initialPath) # project directory

        vcsType = url["vcsType"]
        command = url["command"]
        sub_directory = ""
        if sub_repository_count > 1:
            # make directory of sub-repository
            temp = command
            if vcsType == "git": offset = -1
            elif vcsType == "svn": offset = -2
            elif vcsType == "hg": offset = -2
            else: 
                offset = -1
                temp = command.split(" ")[0]
            sub_directory = temp.split("/")[offset]
            try:
                os.chdir(sub_directory)
            except:
                os.mkdir(sub_directory)
                os.chdir(sub_directory)
    
        current_path = os.getcwd() # project or sub-project directory

        remote_repo_revision = []
        if vcsType == "git":
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
        else:
            remote_repo_revision.append("UnKnown")
            remote_repo_revision.append("UnKnown")

        # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
        if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
            log.error("Project has no revision : {}".format(crawlingInfo.projectName))
            return False

        revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
        for rev in revision_list:
            command = url["command"]

            os.chdir(current_path)
            log.warning(current_path)
            git_hash = rev[0]
            revision = rev[1].split("/")[-1]
            revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
            release_ver = "{}/{}".format(sub_directory, revision) if sub_directory != "" else revision
            rel_createdOn = ""

            if any([vcsType == "git", vcsType == "svn"]):
                command = "{} {}".format(command, revision)
            else:
                try:
                    os.chdir(revision)
                except:
                    os.mkdir(revision)
                    os.chdir(revision)

            log.warning("current_path={}".format(os.getcwd()))
            log.warning(command)
            try:
                downresult = VCSDownloader.download(command)
                if downresult >= 1:
                    log.warning("Download Complete!")
                    rel_createdOn = "1900-01-01"
                    if vcsType == "git":
                        rel_createdOn = GetRepoInfo.ResetHardGit(command, git_hash, revision)
                    elif vcsType == "svn":
                        # svn
                        svn_repo_url = command.split(" ")[2]
                        rel_createdOn = GetRepoInfo.getDateSvn(svn_repo_url)

                    fileInfo = [file_dir, release_ver, rel_createdOn]
                    log.warning(fileInfo)
                    crawlingInfo.project_file_db_insert(fileInfo)
                    log.info("downloaded {}, {}".format(crawlingInfo.projectName, release_ver))
            except Exception as e:
                log.error("fail to download {}, {}".format(crawlingInfo.projectName, release_ver))
                log.error(e)
                return False
    return True