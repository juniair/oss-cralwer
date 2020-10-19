# -*- coding: utf-8 -*-
import os
import re
import json
import requests
import logging
import traceback
from bs4 import BeautifulSoup
from datetime import datetime

from worker.gnu import app
from crawler import CrawlingInfo
from common import getenv, get_http_headers, get_tor_proxy
from gnu import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/gnuDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_gnu.json"

@app.task(autoretry_for=(Exception, ))
def get_project_info(project_info, current_path):
    result = get_project_page(project_info, current_path)
    return True

def get_soup_project_page(project_url):
    response = requests.get(project_url, headers=get_http_headers(), proxies=get_tor_proxy())
    soup = BeautifulSoup(response.text, "html.parser")
    return soup

def get_homepage_url(soup):
    try:
        boxitems = soup.select("div.boxitem")
        homepage_list = list(filter(lambda x: (x.select_one("a") and x.select_one("a").get_text().strip() == "Project Homepage"), boxitems))
        if len(homepage_list) > 0:
            homepage_url = homepage_list[0].select_one("a").attrs["href"]
        else: homepage_url = ""
    except Exception as e:
        log.error("error to get_homepage_url...")
        log.error(e)
        homepage_url = ""
    return homepage_url

def get_createdOn(soup):
    offset = len("Registration Date: ") + 4 # 4 = 영문 요일 표기와 공백문자
    metadata = list(filter(lambda x: "Registration Date" in x.get_text(), soup.select("p")))
    if len(metadata) == 0:
        return ""
    # log.warning(metadata)
    
    try:
        temp_createdOn = metadata[0].get_text().split("\n")[0]
        # Wed 21 Oct 2009 05:39:27 PM UTC
        createdOn = temp_createdOn[offset:]
        # log.warning(createdOn)
        createdOn = datetime.strptime(createdOn,"%d %b %Y %I:%M:%S %p UTC").date()
    except Exception as e:
        log.error("error to get_createdOn...")
        log.error(e)
        createdOn = ""
    return createdOn

def get_license(soup):
    offset = len("License: ")
    metadata = list(filter(lambda x: "Registration Date" in x.get_text(), soup.select("p")))
    if len(metadata) == 0:
        return ""
    try:
        license = metadata[0].get_text().replace("Development Status","\n").split("\n")[1][offset:].strip()
    except Exception as e:
        log.error("error to get_license...")
        log.error(e)
        license = ""
    return license

def get_developers(soup):
    try:
        grouplink = list(filter(lambda x:x.get_text().strip() =="View Members", soup.select("a")))[0].attrs["href"]
        members_url = "https://savannah.gnu.org{}".format(grouplink)
        response = requests.get(members_url)
        teamsoup = BeautifulSoup(response.text,'html.parser')

        # 멤버 테이블이 2개가 나오는 경우도 있어서 첫번째 테이블의 리스트만 사용한다.
        member_rows = teamsoup.select("table.box")[0].select("tr")[1::2]
        # log.warning(member_rows)

        developers = list(
            map(lambda x:re.sub("\s*<(\w*\s*)*>","",x.select_one("a").get_text()),
            list(
                map(lambda x:x.select("td")[1], member_rows)
                )))
        developers.sort()
    except Exception as e:
        log.error("error to get_developers...")
        log.error(e)
        traceback.print_exc()
        developers=[]
    return developers

def get_download_command(download_link):
    response = requests.get("https://savannah.nongnu.org"+download_link, headers=get_http_headers(), proxies=get_tor_proxy())
    soup = BeautifulSoup(response.text,"html.parser")
    if "svn" in download_link:
        command = soup.select("code")[0].get_text().strip()
    else:
        command = soup.select("pre")[0].get_text().strip()
    return command

def get_clone_url(soup):
    toplistitem =soup.select("li.topmenuitemmainitem")
    toplistsourcecode = list(filter((lambda x: x.select_one('a').get_text().strip()=="Source code"),toplistitem))
    if len(toplistsourcecode) == 0:
        return None
    
    toplistsubitem = toplistsourcecode[0].select("li.topmenuitemsubmenu a") 
    downloadItem =  toplistsubitem[0]
    downloadLink = downloadItem.attrs["href"]
    
    command = get_download_command(downloadLink)
    vcsType = command[:3]
    '''
    "Unnamed repository; edit this file 'description' to name the repository.\ngit clone https://git.savannah.gnu.org/git/8sync.git\n\n8sync www.gnu.org web site source\ngit clone https://git.savannah.gnu.org/git/8sync/website.git"
    '''
    if any([vcsType=="svn", vcsType=="cvs", vcsType=="git", vcsType=="hg "]) == False:
        temp = list(filter(lambda x: any([x[:3] == "cvs", x[:3]=="svn", x[:3]=="git", x[:3]=="hg "]), command.split("\n")))
        command = temp[0] # 일단 첫번째 것을 소스코드로 판단하고 진행 
    
    command = command.split("/<")[0]
    vcsType = command.split(' ')[0]

    return {
        "vcsType": vcsType,
        "command": command
    }

def get_project_page(project_info, current_path):
    os.chdir(current_path)

    project_soup = get_soup_project_page(project_info["project_url"])

    # homepageUrl
    homepage_url = get_homepage_url(project_soup)
    if homepage_url == "": homepage_url = project_info["project_url"]
    log.warning("homepage_url={}".format(homepage_url))
    # # craetedOn
    createdOn = get_createdOn(project_soup)
    log.warning(createdOn)
    # # License
    license = get_license(project_soup)
    log.warning(license)
    # # developer
    # #! track from here
    developers = get_developers(project_soup)
    log.warning(developers)
    
    # # category
    category = ""
    # # programmingLanguage
    programmingLanguage =""

    clone_url = get_clone_url(project_soup)
    log.warning(clone_url)
    if clone_url == None:
        log.error("Project has no source code. : {}".format(project_info["project_name"]))
        return False
    
    crawling_info = CrawlingInfo(
        crawlerName="gnu_re",
        projectName=project_info["project_name"],
        projectUrl=project_info["project_url"],
        summary=project_info["summary"],
        homepageUrl=homepage_url,
        createdOn=createdOn,
        developer=','.join(developers),
        programmingLanguage=programmingLanguage,
        License=license
    )
    ppid = crawling_info.project_db_exists()
    if ppid:
        log.warning("{} is downloaded....".format(project_info["project_name"]))
        pid = ppid
    else:
        pid = crawling_info.project_db_insert()

    try:
        os.chdir(project_info["project_name"])
    except:
        os.mkdir(project_info["project_name"])
        os.chdir(project_info["project_name"])

    current_path = os.getcwd()
    source_page.get_source_code.delay(crawling_info.__dict__, clone_url, pid, current_path)
    # source_page.get_source_code(crawling_info.__dict__, clone_url, pid, current_path)
    
    return True