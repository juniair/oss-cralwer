import urllib.request
import requests
from bs4 import BeautifulSoup


baseURL = "http://joomlacode.org"
projectLink = ""
finalL = 0
finalP = 0

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

def projectDownload(URL):
    soup = parsingWebpage(URL)



def proejectScrapping(URL):
    global finalL
    global finalP
    soup = parsingWebpage(URL)
    for i in soup.select(".tabular > .d > td > ul"):
        infoList = i.text.split("\n")
        for j in infoList:
            try:
                if j[0] == "L":
                    print("=====\n라이선스: ", j[9:])
                    if j is soup.select(".tabular > .d > td > ul")[-1]:
                        finalL+=1

                elif j[0] == "P":
                    print("프로그래밍 언어 ", j[22:] + "\n")
                    if j is soup.select(".tabular > .d > td > ul")[-1]:
                        finalP+=1
            except IndexError:
                pass
    for i in soup.select(".menuitem.regular"):
        if(i.text == "Releases"):
            projectDownload(baseURL + i['href'])

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
    print("마지막에 있던 횟수\n L: {} P: {]".format(finalL, finalP))

if __name__ == "__main__":
    '''
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass
    '''
    joomla_crawling_start()
    #flatten(BaseFolderDirectory)