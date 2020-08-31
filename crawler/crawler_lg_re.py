import io
import platform
import re
import shutil
import tarfile
import zipfile

from bs4 import BeautifulSoup
import atexit
from signal import *

from .crawler import *
from . import URLDownloader
from . import project_tasks, download_tasks

class LGCrawler(Crawler):
    def __init__(self):
        for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
            signal(sig, self.handler)

        super(LGCrawler, self).__init__(name="LG")
        # 마지막 수행정보를 저장하기 위한 변수들
        self.LAST_SEARCH_CATEGORY = "AV/Car/Security"  # default value, 1st category.
        self.LAST_SEARCH_PAGE = 0
        self.LAST_PROJECT_NUMBER = 0
        self.item = 0
        self.ver = 0
        self.pid = ""
        self.PROGRESS_LOG_FILENAME = self.initialpath + "/progress_{}.json".format(self.name)

    def handler(self, signum, frame):
        DataBase_Crawler_DB(
            crawlerName="LG_re",
            crawlerStatus='0').crawler_db_insert()
        sys.exit(0)

    # atexit.register(handler)
    def write_progress_log(self, category="AV/Car/Security", page='0', number='0'):
        with open(self.PROGRESS_LOG_FILENAME, 'w') as fp:
            json.dump({
                'LAST_SEARCH_CATEGORY': category,
                'LAST_SEARCH_PAGE': page,
                'LAST_PROJECT_NUMBER': number
            }, fp)

    def read_progress_log(self):
        with open(self.PROGRESS_LOG_FILENAME, 'r') as self.progress:
            lastprogress = json.load(self.progress)
            self.LAST_SEARCH_CATEGORY = lastprogress['LAST_SEARCH_CATEGORY']
            self.LAST_SEARCH_PAGE = lastprogress['LAST_SEARCH_PAGE']
            self.LAST_PROJECT_NUMBER = lastprogress['LAST_PROJECT_NUMBER']

    def preCrawling(self):
        try:
            self.read_progress_log()
        except FileNotFoundError:
            self.write_progress_log()

    def crawlingAction(self):
        initialPath = os.getcwd()

        # LG 카테고리 크롤링에 사용할 전체 카테고리 7개)
        category_list = ["AV/Car/Security", "Appliances", "Commercial",
                         "Computer Product", "Mobile", "TV/Display", "ETC"]

        try:
            DataBase_Crawler_DB(
                crawlerName="LG_re",
                crawlerStatus='1').crawler_db_insert()
            for LGCategory in category_list:
                # 이미 탐색한 카테고리가 있으면 스킵.
                index = category_list.index(LGCategory)
                compareIndex = category_list.index(self.LAST_SEARCH_CATEGORY.strip())
                if compareIndex is not None and index < compareIndex:
                    continue
                self.LAST_SEARCH_CATEGORY = LGCategory

                # 카테고리 크롤링 개시
                self.category_crawling(LGCategory, initialPath)
        except requests.ConnectionError as e:
            self.log.error(e)

        self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

        DataBase_Crawler_DB(
            crawlerName="LG_re",
            crawlerStatus='0').crawler_db_insert()
        # 정상 종료되면 프로그레스 초기화.
        self.LAST_SEARCH_CATEGORY = "AV/Car/Security"
        self.LAST_SEARCH_PAGE = 0
        self.LAST_PROJECT_NUMBER = 0

    def category_crawling(self, category, initialPath):
        # 이전 수행 페이지가 있는 경우 해당 값을 가져옴.
        if int(self.LAST_SEARCH_PAGE) == 0:
            page = 1
        else:
            page = int(self.LAST_SEARCH_PAGE)

        # page limit = 999
        PAGE_SEARCH_LIMIT = 999

        url = "http://opensource.lge.com/osList/list?curPage=" + page + "&m=" + category + "&s="

        # 페이지 1부터 PAGE_SEARCH_LIMIT까지 스크래핑.
        while page <= PAGE_SEARCH_LIMIT:
            self.LAST_SEARCH_PAGE = page
            result = self.crawling_onepage(url + str(page), initialPath)

            # Category Find Terminate Condition check.
            if result == 0:
                break
            page += 1

            self.write_progress_log(self.LAST_SEARCH_CATEGORY, page, self.LAST_PROJECT_NUMBER)

        self.LAST_SEARCH_PAGE = 0
        self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

    # index 페이지를 기준으로 최대 25건의 데이터를 크롤링 하고 프로젝트 다운로드.
    # 1이면 정상종료, 0이면 비정상종료 (404, No Result)
    def crawling_onepage(self, url, initialPath):
        response = requests.get(url)

        # 404 Not Found
        if response.status_code == 404:
            return 0

        soup = BeautifulSoup(response.text, 'lxml')  # 성능 향상을 위해 lxml 파서 사용.

        # HTTP OK(200)이지만 내용이 없는 경우(No results found) 종료
        checkNoResult = soup.find('section', {'class': "list-type-01"})

        if checkNoResult is None:
            raise requests.ConnectionError

        """!!!!!!수정해야함!!!!!!"""
        result = checkNoResult.find('section', {'class': ""})
        """!!!!!!수정해야함!!!!!!"""
        if result is not None and "No results found" in result.text:
            return 0

        # 프로젝트 리스트 탐색
        prev_index = int(self.LAST_PROJECT_NUMBER)
        current_index = 0
        classList = soup.findAll('div', {'class': ""})
        for classItem in classList:
            hrefList = classItem.findAll('a')
            for href in hrefList:
                current_index += 1
                # 기탐색된 프로젝트 스킵
                if current_index < prev_index:
                    # self.LAST_PROJECT_NUMBER = (int(self.LAST_PROJECT_NUMBER) % 25) + 1
                    continue
                self.LAST_PROJECT_NUMBER = (int(self.LAST_PROJECT_NUMBER) % 25) + 1
                # 프로젝트 기본정보 취득
                href_value = href.get('href')
                # self.printdetail(href_value, initialPath)
                project_tasks.get_project_info_from_sourceforge.delay(href_value, initialPath)

                print("---------------------------------------------------------------")

        self.LAST_PROJECT_NUMBER = 0
        return 1

    # 프로젝트 정보 출력.
    # Files 탭이 존재하면 탐색하여 다운로드를 시도.
    # code 탭이 존재하면 탐색하여 다운로드를 시도.
    def printdetail(self, href_value, initialPath):
        os.chdir(initialPath)

        crawlerInfo = None

        infoAddress = "http://opensource.lge.com/" + href_value  # href.get('href')
        URLHash = md5hasher.hashing(infoAddress)
        response = requests.get(infoAddress)
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        """!!!!!!수정해야함!!!!!!"""
        status = soup.find('div', {'class': ""})
        """!!!!!!수정해야함!!!!!!"""

        # status가 존재하면 Realease가 아닌 것으로 판단. Realease가 아니면 볼 필요 없으니 종료.
        if status is not None:
            print("Project Status is not None.")
            return 0

        projectUrl = infoAddress
        # print("Project URL Hash : " + URLHash)

        # 프로젝트 이름
        className = soup.findAll('div', {'class': "title"})
        for Class in className:
            Name = Class.find('h1')
            projectName = Name.get_text()
            # 프로젝트 이름 특수문자 replace
            projectName = re.sub('[\\\\/:*?"<>|]', '_', projectName)

        # 홈페이지
        homepage = soup.find('a', {'id': "homepage"})
        if homepage is not None:
            homepageURL = homepage['href']

        # 설명 (없을수도 있음)
        description = soup.find('p', {'class': "description"})
        description_result = ""
        if description is not None:
            description_result = description.text.rstrip()
        summary = description_result

        # 라이센스 (없을수도 있음)
        license = ""
        pspSection = soup.findAll('section', {'class': "row psp-section"})
        if pspSection is not None:
            for sections in pspSection:
                section = sections.findAll('section', {'class': "project-info"})
                for fields in section:
                    licenseList = fields.findAll('a')
                    for licenseElement in licenseList:
                        license = license + licenseElement.text + ','
                    license = license[0:-1]
        License = license

        # 등록일
        classRegistered = soup.findAll('section', {'class': "project-info"})
        for Registered in classRegistered:
            RegisteredList = Registered.findAll('section', {'class': "content"})
            for Register in RegisteredList:
                createdOn = Register.get_text().strip()

        # 마지막 갱신
        # lastUpdate = soup.find('time', {'class': "dateUpdated"})['datetime']
        # print("Last Update at : " + (lastUpdate if lastUpdate is not None else ""))

        # additionalProjectDetails 가 존재하면 수집.
        additionalProjectDetails = soup.find('section', {'class': "row m-section-additional-details psp-section"})
        if additionalProjectDetails is not None:
            projectInfos = additionalProjectDetails.findAll('section', {'class': "project-info"})
            for project_info in projectInfos:
                info_title = project_info.find('h4').text

                # file_dir = os.path.dirname(os.path.abspath(__file__)) + (
                #    "\\sourceforgeDir\\" if platform.system() == "Windows" else "/sourceforgeDir/")
                # 크롤러 실행 시 절대경로로 실행해야 __file__
                file_dir = self.initialpath + (
                    "\\sourceforgeDir\\" if platform.system() == "Windows" else "/sourceforgeDir/")

                # 개발언어
                if info_title == "Programming Language":
                    info_contents = project_info.findAll('a')
                    programmingLanguages = ""
                    for info_content in info_contents:
                        programmingLanguages = programmingLanguages + info_content.text + ","
                    programmingLanguages = programmingLanguages[0:-1]
                    pl = programmingLanguages

                    createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
                    crawlerInfo = CrawlingInfo(
                        crawlerName="sourceforge_re",
                        projectName=projectName,
                        projectUrl=projectUrl,
                        summary=summary,
                        createdOn=createdOn,
                        homepageUrl=homepageURL,
                        programmingLanguage=pl,
                        License=License
                    )
                    self.pid = crawlerInfo.project_db_insert()
                    ppid = crawlerInfo.project_db_exists()

                    self.log.debug(
                        "fetch: {}, {}, license={}, pid={}".format(projectName, projectUrl, License, self.pid))
                    # 새 디렉토리 말고 기존 디렉토리에서 이어받기 위하여
                    # print(os.getcwd())
                    # print("self.pid=",self.pid, "ppid=", ppid)
                    if ppid:
                        if int(ppid) < int(self.pid):
                            self.pid = ppid
                            print("Change pid : {0}".format(self.pid))
                    if not (os.path.exists(str(self.pid))):
                        try:
                            shutil.rmtree(projectName)
                            print("Delete {0}".format(projectName))
                        except:
                            pass

                        try:
                            os.chdir(projectName)
                        except:
                            os.mkdir(projectName)
                            os.chdir(projectName)
                    else:
                        os.chdir(self.pid)

        revision = "UnKnown"
        rel_createdOn = ""

        # Code 네비게이션을 우선 탐색.
        top_nav = soup.find('div', {'id': "top_nav_admin"})
        top_nav_contents = top_nav.findAll('li')
        for top_nav_content in top_nav_contents:
            link = top_nav_content.find('a')['href']
            element = top_nav_content.find('span')
            if element is None:  # 없으면 컨티뉴.
                continue
            if element.text == "Code":
                # file_db insert
                try:
                    os.chdir(revision)
                except:
                    os.mkdir(revision)
                    os.chdir(revision)

                fileInfo = [file_dir, revision, rel_createdOn]
                crawlerInfo.project_file_db_insert(fileInfo)
                print("\r" + crawlerInfo.toString())

                if not os.path.isdir("_vcs"):
                    os.mkdir("_vcs")
                os.chdir("_vcs")
                print("Code : https://sourceforge.net" + link)
                # 해당 링크를 기점으로 코드탐색 실행.
                current_path = os.getcwd()
                self.search_sourcefile_from_source_tab("https://sourceforge.net" + link, crawlerInfo, projectName,
                                                       self.pid)

                self.LAST_PROJECT_NUMBER += 1

                self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)
                return True

        # Code 네비게이션이 없으면 Files를 탐색.
        for top_nav_content in top_nav_contents:
            link = top_nav_content.find('a')['href']
            element = top_nav_content.find('span')
            if element is None:  # 없으면 컨티뉴.
                continue
            elif element.text == 'Files':
                # file_db insert
                try:
                    os.chdir(revision)
                except:
                    os.mkdir(revision)
                    os.chdir(revision)
                fileInfo = [file_dir, revision, rel_createdOn]
                crawlerInfo.project_file_db_insert(fileInfo)
                print("\r" + crawlerInfo.toString())

                print("Files : https://sourceforge.net" + link)

                newdirname = str(self.pid)
                if not os.path.isdir(newdirname):
                    try:
                        os.chdir(projectName)
                    except:
                        os.mkdir(projectName)
                        os.chdir(projectName)
                else:
                    os.chdir(newdirname)

                # 해당 링크를 기점으로 파일탐색 실행.
                current_path = os.getcwd()
                self.search_sourcefile_from_files_tab("https://sourceforge.net" + link, crawlerInfo, projectName,
                                                      self.pid)

                self.LAST_PROJECT_NUMBER += 1
                self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

                return True

        self.write_progress_log(self.LAST_SEARCH_CATEGORY, self.LAST_SEARCH_PAGE, self.LAST_PROJECT_NUMBER)

    def rename_directory(self, projectName, pid, initialPath):
        os.chdir(initialPath)
        try:
            newdirname = str(pid)
            print("Rename " + projectName + " > " + newdirname)
            if os.path.exists(projectName):
                if os.path.isdir(newdirname):
                    shutil.rmtree(newdirname)
                    os.rename(projectName, newdirname)
                else:
                    os.rename(projectName, newdirname)
        except Exception as e:
            self.log.error(e)
            print('Rename Error')

    # Code를 통해 소스코드를 받을 수 있는지 검사, 다운로드하는 함수.
    # 기본적으로는 access_url이 있는지 검사하여, input field의 내용을 subprocess를 통해 실행시킨다.
    def search_sourcefile_from_source_tab(self, url, crawlerInfo, projectName, pid):
        initialPath = os.getcwd()
        # Code 탭이 외부 링크로 연결된다면, response가 깨지게된다. ConnectionError가 발생하므로 이를 고침.
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            # 오류 로그 기록
            self.log.error("ConnectionError : " + url)
            return 0

        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        access_url = soup.find('input', {'id': 'access_url'})
        access_urls = soup.find('div', {'id': "access_urls"})

        result = 0
        # access_urls 란이 없는 경우는 Read Only CVS임. (git, svn, hg 접속을 할 수 없음)
        # 한 번 더 request를 보내서 command를 찾아내고, 실행환경이 windows가 아니면 다운로드 시작(windows면 pop-up alert가 방해하여 제한)
        if access_urls is None:
            div = soup.find('div', {'class': 'grid-24 pad'})
            alists = div.findAll('a')
            linktag = alists[-1]
            cvs_repo_link = linktag['href']
            cvs_request = requests.get(cvs_repo_link)
            cvs_soup = BeautifulSoup(cvs_request.text, 'lxml')
            listitems = cvs_soup.findAll('b')

            checkflag = True
            for list in listitems:
                command = list.text
                if 'cvs -z3' in command:
                    if VCSDownloader.download(command) == 0:
                        checkflag = False
            result = 1 if checkflag else 0

        # Read Only인 경우 다운로드 불가. (이 경우는 git, svn, hg Read Only인 경우.)
        elif access_urls.find('span').text is "Read Only access":
            result = 0

        # access url이 존재하면 command를 추출하여 VCSDownloader.download(command) 호출.
        elif access_url is not None:
            command = access_url['value']
            result = VCSDownloader.download(command)
            print("VCS Download")
            result = 1 if result else 0

        self.rename_directory(projectName, pid, initialPath)
        return result

    # Files 탭으로부터 출발하여 재귀적으로 디렉토리 파고들어 파일만 존재하게되면 다운로드한다.
    def search_sourcefile_from_files_tab(self, url, crawlerInfo, projectName, pid):
        initialPath = os.getcwd()
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            # 오류 로그 기록
            self.log.error("ConnectionError : " + url)
            return 0

        soup = BeautifulSoup(response.text, 'lxml')
        fileList = soup.find('table', {'id': "files_list"})
        tableBody = fileList.find('tbody')
        directories = tableBody.findAll('tr', {'class': "folder"})
        directories2 = tableBody.findAll('tr', {'class': "file"})

        ret = 0
        if len(directories) is not 0:
            chkval = 0
            for directory in directories:
                if directory['title'] is None:
                    continue
                print("find directory :", directory['title'])

                regex = re.compile('([0-9][.][0-9])')
                p_match = regex.search(directory['title'])
                if p_match:
                    if not os.path.isdir(directory['title']):
                        print("pattern match!!")
                        chkval += 1

                if not os.path.isdir(directory['title']):
                    os.mkdir(directory['title'])
                os.chdir(directory['title'])
                link = directory.find('a')['href']

                self.search_sourcefile_from_files_tab("https://sourceforge.net" + link, crawlerInfo, projectName, pid)
                os.chdir('..')
                if chkval >= 1:
                    ret = 1
        else:
            # 다운로드 수행
            files = tableBody.findAll('tr', {'class': "file"})
            for fileElement in files:
                url = fileElement.find('a')['href']
                size = fileElement.find('td', {'headers': 'files_size_h'}).text
                # URLDownloader.download(url, fileElement['title'], size)
                # 압축파일은 압축 해제
                name = fileElement['title']
                try:
                    result = URLDownloader.download(url, name, size)
                except:
                    print("Download Error")
                    result = False
                if (result):
                    if name.endswith('.tar') or name.endswith('.tar.xz') or name.endswith('.tar.gz') or name.endswith(
                            '.tgz'):
                        try:
                            print("tar name >> " + name)
                            tar = tarfile.open(name)
                            tar.extractall()
                            tar.close()
                            print(os.getcwd() + "/" + name)
                            os.remove(os.getcwd() + "/" + name)
                        except Exception as e:
                            print(e)
                            print("Unzip tar error!")
                            pass
                    elif name.endswith('.zip'):
                        try:
                            print("zip name >> " + name)
                            r = requests.get(url)
                            z = zipfile.ZipFile(io.BytesIO(r.content))
                            z.extractall()
                            z.close()
                            print(os.getcwd() + "/" + name)
                            os.remove(os.getcwd() + "/" + name)
                        except Exception as e:
                            print(e)
                            print("Unzip zipfile error!")
                            pass
                    else:
                        pass
        self.rename_directory(projectName, pid, initialPath)
        return ret


if __name__ == "__main__":
    crawler = LGCrawler()
    crawler.crawling()
