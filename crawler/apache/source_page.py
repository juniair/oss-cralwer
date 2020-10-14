# -*- coding: utf-8 -*-

import os
import re
import json
import logging
from datetime import datetime

from worker.apache import app
from apache import source_page

from crawler import CrawlingInfo
import VCSDownloader
from GetRepoInfo import GetRepoInfo
from common import getenv, get_http_headers, get_tor_proxy

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/apacheDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_apache.json"

@app.task(autoretry_for=(Exception, ))
def get_source_code(project_info, repositories, release_list, project_key, pid, current_path):
    os.chdir(current_path)
    log.debug(project_info)
    project_info.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    project_info.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    project_info.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**project_info)

    result = clone_source_code(crawlingInfo, repositories, release_list, project_key, pid, current_path )
    return result


''' 리포지토리 정보 샘플
"repository": [
      "http://git-wip-us.apache.org/repos/asf/lucy.git"
    ]
"repository": [
      "http://svn.apache.org/repos/asf/ace"
    ]
"repository": [
      "https://gitbox.apache.org/repos/asf/archiva.git",
      "https://svn.apache.org/viewvc/archiva/parent/"
    ]
"repository": [
      "https://github.com/apache/apex-core.git",
      "https://github.com/apache/apex-malhar.git"
    ]
"repository": [
      "https://svn.apache.org/repos/asf/falcon",
      "https://git-wip-us.apache.org/repos/asf?p=falcon.git"
    ]
"repository": [
      "git:http://git-wip-us.apache.org/repos/asf/mrunit.git",
      "git:https://git-wip-us.apache.org/repos/asf/mrunit.git"
    ]
"repository": [
      "http://svn.apache.org/repos/asf/polygene/",
      "https://git-wip-us.apache.org/repos/asf/polygene-java.git"
    ]
'''

def clone_source_code(crawlingInfo, repositories, release_list, project_key, pid, current_path):
    file_dir = download_path

    # 리포지토리 정보가 있으나 git으로 clone이 안되는 프로젝트가 존재함.
    # git과 svn을 동시에 제공하는 프로젝트가 존재함
    for repository in repositories:
        log.warning("{} repository : {}".format(project_key, repository))

        is_git = (repository.split('.')[-1] == 'git')
        command = "git clone" if is_git else "svn checkout"
        command = command + ' ' + repository.replace('?p=', '/') + ' ' + project_key
        log.debug(command)

        try:
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
        except Exception as e:
            log.error(e)
            remote_repo_revision = "0"

        # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
        if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
            log.warning("{} has no revision.".format(crawlingInfo.projectName))
            continue

        # git은 tags의 정보를 release 버전으로 사용할수 있으나 svn은 리비전말고 다른정보가 없어서
        # api에서 제공해주는 버전정보가 있다면 해당정보를 릴리즈버전으로 사용하고 없다면 UnKnown으로 한다.
        if is_git == False:
            # svn의 경우 release_list값이 있는 경우 리비젼 리스트 초기화 하고 release_list 값을 사용
            if len(release_list) > 0:
                remote_repo_revision.clear()
            for rel in release_list:
                remote_repo_revision.append(rel["created"])
                remote_repo_revision.append(rel["revision"])

         # (git_hash, revision_name)형태 배열 재구성
        revision_list = list(zip(remote_repo_revision[0::2], remote_repo_revision[1::2]))
        for rev in revision_list:
            os.chdir(current_path)

            git_hash = rev[0] # svn의 경우 "UnKnown" or release_list의 값
            release_ver = rev[1]
            revision = release_ver.split('/')[-1] # refs/tag or refs/head 를 제외한 이름
            # 특수문자 replace
            revision = re.sub('[\\\\/:*?\"<>|]', '_', revision) # svn의 경우 "UnKnown"

            log.warning(rev)
            log.warning(git_hash)
            log.warning(revision)

            # 리비젼 디렉토리로 코드를 다운 받도록 command 작성
            command = "git clone" if is_git else "svn checkout"
            command = "{} {} {}".format(command,repository.replace('?p=', '/'), revision)
            # 코드 다운로드
            log.debug(command)
            downresult = VCSDownloader.download(command)
            if downresult >= 1:
                try:
                    rel_createdOn = "1900-01-01"
                    if is_git:
                        rel_createdOn = GetRepoInfo.ResetHardGit(command, git_hash, revision)
                    else:
                        # svn
                        if len(release_list) == 0:
                            rel_createdOn = GetRepoInfo.getDateSvn(repository)
                        else:
                            rel_createdOn = rev[0] 

                    fileInfo = [file_dir, revision, rel_createdOn]
                    log.debug(fileInfo)
                    crawlingInfo.project_file_db_insert(fileInfo)
                except Exception as e:
                    log.error(e)
            else:
                log.error("Fail to download : {}".format(repository))
    return True
