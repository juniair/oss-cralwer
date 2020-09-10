from celery import Celery
import urllib.request
import requests #위에꺼랑 다름..
import re
from bs4 import BeautifulSoup

#초기 설정. 나중에 토르 브라우저에 랜덤환경변수로 설정해야한다고 하심.
hdr = {'User_Agent': 'Mozilla/5.0'}
baseURL = 'http://opensource.lge.com'

#카테고리 별로 돌릴 URL. 아직 적용 안함.
category_list = ["Mc011", "Mc014", "Mc024", "Mc020", "Mc001", "Mc005", "Mc111"]

#URL 초기화 함수.
def initialcategoryURL(pageNum=1, categoryName=category_list[0]):
    categoryURL = '/osList/list?curPage=' + str(pageNum) + '&m=' + categoryName + '&s='
    print("URL 초기화: ", baseURL + categoryURL)
    return baseURL + categoryURL

#lxml로 하려했더니 안되서 일단 html.parser로 작업.
def parsingWebpage(URL):
    WebpageURL = URL
    req = urllib.request.Request(WebpageURL, headers=hdr)
    html = urllib.request.urlopen(WebpageURL).read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

#URL을 POST로 요청하여 file_name으로 받는 다운로드 함수
def downloadFile(url, file_name):
    with open(file_name, "wb") as file:     
        response = requests.post(url)
        file.write(response.content)

URL = "http://opensource.lge.com/fileMgr/download/li/GC-B569BLCF/509519"
downloadFile(URL, "down_TEST.html")

#화면의 Model List와 Software List중 하나를 긁어옴.
def crawling_list(soup, mode):
    print(mode + " List 다운 시작.")
    if(mode == "Model"):
        list = soup.find_all(id=re.compile(r'(modelRow([0-9])+)'))      # 각 프로젝트는 id가 modelRow로 시작해서 id 정규식으로 검색.
    elif (mode == "Software"):
        list = soup.find_all(id=re.compile(r'(softwareRow([0-9])+)'))   # 각 프로젝트는 id가 modelRow로 시작해서 id 정규식으로 검색.
    else:
        print("모드 오류!")
        exit()

    for i in list:
        filedown_tagged = i.find_all(class_='filedown')     #라이선스와 소스코드 둘다 filedown이라는 클래스가 담긴 버튼을 통해서 다운 받는다.

        for j in filedown_tagged:
            fileName = j.find('img')['alt']                 #파일명 추출

            # onclick의 요소들을 정제하고 linkParam에 담는 과정.
            downloadLink = baseURL + "/fileMgr/download"    # 파일을 다운로드할 때, 이 링크와 onclick값들 중 일부를 합쳐서 다운로드 링크를 생성함.
            linkStart = j['onclick'].find("(")

            #filedown태그를 통해서 라이센스와 소스코드 다운링크를 볼 수 있음. onclick으로부터 다운로드 링크를 추출함.
            linkParam = j['onclick'][linkStart + 2:-2].replace("'", "").split(", ")
            print(linkParam)                                #잘 들어갔는 지 검사용.
            for k in linkParam:                             #라이선스인 li와 소스코드인 op의 다운로드 링크 포맷이 달라서 이렇게 만듦.
                k = k.replace(" ", "%")
                if (k == "op"): downloadLink = downloadLink + "Idx"
                downloadLink = downloadLink + "/" + k
            print(downloadLink)
            print("파일명: " + fileName + "\n")
            #downloadFile(downloadLink, fileName)            #시스템 구축 안하고 돌리면 LG오픈소스 사이트에서 차단 먹이는 코드.
    print(mode + " List 다운 완료.")

def LG_Crawling_Start():
    for category in category_list:
        #페이지 1부터 ~ 끝까지 model_list를 긁음.
        currentPageNum = 1
        while(1):
            #매번 다음 페이지 파싱.
            currentPageSoup = parsingWebpage(initialcategoryURL(currentPageNum, category))
            isEndPage = currentPage = currentPageSoup.select('.list-type-01 #modelTable .categoryView > tr > td')

            if (isEndPage[0].text == "No results"):
                print("다음 카테고리로!\n")
                break

            crawling_list(currentPageSoup, "Model")                                #모델 리스트 긁기

            #다음 페이지로 넘기는 부분.
            currentPage = currentPageSoup.select('.paginate > span > strong')   #현재 페이지.
            #한 페이지밖에 없는 경우.
            if not currentPage:
                print("1페이지 밖에 없음!")
            else:
                print("현재 페이지: " + currentPage[0].text + " 카테고리: " + category)

            print("다음 페이지로.\n")
            currentPageNum += 1

        #model_list를 다 긁고 난 뒤 software_list를 긁음.
        crawling_list(currentPageSoup, "Software")

LG_Crawling_Start()