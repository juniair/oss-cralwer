#-*- coding:utf-8 -*-


import os, sys, json, platform


from worker import app
from logger import getLogger, write_progress_log
from crawler import DataBase_Crawler_DB, CrawlingInfo
import GetRepoInfo
from github import source_page as source_tasks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = BASE_DIR + "/../../data"  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir" # sourceforge 프로젝트 다운로드 경로

log = getLogger(filename="github_crawler.log")


@app.task(autoretry_for=(Exception,))
def get_release_info(item, current_path, current_status):
    # if item haven't license information, skip this.
    if item['license'] is None:
        log.warning(item["name"] + " do not have license information....")
    else:
        get_source_code_with_release_info(item, current_path, current_status)
    return True

def get_source_code_with_release_info(item, current_path, current_status):
    crawlerInfo = CrawlingInfo(
        crawlerName="github_re",
        projectName=item["name"] if item.get("name") else "UnKnown",
        projectUrl=item["html_url"] if item.get("html_url") else "",
        summary=item["description"] if item.get("description") else "",
        homepageUrl=item["homepage"] if item.get("homepage") else "",
        createdOn="",
        programmingLanguage=item["language"] if item.get("language") else "",
        License=item["license"]["name"] if item["license"].get("name") else ""
    )
    
    log.debug("[ " + crawlerInfo.projectName + " ]")
    if item['clone_url'] is not None:
        pid = crawlerInfo.project_db_insert()

        # print("Clone URL : " + item['clone_url'])
        command = "git clone {0} {1}".format(item['clone_url'], item['name'] + '_' + str(item['id']))
        
        log.debug("get release list from repository :"+item['clone_url'])
        try:
            log.debug(command)
            remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
        except:
            remote_repo_revision = "0"
        # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
        if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
            log.warning(crawlerInfo.projectName+" has no revision information")
            return 

        # 프로젝트 디렉토리 생성
        try:
            os.chdir(crawlerInfo.projectName)
        except:
            os.mkdir(crawlerInfo.projectName)
            os.chdir(crawlerInfo.projectName)

        # change project directory
        current_path = os.getcwd()

        ### 여기서 소스코드 다운로드 요청 
        source_tasks.get_source_code.delay(
            item,
            remote_repo_revision, 
            pid, 
            current_path,
            current_status)

        os.chdir(current_path)

