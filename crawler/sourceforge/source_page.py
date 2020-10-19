# -*- coding: utf-8 -*-

import os
import re
import io
import sys
import json
import requests
import shutil
import traceback
import logging
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from celery.utils.log import get_task_logger

from worker import app
from logger import getLogger, write_progress_log
from crawler import DataBase_Crawler_DB, CrawlingInfo
import md5hasher
import VCSDownloader, URLDownloader
from common import get_http_headers, get_tor_proxy, extract_file, getenv

# log = logging.getLogger(__name__) # getLogger(filename="sourceforge_source_page.log")
log = get_task_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH") # BASE_DIR + "/../../data"  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/sourceforgeDir" # sourceforge 프로젝트 다운로드 경로

@app.task(autoretry_for=(Exception,))
def download_from_sourceforge_code_tab(url, projectInfo, projectName, pid, current_path, progress_status):
    log.warning(
        "exec download_from_sourceforge_source_tab : current_path={}".format(current_path))
    os.chdir(current_path)
    if not os.path.isdir("_vcs"):
        os.mkdir("_vcs")
    os.chdir("_vcs")
    current_path = os.getcwd()

    log.debug(projectInfo)
    projectInfo.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    projectInfo.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**projectInfo)
    result = search_sourcefile_from_code_tab(
        url, crawlingInfo, projectName, pid, current_path)
    
    # rename_directory(projectName, pid)
    progress_status["LAST_PROJECT_NUMBER"] += 1

    write_progress_log(
        progress_status["LAST_SEARCH_CATEGORY"], 
        progress_status["LAST_SEARCH_PAGE"], 
        progress_status["LAST_PROJECT_NUMBER"], 
        progress_status["PROGRESS_LOG_FILENAME"])
    return result


