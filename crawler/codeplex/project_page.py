# -*- coding: utf-8 -*-

import os
import re
import platform
import logging
import json
from bs4 import BeautifulSoup
from functools import reduce
import shutil
import requests
from datetime import datetime

from worker.codeplex import app
from crawler import CrawlingInfo
from common import getenv, get_http_headers, get_tor_proxy
import zipfile_custom
import URLDownloader

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/codeplexDir" # sourceforge 프로젝트 다운로드 경로


@app.task(autoretry_for=(Exception,))
def get_project_info(project_name, current_path):
    result = download_source(project_name, current_path)
    return result

def get_project_metadata(project_name):
    lowerPN = project_name.lower()
    project_info = None
    try:
        loadjs = "https://archive.codeplex.com/metadata/{}.json".format(lowerPN)
        project_info = json.loads(requests.get(loadjs).text)
    except Exception as e:
        log.error(e)
    return project_info

def check_programming_language(content):
    try:
        pl_pattern = re.compile('java(\w)*|c#|c\+\+|python|php|scala|kotlin|swift|vue|visual basic|\.NET|groovy|jsp|asp|pascal|javascript|go', re.I)
        pl_search = pl_pattern.search(content)
        programmingLanguage = pl_search.group()
    except:
        programmingLanguage = ""
    return programmingLanguage

def check_version(htmlsource):
    try:
        ver_pattern = re.compile('(version|ver|v)(\s)?(\d[.]?)+', re.I)
        ver_match = ver_pattern.match(htmlsource)
        version = ver_match.group()
    except:
        version = "UnKnown"
    return version

def check_sourceCode(current_path):
    # 소스코드가 sourceCode/sourceCode.zip 형태로 압축 되어 있는 경우를 체크 해야 함
    sourceCode_directory = "{}/sourceCode".format(current_path)
    os.chdir(sourceCode_directory)
    sourceCode_zip_file = "sourceCode.zip"

    result = False
    if os.path.isfile(sourceCode_zip_file):
        try:
            log.warning("extract sourceCode.zip ...")
            with zipfile_custom.ZipFile(sourceCode_zip_file) as z:
                z.extractall()
            os.remove(os.getcwd() + "/" + sourceCode_zip_file)
            result = True
        except Exception as e:
            log.error(e)
    
    os.chdir(current_path)
    return result

def download_source(project_name, current_path):
    os.chdir(current_path)

    projectUrl = "https://archive.codeplex.com/?p=" + project_name
    projectSoup = BeautifulSoup(requests.get(projectUrl).text, "html.parser")
    
    project_info = get_project_metadata(project_name)
    if project_info is None:
        log.error("{} has no information !!!!".format(project_name))
        return False

    summary = project_info['Description']
    category = project_info['TagList']

    homepageUrl = project_info['MovedLink'] if project_info.get("MovedLink") else ""

    programmingLanguage = check_programming_language(category)
    version = check_version(project_info['HomeWiki'])
    
    # LastEdited
    try:
        rel_createdOn = project_info['LastEdited'].replace('T', ' ').split(' ')[0]
    except:
        rel_createdOn = ""

# Zipdownload
    url = "https://codeplexarchive.blob.core.windows.net/archive/projects/{0}/{0}.zip".format(project_name)

    file_dir = download_path
    log.debug("make directory : {}".format(project_name))
    try:
        os.chdir(project_name)
    except:
        os.mkdir(project_name)
        os.chdir(project_name)

    log.debug("make directory : {}".format(version))
    try:
        os.chdir(version)
    except:
        os.mkdir(version)
        os.chdir(version)

    local_filename ="{}.zip".format(project_name)
    
    result = False
    try:
        result = URLDownloader.download(url, local_filename, 0, True)
        if (result):
            try:
                log.debug("extract file name >> " + local_filename)
                # "\"에 대해 처리를 못함
                # result = extract_file(local_filename, os.getcwd())
                # codeplex의 zip파일이 압축해제 시 우분투서버에서 path 구분자가 / 가 아니라 \ 로 잡혀서 내장에서 따로 빼내서 커스텀함
                with zipfile_custom.ZipFile(local_filename) as z:
                    z.extractall()
                
                check_sourceCode(os.getcwd())
                
                log.debug("delete : " + os.getcwd() + "/" + local_filename)
                os.remove(os.getcwd() + "/" + local_filename)
                result = True
            except Exception as e:
                log.error(str(e))
                log.error("Decompression file error! file="+local_filename)
                result = False
    except Exception as e:
        log.error(e)
        log.error("Download Error :"+url)
        result = False

    if result:
        os.chdir('license')
        with open('license.json', 'r') as li:
            # License
            json_data = json.load(li)
            try:
                License = json_data["Name"]
            except:
                License = ""
            # createdOn
            try:
                temp = json_data["StartDate"]
                co_pattern = re.compile('\d{13}')
                co_match = co_pattern.search(temp)
                temp2 = co_match.group()[0:10]
                createdOn = datetime.fromtimestamp(int(temp2))
            except:
                createdOn = ""

        crawlingInfo = CrawlingInfo(
                crawlerName="codeplex_re",
                projectName=project_name,
                projectUrl=projectUrl,
                summary=summary,
                homepageUrl=homepageUrl,
                createdOn=createdOn,
                programmingLanguage=programmingLanguage,
                License=License,
                category=category,
                project_ver=version,
        )
        os.chdir(current_path)
        pid = crawlingInfo.project_db_insert()

        revision = version

        fileInfo = [file_dir, revision, rel_createdOn]
        crawlingInfo.project_file_db_insert(fileInfo)

    return True