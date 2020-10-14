# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

from worker.osdn import app

from crawler import CrawlingInfo
from common import getenv, get_http_headers, get_tor_proxy

from osdn import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/osdnDir" # launchpad 프로젝트 다운로드 경로

PROGRESS_LOG_FILENAME = data_path + "/progress_osdn.json"

@app.task(autoretry_for=(Exception, ))
def get_project_info(project_url, project_name, current_path):
    result = get_project_page(project_url, project_name, current_path)
    return result

def get_project_soup(project_url):
    # Project information Request
    response = requests.get(project_url)

    # if getting project page is failed, skip.
    if response.status_code == 404: return None

    soup = BeautifulSoup(response.text, 'html.parser')
    return soup
    
def check_source_code( project_soup):
    nav_tab = project_soup.select("ul.nav.nav-tabs.content-menu-for-project")

    # suspended Project Check and Skip. example) https://osdn.net/projects/zytxa/
    if nav_tab is None:
        log.error("It has no navigation tab...")
        return False

    toggle_buttons = nav_tab[0].select("li.dropdown a")
    for button in toggle_buttons:
        if button.text.strip() == 'Source Code': return True

    log.error("Source Code dropdown menu doesn't exist.")
    
    return False

def check_release_list( project_soup):
    # Release Check, if project doesn't have any release, Skip it.
    download_item = project_soup.select("div.ptop-download-item")
    if download_item is None:
        log.error("project doesn't have any release.")
        return False
    else:
        return True

def get_member_list(member_list_link):
    url = "https://osdn.net/{}".format(member_list_link)
    response = requests.get(url, headers=get_http_headers(), proxies=get_tor_proxy())
    soup = BeautifulSoup(response.text, "html.parser")
    member_list = [x.get_text().strip() for x in soup.select("a.user-link")]
    member_list.sort()
    return member_list

def get_web_page(project_soup):
    headline = project_soup.select_one("h3.headline1") # 첫번째 헤드라인
    webpage_list = list(filter(lambda x: x.get_text().strip() == "Web Page", headline.select("a")))
    if len(webpage_list) > 0:
        return webpage_list[0].attrs["href"]
    else:
        return ""


def get_project_sub_info(project_soup):
    # get sidebar column for getting Project Information
    sidebar_column = project_soup.select("div#sidebar-column")
    sidebar_component = sidebar_column[0].select("div.well.no-top-round.no-background.no-border ul.unstyled.no-dot > li")

    project_info = {"createdOn": "", "license": "", "programming_language": "", "developers":"", "topic":""}
    for component in sidebar_component:
        span = component.select_one("span")
        if span:
            title = span.get_text().strip()
        else:
            title = component.contents[0]
    
        value = component.select_one("li")

        # log.warning([title, value])
        if title == "Registered":
            createdOn = datetime.strptime(value.get_text().strip(), "%Y-%m-%d %H:%M").date()
            project_info["createdOn"] = createdOn
        elif title == "Developer Member":
            member_list_component = list(filter(lambda x: x.get_text().strip() == "Member List", value.select("a")))
            member_list_link = member_list_component[0].attrs["href"]
            # member list 페이지로 이동해서 정보를 가져와야 한다 
            member_list = get_member_list(member_list_link)
            project_info["developers"] = ",".join(member_list)
        elif title == "License":
            license_list = [x.get_text().strip() for x in value.select("a")]
            project_info["license"] = ",".join(license_list)
        elif title == "Programming Language":
            # log.warning(value)
            programming_languages = [x.get_text().strip() for x in value.select("a")]
            # log.warning(programming_languages)
            project_info["programming_language"] = ",".join(programming_languages)
        elif title == "Topics":
            topics = [x.get_text().strip() for x in value.select("a")]
            project_info["topic"] = ",".join(topics)

    return project_info

def get_repository(project_url):
    try:
        clone_url = []
        response = requests.get(project_url + 'scm/', headers=get_http_headers(), proxies=get_tor_proxy())
        soup = BeautifulSoup(response.text, 'html.parser')
        repository = soup.select("input.input-xlarge")
        for repository_url in repository:
            repos = json.loads(repository_url.attrs['data-repos'])
            clone_url.append(repos["https"] if repos.get("https") else repos["http"] if repos.get("http") else repos["anon"] if repos.get("anon") else None)
    except Exception as e:
        log.error(e)
        clone_url = None
    return clone_url

def check_vcs_type(clone_url):
    # Construct VCS command.
    # gitroot / svnroot / hg.osdn.com / other(CVS)
    # git -> (git clone) cloningURL name
    # Subversion -> (svn checkout) cloningURL name
    # Mercurial -> (hg clone) cloningURL name
    # CVS -> (cvs -z3 -d) cloningURL 후 modulename 스트링을 replace 시켜줘야함.
    result = []
    for url in clone_url:
        vcsType = ""
        command = ""
        if "gitroot" in url:
            command = "git clone {}".format(url)
            vcsType = "git"
        elif "svnroot" in url:
            command = "svn checkout {}".format(url)
            vcsType = "svn"
        elif "hg.osdn.net" in url:
            command = "hg clone {}".format(url)
            vcsType = "hg"
        else:
            command = "cvs -z3 -d {}".format(url)
            vcsType = "cvs"
            command = command.replace('modulename', url.split(" ")[0].split('/')[-1])
        result.append({
            "vcsType": vcsType,
            "command": command
        })
    return result

def get_project_page(project_url, project_name, current_path):
    os.chdir(current_path)
    project_soup = get_project_soup(project_url)

    if check_source_code(project_soup) == False:
        return False

    if check_release_list(project_soup) == False:
        return False

    # get Project Description (Nullable)

    if project_soup.select_one("div.wiki-compact"):
        project_description = project_soup.select_one("div.wiki-compact").text.strip() 
    else:
        project_description = project_soup.select_one("div#ptop-project-desc p").text.strip()

    project_info = get_project_sub_info(project_soup)
    log.warning(project_info)

    homepage_url = get_web_page(project_soup)

    # get Cloning URL
    clone_url = get_repository(project_url)
    # No available VCS -> Skip
    if any([clone_url is None, len(clone_url)==0]):
        log.error("project doesn't have any repository.")
        return False
    log.warning(clone_url)
    
    #디렉토리명으로 특수문자 안들어가도록 replace
    project_name = re.sub('[\\\\/:*?"<>|]','_',project_name.split('/')[0])

    crawling_info = CrawlingInfo(
        crawlerName="osdn_re",
        projectName=project_name,
        projectUrl=project_url,
        homepageUrl=homepage_url,
        summary=project_description,
        category=project_info["topic"],
        createdOn=project_info["createdOn"],
        programmingLanguage=project_info["programming_language"],
        License=project_info["license"],
        developer=project_info["developers"]
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
    vcs_command = check_vcs_type(clone_url)
    source_page.get_source_code.delay(crawling_info.__dict__, vcs_command, pid, current_path)

    return True