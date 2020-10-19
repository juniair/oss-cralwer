#-*- coding:utf-8 -*-


import os, sys, json, platform
import logging
from datetime import datetime

from worker.github import app

from logger import getLogger
from crawler import CrawlingInfo
from common import getenv, get_yyyy_mm_dd

from github import source_page as source_tasks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir" # sourceforge 프로젝트 다운로드 경로

log = logging.getLogger(__name__) # getLogger(filename="github_crawler.log")


@app.task(autoretry_for=(Exception,))
def get_release_info(item, current_path, progress_status):
    result = True
    # if item['license'] is None:
    #     log.warning(item["name"] + " do not have license information....")
    #     # item['license'] = {"key": "UnKnown", "name": "UnKnown", "spdx_id": "UnKnown", "url": "", "node_id": ""}
    # else:
    #     result = get_source_code_with_release_info(item, current_path, progress_status)
    if item['license'] is None:
        log.warning("{}[{}] do not have license information....".format(item["name"], item['full_name']))
        item['license'] = {
            "key": "",
            "name": 'UnKnown',
            "spdx_id": "",
            "url": "",
            "node_id": ""
            }
    result = get_source_code_with_release_info(item, current_path, progress_status)
    return result

def get_source_code_with_release_info(item, current_path, progress_status):
    owner_login = item['owner']['login']
    projectName = "{}_{}".format((item["name"] if item.get("name") else "UnKnown"), owner_login)
    createdOn = datetime.strptime(get_yyyy_mm_dd(item["created_at"]), "%Y-%m-%d").date()
    crawlerInfo = CrawlingInfo(
        crawlerName="github_re",
        projectName=projectName,
        projectUrl=item["html_url"] if item.get("html_url") else "",
        summary=item["description"] if item.get("description") else "",
        homepageUrl=item["homepage"] if item.get("homepage") else "",
        developer=owner_login,
        createdOn=createdOn,
        programmingLanguage=item["language"] if item.get("language") else "",
        License=item["license"]["name"] if item["license"].get("name") else ""
    )
    
    log.debug("Download [ " + crawlerInfo.projectName + " ]")
    if item['clone_url'] is not None:
        # DB 부분은 테스트로 제외
        # project 정보 체크하여 있다면 다운로드 받은 것으로 판단하고 pass
        pid = crawlerInfo.project_db_exists()
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
        log.debug("call source_tasks.get_source_code.delay: {}".format(item['clone_url']))
        source_tasks.get_source_code.delay(
            crawlerInfo.__dict__,
            item['clone_url'],
            item['id'],
            # item,
            # remote_repo_revision, 
            pid, 
            current_path,
            progress_status)

        return True
    else:
        log.warning("Project[{}] does not have clone url...".format(crawlerInfo.projectName))
        return False
