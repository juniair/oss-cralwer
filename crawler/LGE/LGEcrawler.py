# -*- coding: utf-8 -*-

# opensource.lge.com 사이트에서 크롤링해주는 프로그램.
# 카테고리 7와, Model List의 모든 페이지와, Software List의 라이선스와 소스를 받음. 한번에 6개까지 다운로드 가능.
import sys
import urllib.request
import requests
import re, os, time
sys.path.append("..")
from bs4 import BeautifulSoup
from crawler.filechecking import *
#sys.path.append("..")
#from Decompresser import flatten
#from crawler import DataBase_Crawler_DB, CrawlingInfo
from datetime import datetime
#from worker import app

#초기 설정. 나중에 토르 브라우저에 랜덤환경변수로 설정해야한다고 하심.
hdr = {'User_Agent': 'Mozilla/5.0'}
baseURL = 'http://opensource.lge.com'
BaseFolderDirectory = os.path.expanduser("~") + os.sep +"LGE_Crawling"

searchMode = 0
breakedPoint = ""

#카테고리 별 태그.
category_dic = {
    "Mc011": "AV/Car/Security", "Mc014": "Appliances", "Mc024": "Commercial",
    "Mc020": "Computer Product", "Mc001": "Mobile", "Mc005": "TV/Display", "Mc111": "ETC"
}

#URL 초기화 함수.
def initialcategoryURL(pageNum, categoryName):
    categoryURL = '/osList/list?curPage=' + str(pageNum) + '&m=' + categoryName + '&s='
    print("URL 초기화: {}".format(baseURL + categoryURL))
    return baseURL + categoryURL

#lxml로 하려했더니 안되서 일단 html.parser로 작업.
def parsingWebpage(URL):
    WebpageURL = URL
    html = urllib.request.urlopen(WebpageURL).read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

# 텍스트에 포함되어 있는 특수 문자 제거
def cleanText(readData):
    text = re.sub('[\\\\/:*?\"<>|]', '', readData)
    return text

#home경로에 폴더를 만들고 카테고리별로 폴더를 만들어서, URL을 POST로 요청하여 file_name으로 받는 다운로드 함수
#@app.task(autoretry_for=(Exception,))
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
    print("현재 경로는: {}".format(os.getcwd()))

    response = requests.post(url, stream="True")
    opensourceFile = text_file = open(file_name,"wb")
    for chunk in response.iter_content(chunk_size=1024):
        opensourceFile.write(chunk)

    opensourceFile.close()

