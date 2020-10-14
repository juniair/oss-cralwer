# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

from worker.launchpad import app
from crawler import CrawlingInfo
from common import getenv, get_http_headers, get_tor_proxy

from launchpad import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/launchpadDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_launchpad.json"


@app.task(autoretry_for=(Exception, ))
def get_project_info(entry, current_path):
    result = get_project_page(entry, current_path)
    return True

def get_json(url):
    response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    data = json.loads(response.text)
    return data

def get_milestones(url):
    milestones = get_json(url)
    return milestones

def is_not_downloadable(web_link):
    url = "https://git.launchpad.net/" + web_link.split('/')[-1]
    downloadable = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    return downloadable.url != url

def get_owner(owner_link):
    owner_response_json = get_json(owner_link)
    return owner_response_json

def get_project_page(entry, current_path):
    os.chdir(current_path)
    # self.count += 1
    project_name = entry['title'] if entry.get('title') else ""

    if project_name == "":
        log.error("There is no project name...")
        return False

    # Only allow Git.
    if any([entry['vcs'] == None, entry['vcs'] == 'Bazaar']):
        log.error("Only allow git repository...{}".format(project_name))
        return False
    
    milestones = get_milestones(entry['all_milestones_collection_link'])

    # if this project haven't milestone, skip it.
    if milestones['total_size'] == 0:
        log.error("this project haven't milestone...{}".format(project_name))
        # return False

    if is_not_downloadable(entry['web_link']):
        log.error("It is not downloadable...{}".format(project_name))
        return False

    projectUrl = entry['web_link'] if entry.get('web_link') else ""
    homepageUrl = entry['homepage_url'] if entry.get('homepage_url') else ""

    # 프로젝트명의 특수문자때문에 오류발생하여 추가
    project_name = re.sub('[\\\\/:*?"<>|]', '_', project_name)

    owner_response_json = get_owner(entry["owner_link"])
    projectDeveloper = owner_response_json['name'] if owner_response_json.get('name') else ""

    summary = entry['summary'].strip() if (entry['summary'] is not None) else ""
    
    entry_licenses = list(filter(lambda x: x != "I don't know yet", entry['licenses']))
    licenses = ",".join(entry_licenses)

    programmingLanguage = entry['programming_language'] if entry.get('programming_language') else ""
    createdOn = entry['date_created'].split('T')[0]
    createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()

    crawling_info = CrawlingInfo(
        crawlerName="launchpad_re",
        projectName=project_name,
        projectUrl=projectUrl,
        summary=summary,
        createdOn=createdOn,
        homepageUrl=homepageUrl,
        developer=projectDeveloper,
        programmingLanguage=programmingLanguage,
        License=licenses
    )

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
    log.warning(current_path)
    # command = "git clone https://git.launchpad.net/{0} {0}".format(entry['web_link'].split('/')[-1])
    # log.warning(command)
    clone_url = "https://git.launchpad.net/{}".format(entry['web_link'].split('/')[-1])
    log.warning(clone_url)

    source_page.get_source_code.delay(crawling_info.__dict__, clone_url, pid, current_path)

    return True