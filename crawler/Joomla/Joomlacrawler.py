# -*- coding: utf-8 -*-

import urllib.request
import requests, os, re
from bs4 import BeautifulSoup

BaseFolderDirectory = os.path.expanduser("~") + os.sep + "Joomla_Crawling"
baseURL = "http://joomlacode.org"
projectLink = ""
filePath = []

#URL 초기화 함수.
def initialcategoryURL(pageNum):
    NumPage = baseURL + "/gf/project/?action=&_project_total=50&_project_page=" + str(pageNum)
    print("URL 초기화: {}".format(NumPage))
    return NumPage

def parsingWebpage(URL):
    WebpageURL = URL
    html = urllib.request.urlopen(WebpageURL).read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

# 텍스트에 포함되어 있는 특수 문자 제거
def cleanText(readData):
    text = re.sub('[+,#/\?:^$@*\"※~&%ㆍ\\‘|\(\)\[\]\<\>`\'…》]', '', readData)
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

    with open(file_name, "wb") as file:
        response = requests.get(url)
        file.write(response.content)

#다운로드 할 파일이 있는지 검출해주는 함수
def proejctDetect(soup):
    packageDetect = lambda x: x == 'No Packages Were Found'
    availableFileDetect = lambda x: x[-41:] == 'No available files found for this package'

    for i in soup.select(".main"):
        if (i.text.strip()[:7] == "Unknown"):
            print("\t\t\t\t=========>파일 메뉴가 없네요.")
            return False
        else:
            MenuList = i.text.split("\n")

        if (True in list(map(packageDetect, MenuList))):
            print(list(map(packageDetect, MenuList)))
            print("\t\t\t\t=========>발견된 패키지가 없어요.")
            return False
        elif (True in list(map(availableFileDetect, MenuList))):
            print(list(map(availableFileDetect, MenuList)))
            print("\t\t\t\t=========>다운로드할 파일이 없어요.")
            return False
    return True

def projectDownload(URL):
    global filePath
    soup = parsingWebpage(URL)

    #파일에 문제 있는 것들 걸러내기
    if proejctDetect(soup) is False:
        print("반출!!")
        #아무것도 받지 않은 프로젝트는 폴더 생성하지 않기
        filePath = []
        print("경로 초기화!")
        return

    #여기다 파일 식별하고 다운받는 코드 작성.
    toggle = sec_toggle = 0
    releaseList = []

    packageDetect = soup.select(".tabular > .l > td, .tabular > .d > td")

    for i in packageDetect:
        # 패키지하고 최신파일 출력
        try:
            if(i['rowspan'] is not None):
                if toggle == 0:
                    #패키지 폴더 생성을 위한 배열 추가.
                    packageName = i.text.strip()
                    filePath.append(packageName)
                    print("\n\t패키지명: " + packageName)

                    toggle = 1
                    rowspan = int(i['rowspan'])
                    print("\t" + baseURL + i.a['href'])
                    fileList = parsingWebpage(baseURL + i.a['href']).select(".tabular > .l > td, .tabular > .d > td")
                    
                else:
                    releaseList.append(i.text)
                    rowspan -= int(i['rowspan'])
                    if (rowspan == 0):
                        print("\t최근 릴리즈: " + ', '.join(releaseList))
                        toggle = 0
                        releaseList=[]

                        # 패키지에 있는 여러 버전들 스크래핑, 다운로드
                        for j in fileList:
                            try:
                                if (j['rowspan'] is not None):
                                    if sec_toggle == 0:
                                        if j != fileList[0]:
                                            del filePath[-1]

                                        releaseName = j.a.text.strip()
                                        filePath.append(releaseName)
                                        print("\t\t릴리즈명: " + releaseName)
                                        sec_toggle = 1
                                        fileParam = 0

                                    else:
                                        print("\t\t릴리즈 날짜: " + j.text + "\n")
                                        sec_toggle = 0

                            # 파일들이 있는 곳.
                            except(KeyError):
                                fileParam += 1
                                if (fileParam % 3 == 1):
                                    # 파일명하고 다운로드 링크 추출
                                    fileName = j.text
                                    fileURL = baseURL + j.a['href']

                                    print("\t\t\t파일명: " + fileName)
                                    print("\t\t\t" + fileURL + "\n")

                                    print("경로: " + " => ".join(filePath) + "\n")
                                    #downloadFile(fileURL, fileName, filePath)
                            if(j==fileList[-1]):
                                del filePath[-1]
                        del filePath[-1]


        except(KeyError):
            pass

def proejectScrapping(URL):
    soup = parsingWebpage(URL)
    for i in soup.select(".tabular > .d > td > ul"):
        infoList = i.text.split("\n")
        for j in infoList:
            try:
                if j[0] == "L":
                    print("=====\n라이선스: ", j[9:])

                elif j[0] == "P":
                    print("프로그래밍 언어 ", j[22:] + "\n-----------------------------------------------")

            except IndexError:
                pass
    projectDownload(URL + "frs")

def one_page_crawling(soup):
    global filePath
    count = 0
    for i in soup.find_all("td", {"valign": "middle"}):
        if count % 3 ==0:
            projectLink = baseURL + i.find("a").attrs['href']
            print("▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒\n"+projectLink)

            #프로젝트 폴더 생성을 위한 추가.
            projectName = i.text.strip()
            filePath.append(projectName)
            print("프로젝트명: ", projectName)
        elif count % 3 == 1:
            print("업로더: ", i.text)
        elif count % 3 == 2:
            print("설명: ", i.text, "\n")
            proejectScrapping(projectLink)
            filePath = []

        count = count + 1

def joomla_crawling_start():
    currentPageNum = 1
    while (1):
        # 매번 다음 페이지 파싱.
        currentPageSoup = parsingWebpage(initialcategoryURL(currentPageNum))

        one_page_crawling(currentPageSoup)

        # 다음 페이지로 넘기는 부분.
        currentPage = currentPageSoup.select('.paginator > strong')[1].text  # 현재 페이지.
        if currentPage[0] == " ":
            print("\n크롤링 종료")
            return

        print("현재 페이지: {}".format(currentPage))
        print("다음 페이지로.\n")
        currentPageNum += 1

if __name__ == "__main__":
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass
    joomla_crawling_start()
    flatten(BaseFolderDirectory)