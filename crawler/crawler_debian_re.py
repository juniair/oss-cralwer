from bs4 import BeautifulSoup
from urllib.request import urlopen
import URLDownloader
from crawler import *
import shutil
import stat
import atexit
from signal import *
import tarfile
import time

def handler() :
    DataBase_Crawler_DB(
        crawlerName="debian_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class DebianCrawler(Crawler):
    def __init__(self):
        super(DebianCrawler,self).__init__(name="debian")
        self.last_seen_info = ''

    def preCrawling(self):
        try:
            with open('progress_debian.json','r') as progress:
                lastprogress = json.load(progress)
                self.last_seen_info = lastprogress['last_seen_info']
                print(self.last_seen_info)
        except:
            with open('progress_debian.json','w') as progress:
                json.dump({'last_seen_info':self.last_seen_info}, progress)

    def crawlingAction(self):
        print(os.getcwd())
        initialpath = os.getcwd()
        DataBase_Crawler_DB(
            crawlerName="debian_re",
            crawlerStatus='1').crawler_db_insert()
        response = urlopen("https://packages.debian.org/stretch/allpackages")
        html = response.read()
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div', {'id': 'content'})
        packageLinks = div.findAll('a')

        # OS에 맞는 경로 설정
        file_dir = os.path.dirname(os.path.realpath(__file__)) + (
            "\\debianDir\\" if platform.system() == "Windows" else "/")

        print("file_dir : "+file_dir)

        skip = True
        for packageLink in packageLinks:

            # First Crawling...
            if self.last_seen_info == '':
                skip = False

            if packageLink['href'] == self.last_seen_info:
                skip = False

            if skip:
                continue

            try:
                packageResponse = requests.get("https://packages.debian.org/stable/" + packageLink['href'])
            except requests.exceptions.SSLError:
                # if SSL Error Ocurr, skip it and logging.
                self.log.Error(
                    "[crawler_debian] Occur SSLError at " + "https://packages.debian.org/stable/" + packageLink['href'])
                continue

            packageSoup = BeautifulSoup(packageResponse.text, 'lxml')
            navbar = packageSoup.find('div', {'id': "pnavbar"})

            # if navigation bar can't found, set category empty.
            if navbar is None:
                category = ""
            else:
                category = navbar.findAll('a')[-1].text

            # Virtual Category haven't any information. skip it.
            # Package Category is access Error Page. skip it.
            if category == 'virtual' or category == 'Packages':
                continue

            # Content Parsing
            content = packageSoup.find('div', {'id': 'content'})
            # projectName = content.find('h1').text.split(' ')[1].strip()
            projectName = packageLink['href']

            try :
                summary = content.find('div', {'id': "pdesc"}).find('h2').text
            except:
                summary = ""

            try:
                description = content.find('div', {'id': "pdesc"}).find('p').text.strip()
            except:
                description = ""

            try :
                version = ((content.find('h1').text.split('(')[1]).split(')')[0]).split(' ')[0]
                version = re.sub('[\\\\/:*?"<>|]', '_', version)
            except:
                version = "UnKnown"

            projectUrl = "https://packages.debian.org/stable/" + packageLink['href']
            print(projectUrl)

            # downloadable URL Parsing.
            try:
                downloadURLs = content.find('div', {'id': "pmoreinfo"}).findAll('ul')[1].findAll('li')
            except:
                continue

            try:
                os.chdir("debianDir")
            except:
                pass

            # OS에 맞는 경로 설정
            file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                "\\debianDir\\" if platform.system() == "Windows" else "/debianDir/")
            print("file_dir : " + file_dir)

            try:
                os.chdir(projectName)
            except:
                os.mkdir(projectName)
                os.chdir(projectName)

            try:
                os.chdir(version)
            except:
                os.mkdir(version)
                os.chdir(version)

            for downloadURL in downloadURLs:
                name = downloadURL.find('a').text
                url = downloadURL.find('a')['href']
                # url http로 들어오지 않는 항목도 있어서 오류발생 수정.
                if(url.find('http') == -1):
                    continue

                result = URLDownloader.download(url, name[1:-1], 0)
                if(result):
                    if name[1:-1].endswith('.tar') or name[1:-1].endswith('.tar.xz') or name[1:-1].endswith('.tar.gz') or name[1:-1].endswith('.tgz') :
                        try:
                            print(name[1:-1])
                            with tarfile.open(name[1:-1]) as tar:
                                tar.extractall()
                            print(os.getcwd() + "/" + name[1:-1])
                        except Exception as e:
                            print(e)
                            print("Unzip tar error!")
                            pass
                        finally:
                            os.remove(os.getcwd() + "/" + name[1:-1])

            print("--------------------------------------------------------------")
            os.chdir(initialpath)
            self.last_seen_info = projectName
            with open('../progress_debian.json', 'w') as progress:
                json.dump({'last_seen_info': self.last_seen_info}, progress)

            self.crawlingList.append(CrawlingInfo(
                crawlerName="debian_re",
                projectName=projectName,
                projectUrl=projectUrl,
                summary=summary,
                category=category,
                project_ver=version,
                hasing='',
            ))

            pid = self.crawlingList[-1].project_db_insert()

            revision = version
            rel_createdOn = ""

            fileInfo = [file_dir, revision, rel_createdOn]
            self.crawlingList[-1].project_file_db_insert(fileInfo)
            dirpath = file_dir + str(pid)
            newdirname = str(pid)
            print(newdirname)

            def set_rw(operation, name, exc):
                os.chmod(name, stat.S_IWRITE)
                return True

            if os.path.isdir(newdirname):
                shutil.rmtree(newdirname, onerror=set_rw)
                time.sleep(1)
                os.rename(projectName, newdirname)
            else:
                os.rename(projectName, newdirname)
            os.chdir(initialpath)

            print("\r" + self.crawlingList[-1].toString())

        # progress 초기화
        os.chdir(initialpath)
        self.last_seen_info = ''
        with open('../progress_debian.json', 'w') as progress:
            json.dump({'last_seen_info': self.last_seen_info}, progress)

        DataBase_Crawler_DB(
            crawlerName="debian_re",
            crawlerStatus='0').crawler_db_insert()


crawler = DebianCrawler()
crawler.crawling()