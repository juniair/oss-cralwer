import urllib.request
import requests
from bs4 import BeautifulSoup

baseURL = "http://joomlacode.org"
projectLink = ""

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

#다운로드 할 파일이 있는지 검출해주는 함수
def proejctDetect(soup):
    packageDetect = lambda x: x == 'No Packages Were Found'
    availableFileDetect = lambda x: x[-41:] == 'No available files found for this package'

    for i in soup.select(".main"):
        #print(i)
        if (i.text.strip()[:7] == "Unknown"):
            print("\t\t\t\t====>파일 메뉴가 없네요.<====\t\t\t\t")
            return False
        else:
            MenuList = i.text.split("\n")
            print(MenuList)

        if (True in list(map(packageDetect, MenuList))):
            print(list(map(packageDetect, MenuList)))
            print("\t\t\t\t====>발견된 패키지가 없어요.<====\t\t\t\t")
            return False
        elif (True in list(map(availableFileDetect, MenuList))):
            print(list(map(availableFileDetect, MenuList)))
            print("\t\t\t\t====>다운로드할 파일이 없어요.<====\t\t\t\t")
            return False
    return True

def projectDownload(URL):
    soup = parsingWebpage(URL)

    #파일에 문제 있는 것들 걸러내기
    if proejctDetect(soup) is False:
        print("반출!!")
        return

    


def proejectScrapping(URL):
    soup = parsingWebpage(URL)
    for i in soup.select(".tabular > .d > td > ul"):
        infoList = i.text.split("\n")
        for j in infoList:
            try:
                if j[0] == "L":
                    print("=====\n라이선스: ", j[9:])

                elif j[0] == "P":
                    print("프로그래밍 언어 ", j[22:] + "\n")

            except IndexError:
                pass
    projectDownload(URL + "frs")

def one_page_crawling(soup):
    count = 0
    for i in soup.find_all("td", {"valign": "middle"}):
        if count % 3 ==0:
            projectLink = baseURL + i.find("a").attrs['href']
            print(projectLink)
            print("프로젝트명: ", i.text)
        elif count % 3 == 1:
            print("업로더: ", i.text)
        elif count % 3 == 2:
            print("설명: ", i.text, "\n")
            proejectScrapping(projectLink)
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
    '''
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass
    '''
    joomla_crawling_start()
    #flatten(BaseFolderDirectory)