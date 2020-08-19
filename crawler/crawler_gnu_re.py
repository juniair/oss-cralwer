import platform
import shutil

from crawler import *
import re
from bs4 import BeautifulSoup
import functools
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="gnu_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class GNUCrawler(Crawler):
    def __init__(self):
        super(GNUCrawler, self).__init__(name="gnu")
        self.interval = 50
        self.page = 0
        self.item = 0

    def preCrawling(self):
        try:
            with open('progress_gnu.json', 'r') as self.progress:
                lastprogress = json.load(self.progress)
                self.page = lastprogress['page']
                self.item = lastprogress['item']
        except:
            with open('progress_gnu.json', "w") as self.progress:
                json.dump({'page': self.page, 'item': self.item}, self.progress)

    def crawlingAction(self):
        crawlerDir = os.getcwd()
        while(True):
            DataBase_Crawler_DB(
                crawlerName="gnu_re",
                crawlerStatus='1').crawler_db_insert()
            print(crawlerDir)
            pagenumbering = self.page * self.interval + self.item
            pagenumbering2 = self.interval
            projectLists = list(filter(
                lambda x: (x.findAll("td")[0].findAll("a")[0].text != "") and (
                    x.findAll("td")[1].text != ""),
                BeautifulSoup(
                    requests.get("https://savannah.gnu.org/search/?type_of_search=soft&words=%2A&offset={offset}&max_rows={interval}#results"
                                 .format(offset = pagenumbering + 9,interval = pagenumbering2)).text,
                    'html.parser'
                ).findAll('tr')[1:]
            ))

            # Escape Condition
            if len(projectLists) <= 0:
                print("Not found. Last Page!")
                break

            for project in projectLists:
                # projectName
                projectName = project.findAll("td")[0].findAll("a")[0].text
                projectName = re.sub('[\\\\/:*?\"<>|]', '_', projectName)
                # projectUrl
                projectUrl = project.findAll("td")[0].findAll(
                    "a")[0].attrs["href"].replace("..", "https://savannah.gnu.org")
                # summary
                summary = project.findAll("td")[1].text

                projectSoup = BeautifulSoup(
                    requests.get(projectUrl).text, 'html.parser')
                # homepageUrl
                try:
                    homepageUrl = list(filter(lambda x: x.findAll(
                        "a").text == " Project Homepage", projectSoup.findAll("div", {"class": "boxitem"})))[0].text
                except:
                    homepageUrl = ""
                # craetedOn
                metadata = list(filter(lambda x: "Registration Date" in x.text, projectSoup.findAll("p")))[
                        0].text
                try:
                    createdOn = functools.reduce((lambda x,y:x+' '+y),metadata.split("\n")[0][19:].split(' ')[1:6])
                    createdOn = datetime.strptime(createdOn,"%d %b %Y %I:%M:%S %p")
                except :
                    createdOn = ""
                # License
                try:
                    License = metadata.replace("Development Status","\n").split("\n")[1][9:]
                except:
                    License = ""
                # developer
                #! track from here
                developers=[]
                try:
                    grouplink = list(filter(lambda x:x.text =="View Members", projectSoup.findAll("a")))[0].attrs["href"]
                    teamsoup = BeautifulSoup(requests.get("https://savannah.gnu.org"+grouplink).text,'html.parser')
                    # step1 = teamsoup.findAll("tr")[1::2]
                    # step2 = list(map(lambda x:x.findAll("td")[1],step1))
                    # step3 = list(map(lambda x:x.findAll("a"),step2))
                    
                    developers = list(map(lambda x:re.sub("\s*<(\w*\s*)*>","",x.findAll("a")[0].text),list(map(lambda x:x.findAll("td")[1],teamsoup.findAll("tr")[1::2]))))
                except:
                    developers=[]
                # category
                category = ""
                # programmingLanguage
                programmingLanguage =""
                try:
                    toplistitem =projectSoup.findAll("li",{"class":"topmenuitemmainitem"})
                    toplistsourcecode = list(filter((lambda x:x.findAll('a')[0].text=="Source code"),toplistitem))[0]
                    toplistsubitem = list(toplistsourcecode.findAll("li",{"class":"topmenuitemsubmenu"}))
                    downloadItem =  toplistsubitem[0].findAll("a")[0]
                    downloadLink = downloadItem.attrs["href"]
                    downloadSoup = BeautifulSoup(requests.get("https://savannah.nongnu.org"+downloadLink).text,"html.parser")
                    if "svn" in downloadLink:
                        command = downloadSoup.findAll("code")[0].text.strip()
                    else:
                        command = downloadSoup.findAll("pre")[0].text.strip()
                    command = command.split("/<")[0]
                    vcsType = command.split(' ')[0]

                    os.chdir(crawlerDir)
                    print("[ "+ projectName + " ]")
                    print(command)

                    developers = (', '.join(developers))
                    # OS에 맞게 경로넣기
                    file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                        "\\gnuDir\\" if platform.system() == "Windows" else "/gnuDir/")

                    remote_repo_revision = []
                    if vcsType == "git":
                        remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
                    else:
                        remote_repo_revision.append("UnKnown")
                        remote_repo_revision.append("UnKnown")

                    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
                    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
                        continue

                    self.crawlingList.append(CrawlingInfo(
                        crawlerName="gnu_re",
                        projectName=projectName,
                        projectUrl=projectUrl,
                        summary=summary,
                        homepageUrl=homepageUrl,
                        createdOn=createdOn,
                        developer=developers,
                        programmingLanguage=programmingLanguage,
                        License=License
                    ))
                    pid = self.crawlingList[-1].project_db_insert()

                    try:
                        os.chdir(projectName)
                    except:
                        os.mkdir(projectName)
                        os.chdir(projectName)

                    downcnt = 0
                    projectDir = os.getcwd()
                    while downcnt < len(remote_repo_revision):
                        os.chdir(projectDir)
                        if remote_repo_revision[downcnt + 1].startswith('refs/tags/'):
                            temp = remote_repo_revision[downcnt + 1].split("/")
                            revision = "_".join(temp[2:len(temp)])
                        else:
                            revision = remote_repo_revision[downcnt + 1].split("/")[-1]
                            # 특수문자 replace
                        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
                        rel_createdOn = ""

                        try:
                            os.chdir(revision)
                        except:
                            os.mkdir(revision)
                            os.chdir(revision)

                        downresult = VCSDownloader.download(command)
                        if downresult >= 1:
                            if vcsType == 'git':
                                rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision,
                                                                         revision, downcnt)

                        fileInfo = [file_dir, revision, rel_createdOn]
                        self.crawlingList[-1].project_file_db_insert(fileInfo)
                        print("\r" + self.crawlingList[-1].toString())
                        downcnt += 2

                    os.chdir(crawlerDir)
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
                        print(e)
                        print('Rename Error')

                    self.item += 1
                    os.chdir(crawlerDir)
                    with open('../progress_gnu.json','w') as self.progress:
                        json.dump({'page':self.page,'item':self.item}, self.progress)
                except Exception as e:
                    print(e)
                    print("Exception!!")
                    self.item += 1
                    os.chdir(crawlerDir)
                    with open('../progress_gnu.json','w') as self.progress:
                        json.dump({'page':self.page,'item':self.item}, self.progress)

                    print("--------------------------")


            self.page += 1
            self.item = 0
            os.chdir(crawlerDir)
            with open('../progress_gnu.json','w') as self.progress:
                json.dump({'page':self.page,'item':self.item}, self.progress)

        DataBase_Crawler_DB(
            crawlerName="gnu_re",
            crawlerStatus='0').crawler_db_insert()


crawler = GNUCrawler()
crawler.crawling()