@app.task(autoretry_for=(Exception,))
def download_from_sourceforge_files_tab(url, projectInfo, projectName, pid, current_path, progress_status):
    log.warning(
        "exec download_from_sourceforge_code_tab : current_path={}".format(current_path))
    os.chdir(current_path)
    log.debug(projectInfo)
    projectInfo.pop("projectUrlHash", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("hashing", None) # 클래스 생성자에서 만들어지는 멤버이기 때문에 삭제
    projectInfo.pop("nameMargin", None) # 클래스 생성자에 없는 파라미터 삭제
    projectInfo.pop("pppid", None) # 클래스 생성자에 없는 파라미터 삭제
    crawlingInfo = CrawlingInfo(**projectInfo)
    result = search_sourcefile_from_files_tab(url, crawlingInfo, projectName, pid, current_path, "")
    
    # rename_directory(projectName, pid)
    progress_status["LAST_PROJECT_NUMBER"] += 1

    write_progress_log(
        progress_status["LAST_SEARCH_CATEGORY"], 
        progress_status["LAST_SEARCH_PAGE"], 
        progress_status["LAST_PROJECT_NUMBER"], 
        progress_status["PROGRESS_LOG_FILENAME"])
    return result


def rename_directory(projectName, pid):
    org_path = os.getcwd()
    os.chdir(download_path)
    log.debug("rename_directory: current directory="+download_path+"/"+projectName)
    try:
        newdirname = str(pid)
        log.debug("Rename " + projectName + " > " + newdirname)
        if os.path.exists(projectName):
            # pid 디렉토리가 존재 한다면 삭제
            if os.path.isdir(newdirname):
                shutil.rmtree(newdirname)
            os.rename(projectName, newdirname)
    except Exception as e:
        log.error(str(e))
    os.chdir(org_path)


def get_latest_commit_date_from_cvs_history(history_url):
    history_url = "https://sourceforge.net"+history_url
    try:
        response = requests.get(history_url, headers=get_http_headers(), proxies=get_tor_proxy())
    except requests.exceptions.ConnectionError:
        # 오류 로그 기록
        log.error("ConnectionError : "+history_url)
        return ""

    html = response.text
    soup = BeautifulSoup(html, 'lxml')
    rev_list = soup.findAll('tr', {"class":"rev"}) 
    if len[rev_list] > 0:
        td_list = rev_list[0].findAll("td")
        if len(td_list) > 2:
            return td_list[1].text.strip()
    return ""

def insert_release_version(revision_name, modified_dt, pid, crawlerInfo):
    # file_db insert
    revision = "/".join(revision_name if revision_name is not None else 'UnKnown')
    # db에 저장 되는 경로는 docker환경이 아닌 host의 file경로 정의
    file_dir = "/HDD2"+download_path 
    fileInfo = [file_dir, revision, modified_dt, pid]
    log.info("insert_release_version : projectName="+crawlerInfo.projectName)
    log.info("insert_release_version : revision="+revision)
    log.info("insert_release_version : modified_dt="+modified_dt)
    crawlerInfo.project_file_db_insert(fileInfo)

def exists_release_version(revision_name, crawlerInfo):
    revision = "/".join(revision_name if revision_name is not None else 'UnKnown')
    return crawlerInfo.project_file_db_exists(revision)

# Code를 통해 소스코드를 받을 수 있는지 검사, 다운로드하는 함수.
# 기본적으로는 access_url이 있는지 검사하여, input field의 내용을 subprocess를 통해 실행시킨다.
def search_sourcefile_from_code_tab(url, crawlingInfo, projectName, pid, current_path):
    initialPath = current_path # os.getcwd()
    log.warning("search_sourcefile_from_source_tab.initialPath="+initialPath)
    result = False

    # Code 탭이 외부 링크로 연결된다면, response가 깨지게된다. ConnectionError가 발생하므로 이를 고침.
    try:
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    except requests.exceptions.ConnectionError:
        # 오류 로그 기록
        log.error("ConnectionError : "+url)
        return result

    html = response.text
    soup = BeautifulSoup(html, 'lxml')
    access_url = soup.find('input', {'id': 'access_url'})
    access_urls = soup.find('div', {'id': "access_urls"})

    # release 정보를 insert 해야 함
    history_url = soup.find('a', {'title':'History'})
    if history_url:
        latest_commit_date = get_latest_commit_date_from_cvs_history(history_url["href"])
    else: latest_commit_date = ""
    
    # 릴리스 정보가 이미 DB에 있는 경우  psss
    if exists_release_version(["UnKnown"], crawlingInfo) != False: 
        log.warning("release [{}] is exists!".format("/".join(["UnKnown"])))
        return True

    insert_release_version(["UnKnown"], latest_commit_date, pid, crawlingInfo)

    # revision 디렉토리 생성하고 이동
    sub_directory = os.path.join(os.getcwd(), "UnKnown")
    log.debug('sub_directory='+sub_directory)
    # os.mkdir(directory['title'])
    os.makedirs(sub_directory)
    os.chdir(sub_directory)

    # access_urls 란이 없는 경우는 Read Only CVS임. (git, svn, hg 접속을 할 수 없음)
    # 한 번 더 request를 보내서 command를 찾아내고, 실행환경이 windows가 아니면 다운로드 시작(windows면 pop-up alert가 방해하여 제한)
    if access_urls is None:
        div = soup.find('div', {'class': 'grid-24 pad'})
        alists = div.findAll('a')
        linktag = alists[-1]
        cvs_repo_link = linktag['href']
        cvs_request = requests.get(cvs_repo_link, headers=get_http_headers(), proxies=get_tor_proxy())
        cvs_soup = BeautifulSoup(cvs_request.text, 'lxml')
        listitems = cvs_soup.findAll('b')

        checkflag = True
        for list in listitems:
            command = list.text
            if 'cvs -z3' in command:
                if VCSDownloader.download(command) == 0:
                    checkflag = False
        result = True if checkflag else False

    # Read Only인 경우 다운로드 불가. (이 경우는 git, svn, hg Read Only인 경우.)
    elif access_urls.find('span').text is "Read Only access":
        result = False

    # access url이 존재하면 command를 추출하여 VCSDownloader.download(command) 호출.
    elif access_url is not None:
        command = access_url['value']
        result = VCSDownloader.download(command)
        log.debug("VCS Download result="+result)
        result = True if result else False

    return result


# Files 탭으로부터 출발하여 재귀적으로 디렉토리 파고들어 파일만 존재하게되면 다운로드한다.
def search_sourcefile_from_files_tab(url, crawlingInfo, projectName, pid, current_path, release=None):
    # 릴리스 정보 저장할 변수 초기화
    if not release: release = {"version":[], "modified_dt":""}

    initialPath = current_path # os.getcwd()
    log.warning("search_sourcefile_from_files_tab.initialPath="+initialPath)
    try:
        response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    except requests.exceptions.ConnectionError as e:
        log.error(str(e))
        # 오류 로그 기록
        log.error("ConnectionError : "+url)
        return False

    soup = BeautifulSoup(response.text, 'lxml')
    fileList = soup.find('table', {'id': "files_list"})
    if fileList is None:
        log.error(projectName+" --> file_list is not found!!!!!")
        return False
        
    tableBody = fileList.find('tbody')
    directories = tableBody.findAll('tr', {'class': "folder"})
    
    ret = False
    if len(directories) is not 0:
        chkval = 0
        for directory in directories:
            if directory['title'] is None:
                continue
            log.debug("find directory :"+ directory['title'])

            regex = re.compile('([0-9][.][0-9])')
            p_match = regex.search(directory['title'])
            if p_match:
                if not os.path.isdir(directory['title']):
                    log.debug("pattern match!!")
                    chkval += 1

            if not os.path.isdir(directory['title']):
                #  [Errno 2] No such file or directory 오류가 나는 경우가 있음
                # os.makedirs(path) 
                # https://stackoverflow.com/questions/59181118/os-mkdir-returns-error-filenotfounderror-errno-2-no-such-file-or-directory
                sub_directory = os.path.join(os.getcwd(), directory['title'])
                log.debug('sub_directory='+sub_directory)
                # os.mkdir(directory['title'])
                os.makedirs(sub_directory)

            parent_directory = os.getcwd()
            os.chdir(directory['title']) # folder로 이동

            link = directory.find('a')['href']
            # 폴더를 리비젼 정보로 저장한다.
            release["version"].append(directory["title"])
            release["modified_dt"] = directory.find("abbr")["title"][:10] # YYYY-mm-dd

            search_sourcefile_from_files_tab(
                "https://sourceforge.net" + link, crawlingInfo, projectName, pid, os.getcwd(), release)
            os.chdir(parent_directory) # ('..')
            # 마지막 추가된 폴더 제거
            if len(release["version"]) > 0: del release["version"][-1] 
            ret = (chkval >= 1)
    else:
        # 릴리스 정보가 이미 DB에 있는 경우  psss
        if exists_release_version(release["version"], crawlingInfo) != False: 
            log.warning("release [{}] is exists!".format("/".join(release["version"])))
            return True
        
        # 릴리즈 버젼 정보가 없는 경우는 UnKnown으로 디렉토리를 생성한다.
        if len(release["version"]) == 0:
            sub_directory = os.path.join(os.getcwd(), "UnKnown")
            log.debug('sub_directory='+sub_directory)
            # os.mkdir(directory['title'])
            os.makedirs(sub_directory)
            os.chdir(sub_directory)
            release["version"].append('UnKnown')

        # 릴리스 정보 insert
        insert_release_version(release["version"], release["modified_dt"], pid, crawlingInfo)

        # 다운로드 수행
        files = tableBody.findAll('tr', {'class': "file"})
        for fileElement in files:
            url = fileElement.find('a')['href']
            size = fileElement.find('td', {'headers': 'files_size_h'}).text
            # 압축파일은 압축 해제
            name = fileElement['title']
            try:
                result = URLDownloader.download(url, name, size, True)
                if (result):
                    try:
                        log.debug("extract file name >> " + name)
                        result = extract_file(name, os.getcwd())
                        if result:
                            log.debug("delete : " + os.getcwd() + "/" + name)
                            os.remove(os.getcwd() + "/" + name)
                        ret = True
                    except Exception as e:
                        log.error(str(e))
                        log.error("Decompression file error! file="+name)
                        ret = False
            except Exception as e:
                traceback.print_exc()
                log.error(str(e))
                log.error("Download Error :"+url)
                result = False
    return ret
