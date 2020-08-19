import platform
import re
import shutil

from crawler import *
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="launchpad_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)
class LanchpadCrawler(Crawler):
    def __init__(self):
        super(LanchpadCrawler,self).__init__(name="launchpad")
        self.url = "https://api.launchpad.net/1.0/projects?ws.size=100&ws.op=latest"

    def preCrawling(self):
        try:
            with open('progress_launchpad.json', 'r') as self.progress:
                lastprogress = json.load(self.progress)
                self.url = lastprogress['url']
        except FileNotFoundError:
            with open('progress_launchpad.json', 'w') as self.progress:
                json.dump({'url': "https://api.launchpad.net/1.0/projects?ws.size=100&ws.op=latest"}, self.progress)


    def crawlingAction(self):
        self.count = 0
        self.satisfied_count = 0
        self.download_count = 0

        self.testval = 1
        while True:

            DataBase_Crawler_DB(
                crawlerName="launchpad_re",
                crawlerStatus='1').crawler_db_insert()

            print('[crawler_launchpad] ' + self.url + ' Searching...')
            i = 0
            # Maximum 10 time retry.
            isconnected = False
            dictionary = {}
            initialPath = os.getcwd()
            for i in range(1, 11):
                try:
                    response = requests.get(self.url)
                    text = response.text
                    dictionary = json.loads(text)
                    isconnected = True
                    break
                except:
                    print('[crawler_launchpad] timeout. retrying... count = {0}'.format(i))
                    pass

            # Conncetion failed 10 times, terminate it.
            if not isconnected:
                try:
                    # 10회 재시도 실패하면 다음 페이지로 이동
                    with open('../progress_launchpad.json', 'r') as self.progress:
                        nextLink = json.load(self.progress)
                        linkList = str(nextLink['url']).split('&')
                        print(linkList)
                        if len(linkList) >= 3:
                            temp0 = linkList[1].split('=')
                            temp1 = linkList[2].split('=')
                            temp2 = linkList[3].split('=')
                            temp1[1] = str(int(temp1[1]) + int(temp0[1]))
                            temp2[1] = str(int(temp2[1]) + int(temp0[1]))
                            linkList[2] = '='.join(temp1)
                            linkList[3] = '='.join(temp2)
                            self.url = "&".join(linkList)
                            with open('../progress_launchpad.json', 'w') as self.progress:
                                json.dump({'url': self.url}, self.progress)
                            print('[crawler_launchpad] connection Error > next Pages')
                            continue
                        else:
                            print('[crawler_launchpad] connection Error1')
                except:
                    print('[crawler_launchpad] connection Error2')
            print('[crawler_launchpad] response received.')

            for entry in dictionary['entries']:

                self.count += 1
                # print('[crawler_launchpad] searching entry {0}'.format(dictionary['entries'].index(entry)))
                # Only allow Git.
                if entry['vcs'] is None:
                    continue
                elif entry['vcs'] == 'Bazaar':
                    continue

                milestone_response = requests.get(entry['all_milestones_collection_link'])
                milestones = json.loads(milestone_response.text)

                # if this project haven't milestone, skip it.
                if milestones['total_size'] == 0:
                    continue

                downloadable = requests.get("https://git.launchpad.net/" + entry['web_link'].split('/')[-1])

                if downloadable.url != "https://git.launchpad.net/" + entry['web_link'].split('/')[-1]:
                    continue

                owner_response = requests.get(entry['owner_link'])
                owner_response_json = json.loads(owner_response.text)

                projectUrl = entry['web_link'] if (entry['web_link'] is not None) else ""
                homepageUrl = (entry['homepage_url'] if entry['homepage_url'] is not None else "Null")
                projectName = entry['title'] if (entry['title'] is not None) else ""

                # 프로젝트명의 특수문자때문에 오류발생하여 추가
                projectName = re.sub('[\\\\/:*?"<>|]', '_', projectName)

                print("Version Control System : " + entry['vcs'])
                projectDeveloper = owner_response_json['name'] if (owner_response_json['name'] is not None) else ""
                summary = entry['summary'].strip() if (entry['summary'] is not None) else ""
                licenses = ""
                for element in entry['licenses']:
                    licenses = element + ','
                License = licenses
                programmingLanguage = entry['programming_language'] if entry['programming_language'] is not None else "Null"
                createdOn = entry['date_created'].split('T')[0]
                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()

                command = "git clone https://git.launchpad.net/" + entry['web_link'].split('/')[-1] + " " + \
                          entry['web_link'].split('/')[-1]

                # if not os.path.isdir("launchpadDir"):
                #     os.mkdir("launchpadDir")
                # os.chdir('launchpadDir')

                # OS에 맞는 경로 설정
                #file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                #    "\\launchpadDir\\" if platform.system() == "Windows" else "/launchpadDir/")
                # file경로가 이상하게 잡히는데 원인파악이 어려워 임시조치함
                file_dir = self.initialpath + (
                    "\\launchpadDir\\" if platform.system() == "Windows" else "/launchpadDir/")

                self.crawlingList.append(CrawlingInfo(
                    crawlerName="launchpad_re",
                    projectName=projectName,
                    projectUrl=projectUrl,
                    summary=summary,
                    createdOn=createdOn,
                    homepageUrl=homepageUrl,
                    developer=projectDeveloper,
                    programmingLanguage=programmingLanguage,
                    License=License
                ))

                pid = self.crawlingList[-1].project_db_insert()

                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)

                try:
                    remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
                except:
                    remote_repo_revision.append("UnKnown")
                    remote_repo_revision.append("UnKnown")
                    pass

                # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
                if (remote_repo_revision == "0") or (len(remote_repo_revision) < 1):
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

                self.satisfied_count += 1

            if 'next_collection_link' in dictionary.keys():
                self.url = dictionary['next_collection_link']
            else:
                break
            os.chdir(initialPath)
            with open('../progress_launchpad.json', 'w') as self.progress:
                json.dump({'url': self.url}, self.progress)

        DataBase_Crawler_DB(
            crawlerName="launchpad_re",
            crawlerStatus='0').crawler_db_insert()
        self.url = "https://api.launchpad.net/1.0/projects?ws.size=100&ws.op=latest"

crawler = LanchpadCrawler()
crawler.crawling()
