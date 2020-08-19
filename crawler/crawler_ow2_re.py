import platform
import shutil

from crawler import *
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="ow2_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class OW2Crawler(Crawler):
    def __init__(self):
        super(OW2Crawler,self).__init__(name="ow2")
        self.page=1

    def preCrawling(self):
        try:
            with open('progress_ow2.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.page = lastprogress['page']
        except FileNotFoundError:
            with open('progress_ow2.json', 'w') as progress:
                json.dump({'page':'1'},progress)

    def crawlingAction(self):

        count = 0
        initialPath = os.getcwd()
        while True:
            DataBase_Crawler_DB(
                crawlerName="ow2_re",
                crawlerStatus='1').crawler_db_insert()
            # Search All Project
            url = "https://gitlab.ow2.org/api/v4/projects?per_page=100&page={0}".format(self.page)
            response = requests.get(url)
            text = response.text
            lists = json.loads(text)
            for item in lists:
                detail_response = requests.get(
                    "https://gitlab.ow2.org/api/v4/projects/{0}?license=True".format(item['id']))
                detail_response_text = detail_response.text
                detail_response_json = json.loads(detail_response_text)

                # if License Not found, skip it.
                if detail_response_json['license'] is None:
                    continue

                if 'forked_from_project' in item.keys():
                    continue

                tag_response = requests.get(
                    "https://gitlab.ow2.org/api/v4/projects/{0}/repository/tags".format(item['id']))
                tag_response_text = tag_response.text

                try:
                    tag_response_json = json.loads(tag_response_text)
                except:
                    continue

                # if this project haven't any tag, skip it.
                if bool(tag_response_json) is False:
                    continue

                # if default_branch property not found skip (Maybe Non-public Repo)
                if 'default_branch' not in detail_response_json:
                    continue

                # Get Project Information : URL, URLHash, name, UpdateAt, CreatedAt, Description, License, Programming Language
                projectUrl = item['web_url'] if (item['web_url'] is not None) else ""
                #projectUrl_Hash = md5hasher.hashing(item['web_url']) if (item['web_url'] is not None) else ""
                projectName = (item['name'] if (item['name'] is not None) else "")
                description =  (item['description'] if (item['description'] is not None) else "")
                developer =  item['name_with_namespace'] if (item['name_with_namespace'] is not None) else ""
                developer = developer.split('/')[0]

                # Get License Information
                License = detail_response_json['license']['name'] if (detail_response_json['license']['name'] is not None) else ""

                # Get Programming Information
                pl_response = requests.get("https://gitlab.ow2.org/api/v4/projects/{0}/languages".format(item['id']))
                pl_response_text = pl_response.text
                pl_response_json = json.loads(pl_response_text)

                pl = ""
                for key in list(pl_response_json.keys()):
                    pl = pl + key + ','
                pl = pl[0:-1]
                programmingLanguage = pl

                createdOn =  (item['created_at'].split('T')[0] if (item['created_at'] is not None) else "")
                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
                #print("Clone URL : " + item['http_url_to_repo'])
                command = "git clone {0} {1}".format(item['http_url_to_repo'],
                                                     item['name'].replace(' ', '-') + '_' + str(item['id']))
                file_name = item['name'].replace(' ', '-') + '_' + str(item['id'])
                projectName = file_name
                print("[ "+file_name + " ]")
                print("platform.system() >> " + platform.system())
                # OS에 맞는 경로 설정
                file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                    "\\ow2Dir\\" if platform.system() == "Windows" else "/ow2Dir/")

                self.crawlingList.append(CrawlingInfo(
                    developer=developer,
                    crawlerName="ow2_re",
                    projectName=projectName,
                    projectUrl=projectUrl,
                    summary=description,
                    createdOn=createdOn,
                    programmingLanguage=programmingLanguage,
                    License=License
                ))
                pid = self.crawlingList[-1].project_db_insert()
                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)

                remote_repo_revision = []
                try:
                    remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
                except:
                    remote_repo_revision.append("UnKnown")
                    remote_repo_revision.append("UnKnown")

                # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
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
                    rel_createdOn = ""
                    try:
                        os.chdir(revision)
                    except:
                        os.mkdir(revision)
                        os.chdir(revision)

                    try:
                        downresult = VCSDownloader.download(command)
                        count += downresult

                    except Exception as e:
                        print(e)
                        print("Download Error!")

                    if downresult >= 1:
                        # git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
                        try:
                            rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision,
                                                                     revision, downcnt)
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

            # Terminate Condition Check.
            if response.headers['x-next-page'] is "":
                break
            self.page = response.headers['x-next-page']
            with open('../progress_ow2.json', 'w') as progress:
                json.dump({'page':self.page},progress)

            DataBase_Crawler_DB(
                crawlerName="ow2_re",
                crawlerStatus='0').crawler_db_insert()


crawler = OW2Crawler()
crawler.crawling()
