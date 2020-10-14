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
from datetime import datetime

from worker.bitbucket import app
from bitbucket import source_page as source_tasks

import md5hasher
import GetRepoInfo
from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from logger import getLogger, write_progress_log
from common import get_http_headers, get_tor_proxy, getenv


log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/bitbucketDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_bitbucket.json"


@app.task(autoretry_for=(Exception,))
def get_release_info(item, current_path):
    result = get_source_code(item, current_path)
    return result


def get_source_code(item, current_path):
    owner_login = item['workspace']['slug']
    # 디렉토리명으로 특수문자 안들어가도록 replace
    item_name = re.sub('[\\\\/:*?"<>|]', '_', item['name'])
    projectName = "{}_{}".format((item_name if item.get("name") else "UnKnown"), owner_login)
    createdOn = datetime.strptime(item['created_on'].replace('T', ' ').split(' ')[0], "%Y-%m-%d").date()
    crawlerInfo = CrawlingInfo(
        crawlerName="bitbucket_re",
        projectName=projectName,
        projectUrl=item['links']['html']['href'],
        summary=item['description'],
        homepageUrl=item['website'],
        developer=owner_login,
        createdOn=createdOn,
        programmingLanguage=item['language'],
        License=""
    )
    
    log.debug("Download [ " + crawlerInfo.projectName + " ]")

    if item["links"]["clone"][0].get("href"):
        # DB 부분은 테스트로 제외
        # project 정보 체크하여 있다면 다운로드 받은 것으로 판단하고 pass
        # pid = crawlerInfo.project_db_exists()
        if pid == False:
            log.warning("{} is inserted !!!!".format(crawlerInfo.projectName))
            pid = crawlerInfo.project_db_insert()
        else:
            # 해당 프로젝트는 이미 다운로드 받은 것으로 간주하고 pass
            # 프로젝트 정보만 등록 되고 소스 코드는 다운로드 안된 경우는 어떻게 할까?
            log.warning("{} is founded !!!!".format(crawlerInfo.projectName))
        # pid = 1 # debug

        # 프로젝트 디렉토리 생성
        os.chdir(current_path)
        try:
            os.chdir(crawlerInfo.projectName)
        except:
            os.mkdir(crawlerInfo.projectName)
            os.chdir(crawlerInfo.projectName)

        # change project directory
        current_path = os.getcwd()

        ### 여기서 소스코드 다운로드 요청 
        scm = item["scm"]
        clone_url = item["links"]["clone"][0]["href"]
        tags_url = item['links']['tags']['href']
        log.debug("call source_tasks.get_source_code.delay: {}".format(clone_url))
        source_tasks.get_source_code.delay(
            crawlerInfo.__dict__,
            scm,
            clone_url,
            tags_url,
            pid,
            current_path
        )
        return True
    else:
        log.warning("Project[{}] does not have clone url...".format(crawlerInfo.projectName))
        return False

