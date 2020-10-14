# -*- coding: utf-8 -*-

import os
import json
import logging
import platform
from datetime import datetime
import traceback

from worker.apache import app
from apache import source_page

from crawler import CrawlingInfo
from GetRepoInfo import GetRepoInfo
from common import getenv, get_http_headers, get_tor_proxy

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/apacheDir" # sourceforge 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_apache.json"


@app.task(autoretry_for=(Exception, ))
def get_project_info(project_key, project_info, current_path):
    initialPath = current_path

    try:
        repositories = []
        if project_info.get('repository'):
            repositories = project_info['repository']

        if (len(repositories) == 0):
            log.error("{} has no repository.".format(project_key))
            return False 

        projectUrl = "https://projects.apache.org/project.html?" + project_key
        projectName = project_info['name']

        summary = ""
        if project_info.get('shortdesc'):
            summary = project_info['shortdesc'].strip()
        elif project_info.get('description'):
            summary = project_info['description'].strip()

        homepageUrl = project_info['homepage']

        createdOn = project_info['created'] if project_info.get("created") else ""
        if createdOn != "":
            createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()

        developer = ""
        if project_info.get('developer'):
            temp = []
            for person in project_info['developer']:
                temp.append(person['name'])
            developer = ",".join(temp)
        elif project_info.get("maintainer"):
            temp = []
            for person in project_info['maintainer']:
                temp.append(person['name'])
            developer = ",".join(temp)

        category = project_info['category'] if project_info.get("category") else ""
        
        programming_language = project_info['programming-language'] if project_info.get("programming-language") else ""
        programmingLanguage = [lang.strip() for lang in programming_language.split(",") if lang != '']

        project_ver = project_info['version'] if project_info.get("version") else "UnKnown"
        
        release_list = None
        if project_info.get('release'):
            release_list = []
            for element in project_info['release']:
                release_list.append(element)
        else:
            release_list = []

        License = "Apache License 2.0"

        os.chdir(current_path)

        crawlingInfo = CrawlingInfo(
            crawlerName="apache_re",
            projectName=projectName,
            projectUrl=projectUrl,
            homepageUrl=homepageUrl,
            developer=developer,
            summary=summary,
            category=category,
            License=License,
            createdOn=createdOn,
            programmingLanguage=programmingLanguage,
            project_ver=project_ver
        )

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
            repositories,
            release_list,
            project_key,
            pid,
            current_path
        )
        os.chdir(initialPath)
    except Exception as e:
        log.error(e)
        traceback.print_stack()
        raise e
    return True


