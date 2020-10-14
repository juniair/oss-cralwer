# -*- coding: utf-8 -*-

import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen
from datetime import datetime

from worker.debian import app
from common import getenv, get_http_headers, get_tor_proxy
from license.oss_license import OpenSourceLicense
from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
from debian import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/debianDir" # sourceforge 프로젝트 다운로드 경로

@app.task(autoretry_for=(Exception,))
def get_project_info(project_info, current_path):
    result = get_project_page(project_info, current_path)
    return result

# def check_license_file(license_link):
#     # 라이선스를 체크하는 모듈을 사용해야 한다.
#     log.debug("license link = {}".format(license_link))
#     url = "https://salsa.debian.org/{}".format(license_link)
#     response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
#     # log.warning(response.text)
#     open_source_license = OpenSourceLicense()
#     license_info = open_source_license.find_text_license(response.text)
#     log.warning(license_info)
#     return license_info["license"]


def get_detail_json(project_id):
    log.debug("get_license id={}".format(project_id))
    if project_id == 0: 
        return None

    license_url = "https://salsa.debian.org/api/v4/projects/{}?license=True".format(project_id)
    log.warning("license_url={}".format(license_url))
    # if License Not found, skip it.
    detail_response_json = None
    try:
        detail_response = requests.get(license_url, headers=get_http_headers(), proxies=get_tor_proxy())
        detail_response_text = detail_response.text
        
        detail_response_json = json.loads(detail_response_text)
        # log.warning(detail_response_json)
    except Exception as e:
        log.error(e)

    return detail_response_json

def get_languages(project_id):
    language_url = "https://salsa.debian.org/api/v4/projects/{}/languages".format(project_id)
    pl_response = requests.get(language_url, headers=get_http_headers())
    pl_response_text = pl_response.text
    pl_response_json = json.loads(pl_response_text)

    programmingLanguage= []
    for key in list(pl_response_json.keys()):
        programmingLanguage.append(key)
    return programmingLanguage


def get_project_id(soup):
    project_id = 0
    project_id_obj = soup.select_one(".home-panel-metadata span.text-secondary")
    if project_id_obj:
        temp = project_id_obj.get_text().split(":")
        if len(temp) == 2:
            project_id = int(temp[1].strip())
    return project_id

# data-qa-selector="forked_from_link"  -> fork 된 프로젝트는 bypass???
# (class="home-panel-description").text -> project description
def check_project_page(project_info):
    page_link = project_info["page_link"]
    url = "https://salsa.debian.org/{}".format(page_link)
    project_info["project_link"] = url
    response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    # log.warning(response.text)
    soup = BeautifulSoup(response.text, 'html.parser')

    project_info["project_id"] = get_project_id(soup)
    log.warning(project_info)
    detail_info = get_detail_json(project_info["project_id"])
    
        # # ( name="http_project_clone" ).value -> git clone link
        # http_project_clone = soup.select_one("input[name='http_project_clone']")
        # if http_project_clone:
        #     clone_link = http_project_clone.attrs["value"]
        # else: clone_link = None
        # project_info["clone_link"] = clone_link

        # # (li.nav-item  span.project-stat-value).get_text() == "LICENSE" -> (.nav-link).attrs["href"] -> 라이선스 내용 체크
        # project_stat_value = soup.select_one("li.nav-item  span.project-stat-value")
        
        # if project_stat_value is not None:
        #     text = project_stat_value.get_text().strip()
        #     if text.upper() == "LICENSE":
        #         anchor = project_stat_value.parent
        #         license = check_license_file(anchor.attrs["href"])
        #     else:
        #         license = text
        # else:
        #     license = "UnKnown"

        # project_info["license"] = license

    return detail_info



def get_project_page(project_info, current_path):
    # {'page_link': '/rene/accessodf', 'full_name': 'Rene Engelhard/accessodf', 'license': '', 'description': 'Debian packaging for accessodf'}
    # {'page_link': '/jelmer/acct', 'full_name': 'Jelmer Vernooĳ/acct', 'license': 'GNU General Public License v3.0', 'description': 'acct packaging'}
    os.chdir(current_path)
    # process a project page 

    detail_info = check_project_page(project_info)
    log.warning(detail_info)
    if detail_info == None:
        log.error("project has no detail information : {}".format(project_info["full_name"]))
        return False
    try:
        default_branch = detail_info['default_branch']
        projectUrl = detail_info['web_url']
        homepageUrl = projectUrl
        # projectName = detail_info['name'] if detail_info.get('name') else detail_info["id"]
        # 중복 되는 프로젝트 이름이 있어서 path_with_namespace를 프로젝트 이름으로 사용
        projectName = detail_info['path_with_namespace'] if detail_info.get('path_with_namespace') else detail_info["name"]
        description = detail_info['description']
        clone_url = detail_info["http_url_to_repo"]
        try:
            License = detail_info['license']['name'] if detail_info.get("license") else "UnKnown"
        except Exception as e:
            log.error(e)
            License = "UnKnown"

        programmingLanguage = get_languages(detail_info["id"])

        developer = project_info["full_name"].split("/")[0].strip()
    except Exception as e:
        log.error(e)
        log.error("Project is not existed :{}".format(project_info["full_name"]))
        return False

    try:
        createdOn = detail_info["created_at"].split("T")[0]
        createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
    except Exception as e:
        log.error(e)
        createdOn = ""
    projectName = projectName.replace("/", "_") 
    crawlingInfo = CrawlingInfo(
        crawlerName="debian_re",
        projectName=projectName,
        projectUrl=projectUrl,
        homepageUrl=homepageUrl,
        developer=developer,
        summary=description,
        License=License,
        createdOn=createdOn,
        programmingLanguage=programmingLanguage
    )
    log.warning(crawlingInfo.__dict__)

    ppid = crawlingInfo.project_db_exists()
    if ppid:
        log.warning("{} is downloaded....".format(projectName))
        pid = ppid
    else:
        pid = crawlingInfo.project_db_insert()

    try:
        os.chdir(projectName)
    except:
        os.mkdir(projectName)
        os.chdir(projectName)

    current_path = os.getcwd()

    source_page.get_source_code.delay(
        crawlingInfo.__dict__,
        clone_url, 
        default_branch, 
        pid, 
        current_path
        )
    
    return True