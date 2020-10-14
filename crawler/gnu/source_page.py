# -*- coding: utf-8 -*-
import os
import re
import logging

from worker.gnu import app
from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
import VCSDownloader
from common import getenv, get_http_headers, get_tor_proxy

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gnuDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_gnu.json"

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
    vcsType = clone_url["vcsType"]
    command = clone_url["command"]
    # hg clone https://hg.savannah.nongnu.org/hgweb/toy-releng/
    # git clone https://git.savannah.gnu.org/git/gift.git
    # cvs -z3 -d:pserver:anonymous@cvs.savannah.nongnu.org:/web/turtledenetrix co turtledenetrix
    file_dir = download_path
    # try:

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

    initalPath = current_path
    revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
    for rev in revision_list:
        command = clone_url["command"]
        
        os.chdir(initalPath)
        log.warning(initalPath)
        git_hash = rev[0]
        revision = rev[1].split("/")[-1]
        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
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
        downresult = VCSDownloader.download(command)
        if downresult >= 1:
            if vcsType == 'git':
                rel_createdOn = GetRepoInfo.ResetHardGit(command, git_hash, revision)

            fileInfo = [file_dir, revision, rel_createdOn]
            crawlingInfo.project_file_db_insert(fileInfo)
            log.info("downloaded {}, {}".format(crawlingInfo.projectName, revision))
        else:
            log.info("fail to download {}, {}".format(crawlingInfo.projectName, revision))

    return True