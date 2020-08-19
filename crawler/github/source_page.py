#-*- coding: utf-8 -*-

import os
import re
import io
import sys
import json
import platform
import tarfile
import zipfile
import requests
import shutil
from bs4 import BeautifulSoup

from worker import app
from logger import getLogger, write_progress_log
from crawler import DataBase_Crawler_DB, CrawlingInfo
import VCSDownloader, GetRepoInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = BASE_DIR + "/../../data"  # 절대경로 값으로 설정을 해야 하는데...
download_path = data_path + "/githubDir" # sourceforge 프로젝트 다운로드 경로

log = getLogger(filename="github_crawler.log")

@app.task(autoretry_for=(Exception,))
def get_source_code(item, remote_repo_revision,  pid, current_path, current_status):
    log.debug(item)

    result = git_clone(item, remote_repo_revision, pid, current_path, current_status)
    rename_directory(item["name"], pid)
    return result

def rename_directory(projectName, pid):
    org_path = os.getcwd()
    os.chdir(download_path)
    log.debug("rename_directory: current directory="+download_path+"/"+projectName)
    try:
        newdirname = str(pid)
        log.debug("Rename " + projectName + " > " + newdirname)
        if os.path.exists(projectName):
            if os.path.isdir(newdirname):
                shutil.rmtree(newdirname)
            os.rename(projectName, newdirname)
    except Exception as e:
        log.error(str(e))
    os.chdir(org_path)

def git_clone(item, remote_repo_revision, pid, current_path, current_status):
    crawlingInfo = CrawlingInfo(
        crawlerName="github_re",
        projectName=item["name"] if item.get("name") else "UnKnown",
        projectUrl=item["html_url"] if item.get("html_url") else "",
        summary=item["description"] if item.get("description") else "",
        homepageUrl=item["homepage"] if item.get("homepage") else "",
        createdOn="",
        programmingLanguage=item["language"] if item.get("language") else "",
        License=item["license"]["name"] if item["license"].get("name") else ""
    )

    file_dir = data_path + ("\\githubDir\\" if platform.system() == "Windows" else "/githubDir/")
    command = "git clone {0} {1}".format(item["clone_url"], crawlingInfo.projectName + '_' + str(item['id']))

    downcnt = 0
    while downcnt < len(remote_repo_revision):
        log.debug("change project directory :"+current_path)
        os.chdir(current_path)

        if remote_repo_revision[downcnt + 1].startswith('refs/tags/'):
            temp = remote_repo_revision[downcnt + 1].split("/")
            revision = "_".join(temp[2:len(temp)])
        else:
            revision = remote_repo_revision[downcnt + 1].split("/")[-1]

        # 특수문자 replace
        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
        rel_createdOn = ""
        log.debug("change revision directory :"+revision)
        try:
            os.chdir(revision)
        except:
            os.mkdir(revision)
            os.chdir(revision)

        downresult = 0
        try:
            log.warning('[crawler_github] found {0} project. trying to cloning/pull...'.format(item['name']))
            downresult = VCSDownloader.download(command)
            log.warning('[crawler_github] complete download {0}'.format(item['name'].replace(' ', '-')))
        except Exception as e:
            log.error(str(e))

        if downresult >= 1:
            # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
            try:
                rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision, revision, downcnt)
            except Exception as e:
                log.error(str(e))
                pass

        fileInfo = [file_dir, revision, rel_createdOn]
        crawlingInfo.project_file_db_insert(fileInfo)
        downcnt += 2
    
    return True