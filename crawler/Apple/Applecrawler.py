import urllib.request
import requests
import os, time
from bs4 import BeautifulSoup
from crawler.Decompresser import flatten

BaseFolderDirectory = os.path.expanduser("~") + os.sep + "Apple_Crawling"
baseURL = "https://opensource.apple.com/"

isExist = []

def parsingWebpage(URL):
    WebpageURL = URL
    html = urllib.request.urlopen(WebpageURL).read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def downloadFile(url, file_name, path):
    savePath = BaseFolderDirectory
    os.chdir(savePath)
    for i in path:
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

#버전 하나 (1.5.6 이런 상세버전) 크롤링하는 곳.
def one_versionCrawl(URL, filePath):
    try:
        soup = parsingWebpage(URL)
    except urllib.error.HTTPError:
        print("\t\t\t\t해당 페이지는 웹페이지 오류로 인해 접속이 불가능합니다.")
        return

    for i in soup.select(".project-row"):
        try:
            fileURL = baseURL + i.select_one(".project-downloads > a")['href']
            fileName = i.select_one(".project-name ").text.strip()

        except TypeError: #파일명만 있고 coming soon!이라면서 파일 다운로드 키가 없는 경우가 있음.
            continue

        print("\t\t\t\t" + fileName)
        print("\t\t\t\t" + fileURL)

        if fileName not in isExist:
            isExist.append(fileName)
            print("\t\t\t파일이 없네요")
        else:
            print("\t\t\t파일이 이미 있네요.")
            continue

        downloadFile(fileURL, fileName+".tag.gz", filePath)

#홈페이지에서 버전별로 받는 코드.
def apple_start_crawling():
    soup = parsingWebpage(baseURL)
    for i in soup.find_all(class_="product release-list"):
        filePath = []
        product_name = i.select_one("h3").text
        print("\n제품 명: " + product_name)
        filePath.append(product_name)

        for j in i.select(".release-list-button > span, ul"):
            tagIdentify = j.get('id').split("-")[0]                 #버전과 하위 버전을 구분하기 위한 id 추출.
            count = 0
            if tagIdentify == "list":
                print("\t\t버전 명:", j.text + "\n\t\t▼하위 태그들▼")
                filePath.append(j.text)

            elif tagIdentify == "release":
                count = count + 1
                if count >= 90:                 #한번에 너무 받으면 접속차단되서 잠시 중단
                    print("10초간 휴식(접속차단 방지)")
                    time.sleep(10)

                for k in j.select("li"):
                    versionLink = baseURL + k.a['href']
                    detailversion = k.a.text
                    print("\t\t\t" + detailversion + "\n\t\t\t링크: " + versionLink + "\n")
                    filePath.append(detailversion)
                    one_versionCrawl(versionLink, filePath)
                    del filePath[-1]
                del filePath[-1]
                print("\t\t▲▲▲▲▲▲▲▲")

if __name__ == "__main__":
    try:
        os.mkdir(BaseFolderDirectory)
    except FileExistsError:
        pass
    apple_start_crawling()
    flatten(BaseFolderDirectory)


'''
def apple_start_crawling(URL, path):
    soup = parsingWebpage(URL)

    for i in soup.select('.column'):
        toggle = 0

        fileList = i.select('tr > td > a')
        for j in fileList:
            if (j['href'] in ["./.." ,"./../"]):          #상위 폴더로 이동 생략.
                continue

            if toggle == 0:                     #2개씩 들어가있어서 짝수번째만 작동
                toggle = 1
                continue
            else:
                toggle = 0
                pass

            URL = baseURL
            for k in path:
                URL = URL + k

            filename = j.text
            print("파일이름: ", filename)

            path.append(filename)
            URL = URL + filename


            print("URL: ", URL)
            print(path)

            if filename[-7:-1] == ".tar.g":
                print("아무튼 다운로드함\n")
                #downloadFile(URL, filename)
                del path[-1]

            if j is fileList[-1]:
                del path[-1]
                apple_start_crawling(URL, path)

            else:
                apple_start_crawling(URL, path)
'''