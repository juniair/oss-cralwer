# -*- coding: utf-8 -*-
import os
import requests
import json
import logging
import md5hasher
from datetime import datetime

from crawler import DataBase_Crawler_DB, CrawlingInfo, Crawler
from common import get_http_headers, get_tor_proxy, getenv
from worker.gitlab import app
from gitlab import source_page as source_task

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gitlabDir" # sourceforge 프로젝트 다운로드 경로

@app.task(autoretry_for=(Exception,))
def get_project_info(item, current_path):
    result = get_project_page(item, current_path)
    return result



def get_tags(project_id):
    log.debug("get_tags id={}".format(project_id))
    tags_url = "https://gitlab.com/api/v4/projects/{0}/repository/tags".format(project_id)
    
    try:
        tag_response = requests.get(tags_url, headers=get_http_headers(), proxies=get_tor_proxy())
        tag_response_json = json.loads(tag_response.text)
    except Exception as e:
        log.error(e)
        tag_response_json = []

    return tag_response_json

def get_license(project_id):
    log.debug("get_license id={}".format(project_id))
    license_url = "https://gitlab.com/api/v4/projects/{}?license=True".format(project_id)
    # if License Not found, skip it.
    detail_response_json = None
    try:
        detail_response = requests.get(license_url, headers=get_http_headers(), proxies=get_tor_proxy())
        detail_response_text = detail_response.text
        
        detail_response_json = json.loads(detail_response_text)
        log.debug(detail_response_json)
    except Exception as e:
        log.error(e)

    return detail_response_json

def get_languages(project_id):
    language_url = "https://gitlab.com/api/v4/projects/{}/languages".format(project_id)
    pl_response = requests.get(language_url, headers=get_http_headers())
    pl_response_text = pl_response.text
    pl_response_json = json.loads(pl_response_text)

    programmingLanguage= []
    for key in list(pl_response_json.keys()):
        programmingLanguage.append(key)
    return programmingLanguage


def get_project_page(item, current_path):
    log.debug(item)
    os.chdir(current_path)
    
    try:
        if item.get('forked_from_project'):
            log.warning("{}, Forked From Project Skip !!!!".format(item["name"]))
            return False

        detail_info = get_license(item["id"])
        # if default_branch property not found skip (Maybe Non-public Repo)
        if detail_info['default_branch'] is None:
            log.error("{} has no default_branch!!!".format(item["name"]))
            return False

        # master 는 없기 때문에 master 브랜치만 추가 해야 한다.
        tag_response_json = get_tags(item["id"])

        default_branch = detail_info['default_branch']
        projectUrl = item['web_url']
        projectName = item['name'] if item.get('name') else item["id"]
        description = item['description']
        try:
            License = detail_info['license']['name'] if detail_info.get("license") else "UnKnown"
        except Exception as e:
            log.error(e)
            License = "UnKnown"

        programmingLanguage = get_languages(item["id"])

        try:
            createdOn = detail_info["created_at"].split("T")[0]
            createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
        except Exception as e:
            log.error(e)
            createdOn = ""

        # OS에 맞는 경로 설정
        file_dir = download_path

        log.debug("[ " + projectName + " ]")

        crawlingInfo = CrawlingInfo(
            crawlerName="gitlab_re",
            projectName=projectName,
            projectUrl=projectUrl,
            summary=description,
            createdOn=createdOn,
            programmingLanguage=programmingLanguage,
            License=License
        )

        ppid = crawlingInfo.project_db_exists()
        if ppid:
            log.warning("{} is downloaded....".format(crawlingInfo.projectName))
            pid = ppid
        else:
            pid = crawlingInfo.project_db_insert()
        # pid = 1 # test

        log.debug("current_path="+current_path)
        try:
            os.chdir(projectName)
        except:
            os.mkdir(projectName)
            os.chdir(projectName)
        
        current_path = os.getcwd()

        clone_url = detail_info["http_url_to_repo"]
        source_task.get_source_code.delay(
            crawlingInfo.__dict__, 
            clone_url, 
            tag_response_json, 
            default_branch,
            pid,
            current_path)
    except Exception as e:
        log.error(e)
    return True

