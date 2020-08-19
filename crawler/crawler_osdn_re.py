import re
import shutil

from crawler import *
from bs4 import BeautifulSoup
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="osdn_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)
class OSDNCrawler(Crawler):

    def __init__(self):
        super(OSDNCrawler, self).__init__(name="osdn")
        self.page = 1
        self.url = ""

    def preCrawling(self):
        try:
            with open('progress_osdn.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.page = lastprogress['page']
        except FileNotFoundError:
            with open('progress_osdn.json', 'w') as progress:
                json.dump({'page': self.page}, progress)


    def crawlingAction(self):
        while True:
            DataBase_Crawler_DB(
                crawlerName="osdn_re",
                crawlerStatus='1').crawler_db_insert()
            self.url = "https://osdn.net/softwaremap/simple_list.php?page={0}".format(self.page)
            response = requests.get(self.url)

            # Escape Condition
            if response.status_code == 404:
                break

            soup = BeautifulSoup(response.text, "lxml")
            projectListTable = soup.find("table", {'id': "project-simple-list-table"})
            projectItems = projectListTable.findAll("tr")

            # print("----------page {0} start----------".format(page))
            initialPath = os.getcwd()
            for item in projectItems:

                # page First td skip
                if item.find('td') is None:
                    continue
                # External Project, Freecode.com -> skip.
                elif "(freshmeat)" in item.find('td').text:
                    continue
                # External Project, SourceForge.com -> skip.
                elif "(sfnet)" in item.find('td').text:
                    continue

                # if project haven't download button, skip.
                if item.find('a', {'class': "btn btn-success"}) is None:
                    continue

                projectName = item.find('a').text
                projectURL = "https://osdn.net" + item.find('a')['href']

                # Project information Request
                projectResponse = requests.get(projectURL)

                # if getting project page is failed, skip.
                if projectResponse.status_code == 404:
                    continue

                projectSoup = BeautifulSoup(projectResponse.text, 'lxml')

                # check Source Code button Exist
                isExistSourceCode = False

                navTab = projectSoup.find('ul', {'class': "nav nav-tabs content-menu-for-project"})

                # suspended Project Check and Skip. example) https://osdn.net/projects/zytxa/
                if navTab is None:
                    continue

                toggleButtons = navTab.findAll('li', {'class': "dropdown"})
                for toggleButton in toggleButtons:
                    if toggleButton.find('a').text == 'Source Code':
                        isExistSourceCode = True

                # if Source Code dropdown menu doesn't exist, skip it.
                if isExistSourceCode is False:
                    continue

                # Release Check, if project doesn't have any release, Skip it.
                isExistRelease = projectSoup.find('div', {'class': "ptop-download-item"})
                if isExistRelease is None:
                    continue

                # get Project Description (Nullable)
                projectDescription = projectSoup.find('p').text if projectSoup.find('p') is not None else ""

                # get sidebar column for getting Project Information
                sidebarColumn = projectSoup.find('div', {'id': "sidebar-column"})
                sidebarComponent = sidebarColumn.findAll('div', {'class': "well no-top-round no-background no-border"})

                # sidebarComponent[0] : Project Information
                pInformations = sidebarComponent[0].findAll('ul', {'class': "unstyled no-dot"})
                lastUpdate = ""
                registered = ""

                # get lastUpdate, registered
                for pInfo in pInformations:
                    if pInfo.find('span').text == "Last Update":
                        lastUpdate = pInfo.find('time').text
                        lastUpdate = lastUpdate.split(' ')[0]
                    elif pInfo.find('span').text == "Registered":
                        registered = pInfo.find('ul').find('li').text.strip()
                        registered = registered.split(' ')[0]

                # sidebarComponent[1] : Software Map
                sInformations = sidebarComponent[1].findAll('li')

                license = ""
                pl = ""
                langauge = ""
                topic = ""
                targetUser = ""
                dbEnvironment = ""
                userInterface = ""

                # Referencing Software Map
                # Collect -> Database Environment, Target Users, License, Natural Language, Programming Language
                #            Topics, User Interface
                for sInfo in sInformations:
                    # get Database Environments
                    if sInfo.contents[0] == 'Database Environment':
                        databaseEnvironmentList = sInfo.find('li').findAll('a')
                        for element in databaseEnvironmentList:
                            dbEnvironment = dbEnvironment + element.text + ','
                        dbEnvironment = dbEnvironment[0:-1]
                    # get Target Users (Intended Audience)
                    elif sInfo.contents[0] == 'Target Users':
                        userList = sInfo.find('li').findAll('a')
                        for element in userList:
                            targetUser = targetUser + element.text + ','
                        targetUser = targetUser[0:-1]
                    # get Licenses
                    elif sInfo.contents[0] == 'License':
                        licenseList = sInfo.find('li').findAll('a')
                        for element in licenseList:
                            license = license + element.text + ','
                        license = license[0:-1]
                    # get Natural Language
                    elif sInfo.contents[0] == 'Natural Language':
                        langaugeList = sInfo.find('li').findAll('a')
                        for element in langaugeList:
                            langauge = langauge + element.text + ','
                        langauge = langauge[0:-1]
                    # get Programming Languages
                    elif sInfo.contents[0] == 'Programming Language':
                        langaugeList = sInfo.find('li').findAll('a')
                        for element in langaugeList:
                            pl = pl + element.text + ','
                        pl = pl[0:-1]
                    # get Topics (Category)
                    elif sInfo.contents[0] == 'Topics':
                        topicList = sInfo.find('li').findAll('a')
                        for element in topicList:
                            topic = topic + element.text + ','
                        topic = topic[0:-1]
                    elif sInfo.contents[0] == 'User Interface':
                        interfaceList = sInfo.find('li').findAll('a')
                        for element in interfaceList:
                            userInterface = userInterface + element.text + ','
                        userInterface = userInterface[0:-1]

                # get Cloning URL
                sourceCodeURLResponse = requests.get(projectURL + 'scm/')
                sourceCodeSoup = BeautifulSoup(sourceCodeURLResponse.text, 'lxml')
                repositoryURLS = sourceCodeSoup.find('input', {'class': "input-xlarge"})

                # No available VCS -> Skip
                if repositoryURLS is None:
                    continue

                urlListJSON = json.loads(repositoryURLS['data-repos'])
                cloningURL = list(urlListJSON.values())[0]

                # Construct VCS command.
                # gitroot / svnroot / hg.osdn.com / other(CVS)
                # git -> (git clone) cloningURL name
                # Subversion -> (svn checkout) cloningURL name
                # Mercurial -> (hg clone) cloningURL name
                # CVS -> (cvs -z3 -d) cloningURL 후 modulename 스트링을 replace 시켜줘야함.
                comment = ""
                if "gitroot" in cloningURL:
                    command = "git clone" + " " + cloningURL + " " + cloningURL.split('/')[-2]
                    vcsType = "git"
                elif "svnroot" in cloningURL:
                    command = "svn checkout" + " " + cloningURL + " " + cloningURL.split('/')[-2]
                    vcsType = "svn"
                elif "hg.osdn.net" in cloningURL:
                    command = "hg clone" + " " + cloningURL + " " + cloningURL.split('/')[-2]
                    vcsType = "hg"
                else:
                    command = "cvs -z3 -d" + " " + cloningURL
                    vcsType = "cvs"
                    command = command.replace('modulename', projectURL.split('/')[-2])

                # print Project Information.
                # print("[page " + str(self.page) + "] " + projectName + " : " + projectURL)

                # print("Project URL Hash : " + md5hasher.hashing(projectURL))
                # print("Cloning URL : " + cloningURL)
                print("Clone Command : " + command)
                # print("Last Update : " + lastUpdate)
                # print("Natural Language : " + langauge)
                # print("Target Users : " + targetUser)
                # print("Database Environment : " + dbEnvironment)
                # print("User Interface : " + userInterface)

                #디렉토리명으로 특수문자 안들어가도록 replace
                projectName = re.sub('[\\\\/:*?"<>|]','_',projectName.split('/')[0])
                projectUrl = projectURL
                createdOn = registered
                description = projectDescription
                License = license
                programmingLanguage = pl
                category = topic
                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()

                file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                    "\\osdnDir\\" if platform.system() == "Windows" else "/osdnDir/")

                print("[ " + projectName + " ]")

                self.crawlingList.append(CrawlingInfo(
                    crawlerName="osdn_re",
                    projectName=projectName,
                    projectUrl=projectUrl,
                    summary=description,
                    category=category,
                    createdOn=createdOn,
                    programmingLanguage=programmingLanguage,
                    License=License
                ))
                pid = self.crawlingList[-1].project_db_insert()
                print("pid >> " + str(pid))

                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)

                remote_repo_revision = []
                if vcsType == "git":
                    try:
                        remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
                    except:
                        remote_repo_revision.append("UnKnown")
                        remote_repo_revision.append("UnKnown")
                        pass
                else:
                    remote_repo_revision.append("UnKnown")
                    remote_repo_revision.append("UnKnown")

                if len(remote_repo_revision) < 1:
                    continue

                downcnt = 0
                initalPath = os.getcwd()
                while downcnt < len(remote_repo_revision):
                    os.chdir(initalPath)

                    if remote_repo_revision[downcnt + 1].startswith('refs/tags/'):
                        temp = remote_repo_revision[downcnt + 1].split("/")
                        revision = "_".join(temp[2:len(temp)])
                    else:
                        revision = remote_repo_revision[downcnt + 1].split("/")[-1]

                    # 특수문자 replace
                    revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)
                    rel_createdOn = lastUpdate
                    try:
                        os.chdir(revision)
                    except:
                        os.mkdir(revision)
                        os.chdir(revision)

                    try:
                        downresult = VCSDownloader.download(command)
                        if downresult == "1":
                            print("Download Complete!")
                    except Exception as e:
                        print(e)
                        print("Download Error2")

                    if downresult >= 1 and vcsType == "git":
                        try:
                            rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision,revision, downcnt)
                        except Exception as e:
                            print(e)
                            pass

                    fileInfo = [file_dir, revision, rel_createdOn]
                    self.crawlingList[-1].project_file_db_insert(fileInfo)
                    print("\r" + self.crawlingList[-1].toString())
                    downcnt += 2
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
                    print(e)
                    print('Rename Error')

            self.page += 1
            os.chdir(initialPath)
            with open('../progress_osdn.json', 'w') as progress:
                json.dump({'page': self.page}, progress)
        DataBase_Crawler_DB(
            crawlerName="osdn_re",
            crawlerStatus='0').crawler_db_insert()
        self.page = 1



crawler = OSDNCrawler()
crawler.crawling()