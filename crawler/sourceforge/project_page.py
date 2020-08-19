# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import platform
from signal import *
import requests
import shutil
from datetime import datetime
from bs4 import BeautifulSoup

from worker import app
from logger import getLogger, write_progress_log
from crawler import DataBase_Crawler_DB, CrawlingInfo
import md5hasher
# from .. import download_tasks
from sourceforge import source_page as download_tasks
from common import get_http_headers, get_tor_proxy, getenv

log = getLogger(filename='sourceforge_project_page.log')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH") #BASE_DIR + "/../../data"  # 절대경로 값으로 설정을 해야 하는데...

# 마지막 수행정보를 저장하기 위한 변수들
# default value, 1st category.
LAST_SEARCH_CATEGORY = "development/development"
LAST_SEARCH_PAGE = 0
LAST_PROJECT_NUMBER = 0
item = 0
ver = 0
pid = ""
PROGRESS_LOG_FILENAME = data_path + "/progress_sourceforge.json"

@app.task(autoretry_for=(Exception,))
def get_project_info_from_sourceforge(href, download_path, progress_status):
    log.debug("exec get_project_info_from_sourceforge : {}".format(href))
    if progress_status is None:
        progress_status = {
            "LAST_SEARCH_CATEGORY": LAST_SEARCH_CATEGORY, 
            "LAST_SEARCH_PAGE":LAST_SEARCH_PAGE, 
            "LAST_PROJECT_NUMBER": LAST_PROJECT_NUMBER, 
            "PROGRESS_LOG_FILENAME": PROGRESS_LOG_FILENAME}
    printdetail(href, download_path, progress_status)


