# -*- coding: utf-8 -*-

import os
import re
import json
import logging

from worker.eclipse import app
from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
import VCSDownloader
from common import getenv, get_http_headers, get_tor_proxy

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/eclipseDir" # sourceforge 프로젝트 다운로드 경로


@app.task(autoretry_for=(Exception, ))
def get_source_code(project_info, repositories, pid, current_path):
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)

    result = get_clone_code(crawlingInfo, repositories, pid, current_path)
    return result


def get_clone_code(crawlingInfo, repositories, pid, current_path):
    # OS에 맞는 경로 설정
    file_dir = download_path

    for repository_title, clone_url in repositories.items():
        os.chdir(current_path)

        title = repository_title.split(' - ')[0].split('/')[0]
        try:
            os.chdir(title)
        except:
            os.mkdir(title)
            os.chdir(title)
        repository_path = os.getcwd()
        
        command = "git clone {} master".format(clone_url)
        log.debug(command)

        try:
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
        except Exception as e:
            log.error(e)
            remote_repo_revision = "0"

        # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
        if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
            log.error("Project has no revision. : {}, {}".format(crawlingInfo.projectName, clone_url))
            continue
        
        revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
        for rev in revision_list:
            os.chdir(repository_path)

            git_hash = rev[0]
            revision = rev[1].split("/")[-1]

            # 특수문자 replace
            revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
            rel_createdOn = ""
            
            # db에 저장 되는 릴리즈 이름
            release_ver = "{}/{}".format(title, revision)
            if crawlingInfo.project_file_db_exists(release_ver) is not False:
                log.warning("{} has {} revision!!!".format(crawlingInfo.projectName, release_ver))
                continue
            command = "git clone {} {}".format(clone_url, revision)
            downresult = 0
            try:
                downresult = VCSDownloader.download(command)
            except Exception as e:
                log.error("Download Error! {}, {}".format(crawlingInfo.projectName, revision))
                log.error(e)

            if downresult >= 1:
                # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
                try:
                    rel_createdOn = GetRepoInfo.ResetHardGit(command,  git_hash, revision)
                    fileInfo = [file_dir, release_ver, rel_createdOn]
                    log.debug(fileInfo)
                    crawlingInfo.project_file_db_insert(fileInfo)
                    
                except Exception as e:
                    log.error(e)
                log.info("downloaded {}, {}".format(crawlingInfo.projectName, revision))
    return True
    