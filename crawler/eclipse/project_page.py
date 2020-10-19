# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

from worker.eclipse import app
from crawler import CrawlingInfo
from common import getenv, get_http_headers, get_tor_proxy
from eclipse import source_page

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = getenv("DOWNLOAD_PATH")  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/eclipseDir" # sourceforge 프로젝트 다운로드 경로

@app.task(autoreply_for=(Exception,))
def get_project_info(project_name, project_url, current_path):
    # last Page search
    result = get_project_page(project_name, project_url, current_path)
    return result

def get_project_soup(project_url):
    project_url = "https://projects.eclipse.org{}".format(project_url)
    log.warning(project_url)
    response = requests.get(project_url, headers=get_http_headers(), proxies=get_tor_proxy())
    soup = BeautifulSoup(response.text, "html.parser")
    return soup

def get_governance_soup(project_url):
    governance_url = "https://projects.eclipse.org{}/governance".format(project_url)
    log.warning(governance_url)
    response = requests.get(governance_url, headers=get_http_headers(), proxies=get_tor_proxy())

    soup = BeautifulSoup(response.text, "html.parser")
    return soup

def get_created_date(project_url):
    governance_soup = get_governance_soup(project_url)
    release_list = governance_soup.select("div.field-name-field-releases tr")
    if release_list:
        first_release_row = release_list[-1]
        first_release_date = first_release_row.select("td")[-1].get_text().strip()
        createdOn = datetime.strptime(first_release_date, "%Y-%m-%d").date()
    else:
        createdOn = ""
    return createdOn

def get_developers(project_url):
    who_url = "https://projects.eclipse.org{}/who".format(project_url)
    log.warning(who_url)
    response = requests.get(who_url, headers=get_http_headers(), proxies=get_tor_proxy())
    soup = BeautifulSoup(response.text, "html.parser")
    
    member_list = soup.select("li.projects-members-list-item")
    # developers
    developers = list(set(map(lambda x: x.attrs['sort'], member_list)))
    developers.sort()
    return ', '.join(developers)

def get_repositories(project_url):
    developer_url = "https://projects.eclipse.org{}/developer".format(project_url)
    log.warning(developer_url)
    response = requests.get(developer_url, headers=get_http_headers(), proxies=get_tor_proxy())

    soup = BeautifulSoup(response.text, "html.parser")

    projects_repository = soup.select("div.projects-repository")

    links = list(map(
        lambda x: {x.select_one("div.projects-repository-title").get_text().strip() : x.select_one("span.clone-repo-url").get_text().strip()},
        projects_repository
    ))

    return {k:v for x in links for k,v in x.items()}

def get_project_page(project_name, project_url, current_path):
    os.chdir(current_path)
    
    project_info = {"project_name":project_name}
    project_soup = get_project_soup(project_url)

    # category
    try:
        category = project_soup.select_one("ol.breadcrumb li.active").get_text().strip()
    except Exception as e:
        log.error("error to get category info...")
        log.error(e)
        category = ""
    project_info["category"] = category
    # summary       
    try:
        summary = project_soup.select("div.field-type-text-with-summary p")[0].get_text().strip()
    except Exception as e:
        log.error("error to get summary info...")
        log.error(e)
        summary = ""
    project_info["summary"] = summary
# License
    try:
        license = project_soup.select_one("div.field-name-field-project-licenses a.node-reference-hierarchy-0").get_text()
        # License = project_soup.findAll("div", {"class": "field-name-field-project-licenses"})[
        # 0].findAll("a", {"class": "node-reference-hierarchy-0"})
        # License = str(License).split('>')[1].split('<')[0]
    except Exception as e:
        log.error("error to get license info...")
        log.error(e)
        license = "UnKnown"
    project_info['license'] = license
    
    try:
        project_block_items = project_soup.select("section#block-project-blocks-dynamic-project-links ul.nav li a")
        homepage_url_obj = list(filter(lambda x: x.get_text().strip() == "Website", filter(lambda x: getattr(x, "text", False), project_block_items)))
        # homepageUrl
        homepage_url = homepage_url_obj[0].attrs["href"] if len(homepage_url_obj) > 0 else ""
    except Exception as e:
        log.error("error to get homepage_url info...")
        log.error(e)
        homepage_url = ""
    project_info['homepage_url'] = homepage_url

    # createdOn
    try:
        createdOn = get_created_date(project_url)
    except Exception as e:
        log.error("error to get createdOn info...")
        log.error(e)
        createdOn = ""
    project_info['createdOn'] = createdOn
    
    try:
        developer = get_developers(project_url)
    except Exception as e:
        log.error("error to get developer info...")
        log.error(e)
        developer = ""
    project_info['developer'] = developer

    # programmingLanguage
    programming_language = ["Java"]
    project_info['programming_language'] = programming_language

    try:
        repositories = get_repositories(project_url)
    except Exception as e:
        log.error("")
        log.error(e)
        repositories = ""
    
    if repositories == None or len(repositories) == 0:
        log.error("Project has no repositories. : {}".format(project_name))
        return False
    
    project_info["repositories"] = repositories
    # log.warning(project_info)

    crawling_info = CrawlingInfo(
        crawlerName="eclipse_re",
        projectName=project_info["project_name"],
        projectUrl="https://projects.eclipse.org{}".format(project_url),
        category=project_info['category'],
        summary=project_info['summary'],
        homepageUrl=project_info['homepage_url'],
        createdOn=project_info['createdOn'],
        developer=project_info['developer'],
        programmingLanguage=programming_language,
        License=project_info['license']
    )
    try:
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
        # source_page.get_source_code(crawling_info.__dict__, repositories, pid, current_path)
        source_page.get_source_code.delay(crawling_info.__dict__, repositories, pid, current_path)
    except Exception as e:
        log.error(e)

    return True