# 프로젝트 정보 출력.
# Files 탭이 존재하면 탐색하여 다운로드를 시도.
# code 탭이 존재하면 탐색하여 다운로드를 시도.
def printdetail(href_value, download_path, progress_status):
    log.warning("printdetail. download_path="+download_path)
    os.chdir(download_path) # download_path == data_path+"/sourceforgeDir"

    crawlerInfo = None

    infoAddress = "https://sourceforge.net" + href_value  # href.get('href')
    print(infoAddress)  # debug
    URLHash = md5hasher.hashing(infoAddress)
    response = requests.get(infoAddress, headers=get_http_headers(), proxies=get_tor_proxy())
    html = response.text
    soup = BeautifulSoup(html, 'lxml')
    status = soup.find('div', {'class': "project-status"})

    # status가 존재하면 Realease가 아닌 것으로 판단. Realease가 아니면 볼 필요 없으니 종료.
    if status is not None:
        log.error("Project Status is not None. url="+href_value)
        return 0

    projectUrl = infoAddress
    # print("Project URL Hash : " + URLHash)

    # 프로젝트 이름
    projectName = ''
    className = soup.findAll('div', {'class': "title"})
    for Class in className:
        Name = Class.find('h1')
        projectName = Name.get_text()
        # 프로젝트 이름 특수문자 replace
        projectName = re.sub('[\\\\/:*?"<>|]', '_', projectName)

    # 홈페이지
    homepageURL = ''
    homepage = soup.find('a', {'id': "homepage"})
    if homepage is not None:
        homepageURL = homepage['href']

    # 설명 (없을수도 있음)
    description = soup.find('p', {'class': "description"})
    description_result = ""
    if description is not None:
        description_result = description.text.rstrip()
    summary = description_result

    # 라이센스 (없을수도 있음)
    license = ""
    pspSection = soup.findAll('section', {'class': "row psp-section"})
    if pspSection is not None:
        for sections in pspSection:
            section = sections.findAll('section', {'class': "project-info"})
            for fields in section:
                licenseList = fields.findAll('a')
                for licenseElement in licenseList:
                    license = license + licenseElement.text + ','
                license = license[0:-1]
    License = license

    # 등록일
    createdOn = ''
    classRegistered = soup.findAll('section', {'class': "project-info"})
    for Registered in classRegistered:
        RegisteredList = Registered.findAll('section', {'class': "content"})
        for Register in RegisteredList:
            createdOn = Register.get_text().strip()

    # additionalProjectDetails 가 존재하면 수집.
    additionalProjectDetails = soup.find(
        'section', {'class': "row m-section-additional-details psp-section"})

    file_dir = os.path.join(data_path, "sourceforgeDir") # data_path + ("\\sourceforgeDir\\" if platform.system() == "Windows" else "/sourceforgeDir/")

    if additionalProjectDetails is not None:
        projectInfos = additionalProjectDetails.findAll(
            'section', {'class': "project-info"})
        for project_info in projectInfos:
            info_title = project_info.find('h4').text
           
            # 개발언어
            if info_title == "Programming Language":
                info_contents = project_info.findAll('a')
                programmingLanguages = ""
                for info_content in info_contents:
                    programmingLanguages = programmingLanguages + info_content.text + ","
                programmingLanguages = programmingLanguages[0:-1]
                pl = programmingLanguages

                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
                # log.debug("check2")
                crawlerInfo = CrawlingInfo(
                    crawlerName="sourceforge_re",
                    projectName=projectName,
                    projectUrl=projectUrl,
                    summary=summary,
                    createdOn=createdOn,
                    homepageUrl=homepageURL,
                    programmingLanguage=pl,
                    License=License
                )

                # 프로젝트가 데이터베이스에 등록 되어 있는지 체크
                ppid = crawlerInfo.project_db_exists()
                if ppid:
                    # 해당 프로젝트는 이미 다운로드 받은 것으로 간주하고 pass
                    # 프로젝트 정보만 등록 되고 소스 코드는 다운로드 안된 경우는 어떻게 할까?
                    log.warning("It have already downloaded ["+projectName+"]")
                    return True

                pid = crawlerInfo.project_db_insert()
                ppid = crawlerInfo.project_db_exists() # ppid값을 사용하는 의도를 모르겠음

                log.debug("fetch: {}, {}, license={}, pid={}".format(
                    projectName, projectUrl, License, pid))
                # 새 디렉토리 말고 기존 디렉토리에서 이어받기 위하여
                # print("self.pid=",self.pid, "ppid=", ppid)
                if ppid:
                    if int(ppid) < int(pid):
                        pid = ppid
                        log.debug("Change pid : {0}".format(pid))
                if not (os.path.exists(str(pid))):
                    try:
                        # 혹시 모를 이미 만들어진 프로젝트 디렉토리 삭제
                        shutil.rmtree(projectName)
                        log.debug("Delete {0}".format(projectName))
                    except:
                        pass

                    # 프로젝트 디렉토리 이동 없으면 생성하고 이동
                    try:
                        os.chdir(projectName)
                    except:
                        os.mkdir(projectName)
                        os.chdir(projectName)
                else:
                    os.chdir(pid)
                log.warning("printdetail(project) : current directory="+os.getcwd())
    if crawlerInfo:
        # revision = "UnKnown" # sourceforge에서는 revision값이 없는 것으로 가정
        # rel_createdOn = ""

        # # file_db insert
        # try:
        #     os.chdir(revision)
        # except:
        #     os.mkdir(revision)
        #     os.chdir(revision)
        # log.warning("printdetail(revision) : current directory="+os.getcwd())

        # fileInfo = [file_dir, revision, rel_createdOn]
        # crawlerInfo.project_file_db_insert(fileInfo)
        
        current_path = os.getcwd()

        top_nav = soup.find('div', {'id': "top_nav_admin"})
        top_nav_contents = top_nav.findAll('li')
        # Files / Code 둘중에 먼저 조회 되는 페이지를 처리하고 종료
        # 대부분 Files가 먼저 나옴
        for top_nav_content in top_nav_contents:
            link = top_nav_content.find('a')['href']
            element = top_nav_content.find('span')

            if element is None:  # 없으면 컨티뉴.
                continue

            if element.text == "Code":
                # Code 네비게이션을 우선 탐색.
                
                log.debug("Code : https://sourceforge.net" + link)
                # 해당 링크를 기점으로 코드탐색 실행.
                # print(crawlerInfo.__dict__)
                download_tasks.download_from_sourceforge_code_tab.delay(
                    "https://sourceforge.net" + link,
                    crawlerInfo.__dict__,
                    projectName,
                    pid,
                    current_path,
                    progress_status               
                )

                return True
            elif element.text == 'Files':
                # Code 네비게이션이 없으면 Files를 탐색.
                # print("Files : https://sourceforge.net" + link)

                # 해당 링크를 기점으로 파일탐색 실행.
                download_tasks.download_from_sourceforge_files_tab.delay(
                    "https://sourceforge.net" + link,
                    crawlerInfo.__dict__,
                    projectName,
                    pid,
                    current_path,
                    progress_status
                )

                return True
    else:
        log.error(projectName+" --> crawlerInfo is None --> do not found project information(additionalProjectDetails)")
        write_progress_log(
            progress_status["LAST_SEARCH_CATEGORY"], 
            progress_status["LAST_SEARCH_PAGE"], 
            progress_status["LAST_PROJECT_NUMBER"], 
            progress_status["PROGRESS_LOG_FILENAME"])
    return False
