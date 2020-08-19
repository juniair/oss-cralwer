import platform
import shutil
import re
import time
from crawler import *
from bs4 import BeautifulSoup
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="eclipse_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

#for sig in (SIGABRT, SIGFPE, SIGBREAK, SIGILL, SIGINT, SIGSEGV, SIGTERM):
for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class EclipseCrawler(Crawler):
    def __init__(self):
        super(EclipseCrawler, self).__init__(name="eclipse")
        self.page = 0
        self.item = 0

    def preCrawling(self):
        try:
            with open('progress_eclipse.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.page = lastprogress['page']
                self.item = lastprogress['item']
        except:
            with open('progress_eclipse.json',"w") as progress:
                json.dump({'page':self.page,'item':self.item},progress)

    def crawlingAction(self):
        initialPath = os.getcwd()
        print(initialPath)
        while(True):

            DataBase_Crawler_DB(
                crawlerName="eclipse_re",
                crawlerStatus='1').crawler_db_insert()

            print("[[page]]", self.page)
            pageSoup = BeautifulSoup(requests.get(
                "https://projects.eclipse.org/list-of-projects?combine=&page={0}".format(self.page)).text, "html.parser")

            projectListView = pageSoup.findAll(
                "div", {"class": "node-project"})[self.item:]

            # last Page search
            if len(projectListView) <= 0:
                print("Searching End!")
                break;

            for project in projectListView:
                nameDOM = project.find("h4", {"class": "name"})
# projectName
                projectName = nameDOM.text.strip().replace('/','')
                linkDOM = nameDOM.findAll("a")[0]
# projectUrl
                projectUrl = linkDOM.attrs["href"]
                projectSoup = BeautifulSoup(requests.get(
                    "https://projects.eclipse.org/"+projectUrl).text, "html.parser")
# category
                try:
                    category = projectSoup.findAll("ol", {"class": "breadcrumb"})[
                    0].findAll("li")[3].text
                except:
                    category = ""
# summary       
                try:
                    summary = projectSoup.find(
                    "div", {"class": "field-type-text-with-summary"}).findAll("p")[0].text.strip()
                except:
                    summary = ""
# License
                try:
                    License = projectSoup.findAll("div", {"class": "field-name-field-project-licenses"})[
                    0].findAll("a", {"class": "node-reference-hierarchy-0"})
                    License = str(License).split('>')[1].split('<')[0]

                except:
                    License = ""
                try:

                    homepageUrlCandidate = list(filter(lambda x: x.text == " Website", filter(
                        lambda x: getattr(x, "text", False), projectSoup.findAll("a"))))  # [0].attrs['href']
                    # homepageUrl
                    homepageUrl = homepageUrlCandidate[0].attrs["href"] if len(
                        homepageUrlCandidate) > 0 else ""
                except:
                    homepageUrl = ""
                
# createdOn
                try:
                    GovernanceSoup = BeautifulSoup(requests.get(
                    "https://projects.eclipse.org/"+projectUrl+"/governance").text, "html.parser")
                    createdOn = GovernanceSoup.findAll(
                    "div", {"class": "field-name-field-releases"})[0].findAll("tr")[-1].findAll("td")[-1].text
                    createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
                except:
                    createdOn = ""
                
                whoSoup = BeautifulSoup(requests.get(
                    "https://projects.eclipse.org/"+projectUrl+"/who").text, "html.parser")
# developers
                developer = set(list(map(lambda x: x.attrs['sort'], whoSoup.findAll(
                    "li", {"class": "projects-members-list-item"}))))
                developer = (', '.join(sorted(list(developer))))

# programmingLanguage
                programmingLanguage = ["Java"]
                developerSoup = BeautifulSoup(requests.get(
                    "https://projects.eclipse.org/"+projectUrl+"/developer").text, "html.parser")

                try:
                    repositoryLinks = list(map(
                        lambda x: [x.findAll("div", {"class": "projects-repository-title"})[
                            0].text, x.findAll("span", {"class": "clone-repo-url"})[0].text],
                        filter(
                            lambda x: "git.eclipse" in x.findAll("span", {"class": "clone-repo-url"})[
                                 0].text,developerSoup.findAll("div", {"class": "projects-repository"})
                        )
                    ))
                except:
                    continue

                print("pwd : " + os.getcwd())
                self.crawlingList.append(CrawlingInfo(
                    crawlerName="eclipse_re",
                    projectName=projectName,
                    projectUrl="https://projects.eclipse.org/"+projectUrl,
                    summary=summary,
                    homepageUrl=homepageUrl,
                    createdOn=createdOn,
                    developer=developer,
                    programmingLanguage=programmingLanguage,
                    License=License
                ))

                pid = self.crawlingList[-1].project_db_insert()
                print("\r" + self.crawlingList[-1].toString())

                try:
                    os.chdir(projectName)
                except:
                    try:
                        os.mkdir(projectName)
                        os.chdir(projectName)
                    except:
                        continue

                # OS에 맞는 경로 설정
                file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                    "\\eclipseDir\\" if platform.system() == "Windows" else "/eclipseDir/")

                for idx, repository in enumerate(repositoryLinks):
                    #if idx == 0:
                    title = repository[0].split(' - ')[0].split('.')[-1].split('/')[-1]
                    print(title)
                    try:
                        os.chdir(title)
                    except:
                        os.mkdir(title)
                        os.chdir(title)

                    command = "git clone "+repository[1]
                    print("command : " + command)

                    try:
                        remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
                    except:
                        remote_repo_revision = "0"

                    # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
                    if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
                        continue

                    downcnt = 0
                    initalPath = os.getcwd()
                    while downcnt < len(remote_repo_revision):
                        os.chdir(initalPath)

                        revision = remote_repo_revision[downcnt + 1].split("/")[-1]
                        # 특수문자 replace
                        revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
                        rel_createdOn = ""
                        try:
                            os.chdir(revision)
                        except:
                            os.mkdir(revision)
                            os.chdir(revision)

                        try:
                            downresult = VCSDownloader.download(command)
                        except Exception as e:
                            print(e)
                            print("Download Error!")

                        if downresult >= 1:
                            # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
                            try:
                                rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision, revision, downcnt)
                            except Exception as e:
                                print(e)
                                pass

                        fileInfo = [file_dir, revision, rel_createdOn, title]
                        self.crawlingList[-1].project_file_db_insert(fileInfo)
                        downcnt += 2

                os.chdir(initialPath)

                try:
                    newdirname = str(pid)
                    print("Rename "+projectName+" > "+newdirname)
                    if os.path.exists(projectName):
                        if os.path.isdir(newdirname):
                            shutil.rmtree(newdirname)
                            time.sleep(1)
                            os.rename(projectName, newdirname)
                        else:
                            os.rename(projectName, newdirname)
                except Exception as e:
                    print(e)
                    print('Rename Error')

                os.chdir(initialPath)
                self.item +=1
                with open('../progress_eclipse.json','w') as progress:
                    json.dump({'page':self.page,'item':self.item},progress)

            os.chdir(initialPath)
            self.page += 1
            self.item = 0
            print("last page")
            with open('../progress_eclipse.json','w') as progress:
                json.dump({'page':self.page,'item':self.item},progress)

        os.chdir(initialPath)
        # progress 초기화
        self.page = 0
        self.item = 0
        with open('../progress_eclipse.json', 'w') as progress:
            json.dump({'page': self.page, 'item': self.item}, progress)

        DataBase_Crawler_DB(
            crawlerName="eclipse_re",
            crawlerStatus='0').crawler_db_insert()


crawler = EclipseCrawler()
crawler.crawling()