#화면의 Model List와 Software List중 하나를 긁어옴.
def crawling_list(soup, mode, currentURL):
    global breakedPoint, searchMode
    print("{} List 다운 시작.".format(mode))
    if(mode == "Model"):
        list = soup.find_all(id=re.compile(r'(modelRow([0-9])+)'))      # 각 프로젝트는 id가 modelRow로 시작해서 id 정규식으로 검색.
    elif (mode == "Software"):
        list = soup.find_all(id=re.compile(r'(softwareRow([0-9])+)'))   # 각 프로젝트는 id가 modelRow로 시작해서 id 정규식으로 검색.
    else:
        print("모드 오류!")
        exit()

    crawlerInfo = None

    Sub_category = ""
    Model = ""

    for i in list:
        filePath = []
        #하위 항목 출력
        if i.find(class_='category') is not None:
            Sub_category = i.find(class_='category').text
        if i.find(class_='model-name') is not None:
            Model = i.find(class_='model-name').text
        description = i.find(class_='description').text
        print(">>>>>>\t{} => {} -> {}\t<<<<<<".format(Sub_category, Model, description))

        if searchMode == 1:
            if breakedPoint[0] != description:
                continue

        filePath.append(Sub_category)
        filePath.append(Model)
        filePath.append(description)

        print(filePath)

        # crawlerInfo = CrawlingInfo(
        #     crawlerName="LGEcrawler",
        #     projectName=filePath[1],
        #     summary=filePath[2],
        #     homepageUrl=currentURL,
        #     category=filePath[0],
        #     License="Unknown",
        #     programmingLanguage=None
        # )
        #crawlerInfo.project_db_insert()

        filedown_tagged = i.find_all(class_='filedown')     #라이선스와 소스코드 둘다 filedown이라는 클래스가 담긴 버튼을 통해서 다운 받는다.
        for j in filedown_tagged:
            fileName = j.find('img')['alt']                 #파일명 추출

            if searchMode == "1":
                if breakedPoint[1] != fileName:
                    continue
                else:
                    searchMode = 0

            # onclick의 요소들을 정제하고 linkParam에 담는 과정.
            downloadLink = baseURL + "/fileMgr/download"    #파일을 다운로드할 때, 이 링크와 onclick값들 중 일부를 합쳐서 다운로드 링크를 생성함.
            linkStart = j['onclick'].find("(")

            #filedown태그를 통해서 라이센스와 소스코드 다운링크를 볼 수 있음. onclick으로부터 다운로드 링크를 추출함.
            linkParam = j['onclick'][linkStart + 2:-2].replace("'", "").split(", ")

            for k in linkParam:                             #라이선스인 li와 소스코드인 op의 다운로드 링크 포맷이 달라서 이렇게 만듦.
                k = k.replace(" ", "%")
                if (k == "op"): downloadLink = downloadLink + "Idx"
                downloadLink = downloadLink + "/" + k

            print(downloadLink)
            print("파일명: {}\n".format(fileName))

            try:
                downloadFile(downloadLink, fileName, filePath)
            except:
                print(downloadLink + "에서 오류 발생. 오류 정보 저장")
                writingLog(BaseFolderDirectory, "LGE_Crawling", description, fileName)
                LG_Crawling_Start()

            if(downloadLink[-2:]=="/1"):
                file_dir = "/" + "/".join(map(lambda x: cleanText(x), filePath))
                print(file_dir)
                fileInfo = [file_dir,filePath[2],None]
                #crawlerInfo.project_file_db_insert(fileInfo)

    print("{} List 다운 완료.".format(mode))

def LG_Crawling_Start():
    global breakedPoint, searchMode
    # 중간에 끊겼는지 검사
    print("중간 파일 검사\n")
    breakedPoint = breakcheck(BaseFolderDirectory, "LGE_Crawling")
    if breakedPoint != False:
        searchMode = 1
        print("끊김 파일 있음. 지점: {}\n".format(breakedPoint))
    else:
        print("끊김 파일 없음.\n")
        
    # DataBase_Crawler_DB(
    #     crawlerName="LGEcrawler",
    #     crawlerStatus='1').crawler_db_insert()
        
    for category in category_dic:
        #페이지 1부터 ~ 끝까지 model_list를 긁음.
        currentPageNum = 1
        while(1):
            currentURL = initialcategoryURL(currentPageNum, category)
            #매번 다음 페이지 파싱.
            currentPageSoup = parsingWebpage(currentURL)
            isEndPage = currentPageSoup.select('.list-type-01 #modelTable .categoryView > tr > td')

            if (isEndPage[0].text == "No results"):
                print("다음 카테고리로\n")
                break

            crawling_list(currentPageSoup, "Model", currentURL)                             #모델 리스트 긁기

            #다음 페이지로 넘기는 부분.
            currentPage = currentPageSoup.select('.paginate > span > strong')               #현재 페이지.
            #한 페이지밖에 없는 경우.
            if not currentPage:
                print("1페이지 밖에 없음!")
            else:
                print("현재 페이지: {}\t카테고리: {}".format(currentPage[0].text, category_dic[category]))

            print("다음 페이지로.\n")
            currentPageNum += 1

        currentURL = initialcategoryURL(1, category)
        crawling_list(currentPageSoup, "Software", currentURL)                              #model_list를 다 긁고 난 뒤 software_list를 긁음.

    # DataBase_Crawler_DB(
    #     crawlerName="LGEcrawler",
    #     crawlerStatus='0').crawler_db_insert()

if __name__ == "__main__":
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass

    LG_Crawling_Start()
    #flatten(BaseFolderDirectory)
