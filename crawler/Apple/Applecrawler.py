# -*- coding: utf-8 -*-


import urllib.request
import requests
import os
import re
import time
import sys
sys.path.append("..")
from bs4 import BeautifulSoup
from filechecking import *
from Decompresser import flatten
from crawler import DataBase_Crawler_DB, CrawlingInfo

BaseFolderDirectory = os.path.expanduser("~") + os.sep + "Apple_Crawling"
baseURL = "https://opensource.apple.com"
isExist = []

searchMode = 0
breakedPoint = ""

def parsingWebpage(URL):
    WebpageURL = URL
    html = urllib.request.urlopen(WebpageURL).read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def cleanText(readData):
    text = re.sub('[\\\\/:*?\"<>|]', '', readData)
    return text

def downloadFile(url, file_name, path):
    savePath = BaseFolderDirectory
    os.chdir(savePath)
    for i in path:
        i = cleanText(i)
        try:
            os.mkdir(i)
        except FileExistsError:
            pass
        savePath = savePath + os.sep + i
        os.chdir(savePath)
    print("\t\t\t\t현재 경로는: {}".format(os.getcwd()))

    with open(file_name, "wb") as file:
        response = requests.get(url)
        file.write(response.content)

# 버전 하나 (1.5.6 이런 상세버전) 크롤링하는 곳.
def one_versionCrawl(URL, filePath, crawlerInfo):
    global searchMode, breakedPoint

    try:
        soup = parsingWebpage(URL)
    except urllib.error.HTTPError:
        print("\t\t\t\t해당 페이지는 웹페이지 오류로 인해 접속이 불가능합니다.")
        return

    for i in soup.select(".project-row"):
        try:
            fileName = i.select_one(".project-name ").text.strip()
            fileURL = baseURL + i.select_one(".project-downloads>a")['href']

        except TypeError:  # 파일명만 있고 coming soon!이라면서 파일 다운로드 키가 없는 경우가 있음.
            continue

        if searchMode == "1":
            if breakedPoint[1] != fileName:
                continue
            else:
                searchMode = 0

        print("\t\t\t\t" + fileName)
        print("\t\t\t\t" + fileURL)

    # #프로젝트별 중복되는 프로젝트가 많아서 만든 중복 확인 기능.
    # if fileName not in isExist:
    #     isExist.append(fileName)
    #     print("\t\t\t파일이 없네요")
    # else:
    #     print("\t\t\t파일이 이미 있네요.")
    #     continue

        try:
            downloadFile(fileURL, fileName+".tar.gz", filePath)
        except:
            writingLog(BaseFolderDirectory, "Apple_Crawling", filePath[2], fileName)

        file_dir = "/" + "/".join(map(lambda x: cleanText(x), filePath))
        fileInfo = [file_dir, fileName.split("-")[-1], None]
        crawlerInfo.project_file_db_insert(fileInfo)

# 홈페이지에서 버전별로 받는 코드.
def apple_start_crawling():
    global breakedPoint, searchMode
    # 중간에 끊겼는지 검사
    print("중간 파일 검사\n")
    breakedPoint = breakcheck(BaseFolderDirectory, "Apple_Crawling")
    if breakedPoint != False:
        global searchMode
        searchMode = 1
        print("끊김 파일 있음. 지점: {}\n".format(breakedPoint))
    else:
        print("끊김 파일 없음.\n")

    DataBase_Crawler_DB(  # 크롤링 시작
        crawlerName="Applecrawler",
        crawlerStatus='1').crawler_db_insert()

    soup = parsingWebpage(baseURL)
    for i in soup.find_all(class_="product release-list"):
        filePath = []
        product_name = i.select_one("h3").text
        print("\n제품명: " + product_name)
        filePath.append(product_name)

        for j in i.select(".release-list-button > span, ul"):
            # 버전과 하위 버전을 구분하기 위한 id 추출.
            tagIdentify = j.get('id').split("-")[0]

            if tagIdentify == "list":
                print("\t\t버전 명:", j.text + "\n\t\t▼하위 태그들▼")
                filePath.append(j.text)
                count = 0

            elif tagIdentify == "release":
                count += 1
                if count >= 90:
                    print("5초간 휴식(접속 차단 방지)")
                    time.sleep(5)
                    count = 0

                for k in j.select("li"):
                    versionLink = baseURL + k.a['href']
                    detailversion = k.a.text
                    if searchMode == 1:
                        if breakedPoint[0] != detailversion:
                            continue

                    print("\t\t\t" + detailversion + "\n\t\t\t링크: " + versionLink + "\n")
                    filePath.append(detailversion)
                    crawlerInfo = CrawlingInfo(
                        crawlerName="Applecrawler",
                        projectName=detailversion,
                        homepageUrl=versionLink,
                        developer="Apple Inc.",
                        category=product_name,
                        License="Unknown",
                        programmingLanguage=None
                    )
                    crawlerInfo.project_db_insert()

                    one_versionCrawl(versionLink, filePath, crawlerInfo)

                    del filePath[-1]
                del filePath[-1]
                print("\t\t▲▲▲▲▲▲▲▲")

    DataBase_Crawler_DB(  # 크롤링 종료
        crawlerName="Applecrawler",
        crawlerStatus='0').crawler_db_insert()


if __name__ == "__main__":
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass
    apple_start_crawling()
    flatten(BaseFolderDirectory)
