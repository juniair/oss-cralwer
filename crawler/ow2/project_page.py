# -*- coding: utf-8 -*-

import os
import json
import requests
import logging
from datetime import datetime

from crawler import CrawlingInfo
from worker.ow2 import app
from common import getenv, get_http_headers, get_tor_proxy

from ow2 import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/ow2Dir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_ow2.json"


@app.task(autoretry_for=(Exception, ))
def get_project_info(project_item, current_path):
    result = get_project_page(project_item, current_path)
    return result

def get_tags(project_id):
    log.debug("get_tags id={}".format(project_id))
    tags_url = "https://gitlab.ow2.org/api/v4/projects/{0}/repository/tags".format(project_id)
    
    try:
        tag_response = requests.get(tags_url, headers=get_http_headers(), proxies=get_tor_proxy())
        tag_response_json = json.loads(tag_response.text)
    except Exception as e:
        log.error(e)
        tag_response_json = []

    return tag_response_json

def get_detail_info(project_id):
    log.debug("get_license id={}".format(project_id))
    license_url = "https://gitlab.ow2.org/api/v4/projects/{0}?license=True".format(project_id)
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
    language_url = "https://gitlab.ow2.org/api/v4/projects/{0}/languages".format(project_id)
    pl_response = requests.get(language_url, headers=get_http_headers())
    pl_response_text = pl_response.text
    pl_response_json = json.loads(pl_response_text)

    programmingLanguage= [key for key in list(pl_response_json.keys())]

    return ",".join(programmingLanguage)

def get_project_page(project_item, current_path):
    os.chdir(current_path)

    if project_item.get('forked_from_project'):
        log.warning("{}, Forked From Project Skip !!!!".format(project_item["name"]))
        return False

    detail_info = get_detail_info(project_item["id"])
    # if default_branch property not found skip (Maybe Non-public Repo)
    if detail_info['default_branch'] is None:
        log.error("{} has no default_branch!!!".format(project_item["name"]))
        return False

    # master 는 없기 때문에 master 브랜치만 추가 해야 한다.
    tag_response_json = get_tags(project_item["id"])

    default_branch = detail_info['default_branch']
    project_url = project_item['web_url']
    project_name = project_item['name'] if project_item.get('name') else project_item["id"]
    description = project_item['description']
    developer =  project_item['name_with_namespace'] if project_item.get('name_with_namespace') else project_item["namespace"]["name"]
    developer = developer.split('/')[0]
    try:
        license = detail_info['license']['name'] if detail_info.get("license") else "UnKnown"
    except Exception as e:
        log.error(e)
        license = "UnKnown"

    programming_language = get_languages(project_item["id"])

    try:
        createdOn = detail_info["created_at"].split("T")[0]
        createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
    except Exception as e:
        log.error(e)
        createdOn = ""

    crawling_info = CrawlingInfo(
        developer=developer,
        crawlerName="ow2_re",
        projectName=project_name,
        projectUrl=project_url,
        homepageUrl=project_url,
        summary=description,
        createdOn=createdOn,
        programmingLanguage=programming_language,
        License=license
    )
    log.warning(crawling_info.__dict__)
    ppid = crawling_info.project_db_exists()
    if ppid:
        log.warning("{} is downloaded....".format(project_name))
        pid = ppid
    else:
        pid = crawling_info.project_db_insert()
    try:
        os.chdir(project_name)
    except:
        os.mkdir(project_name)
        os.chdir(project_name)

    current_path = os.getcwd()
    clone_url = detail_info["http_url_to_repo"]

    source_page.get_source_code.delay(
        crawling_info.__dict__, 
        clone_url, 
        pid, 
        tag_response_json,
        default_branch,
        current_path)
    

    return True