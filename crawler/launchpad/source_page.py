# -*- coding: utf-8 -*-

import os
import re
import json
import logging

from worker.launchpad import app
from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
import VCSDownloader
from common import getenv

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/launchpadDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_launchpad.json"


@app.task(autoretry_for=(Exception,))
def get_source_code(project_info, clone_url, pid, current_path):
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)
    result = get_clone_code(crawlingInfo, clone_url, pid, current_path)
    return True

def get_clone_code(crawlingInfo,clone_url, pid, current_path):
    command = "git clone {} {}".format(clone_url, crawlingInfo.projectName)
    log.warning(command)

    remote_repo_revision = None
    try:
        remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
    except Exception as e:
        log.error(e)
        remote_repo_revision = []

    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
        log.error("Project has no revision. {}".format(crawlingInfo.projectName))
        return False

    file_dir = download_path
    initalPath = current_path
    revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
    for rev in revision_list:
        os.chdir(initalPath)
        log.warning(initalPath)
        git_hash = rev[0]
        revision = rev[1].split("/")[-1]

        # 특수문자 replace
        release_ver = re.sub('[\\\\/:*?\"<>|]', '_', revision)
        rel_createdOn = ""
        command = "git clone {} {}".format(clone_url, release_ver)
        log.warning(command)
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
