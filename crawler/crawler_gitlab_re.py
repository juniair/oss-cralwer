import platform
import shutil

import requests
import json
import md5hasher
import logger
from crawler import *
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="gitlab_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

#for sig in (SIGABRT, SIGFPE, SIGBREAK, SIGILL, SIGINT, SIGSEGV, SIGTERM):
for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)
class GitlabCrawler(Crawler):
    def __init__(self):
        super(GitlabCrawler,self).__init__(name="gitlab")
        self.page = 0

    def preCrawling(self):
        try:
            with open('progress_gitlab.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.page = lastprogress['page']
                print("reading page : " + self.page)
        except:
            with open('progress_gitlab.json','w') as progress:
                json.dump({'page':'0'}, progress)

    def crawlingAction(self):
        initialPath = os.getcwd()
        print(initialPath)
        count = 0
        headers = {'Private-Token' : 'uUdQoynytPjKkJNy1ru1'}
        log = logger.getLogger()
        while True:

            DataBase_Crawler_DB(
                crawlerName="gitlab_re",
                crawlerStatus='1').crawler_db_insert()

            # Search All Project.
            url = "https://gitlab.com/api/v4/projects?per_page=100&page={0}".format(self.page)
            log.warning("[crawler_gitlab] " + url + " : Searching...")
            # response = requests.get(url)
            response = requests.get(url, headers = headers)
            text = response.text
            lists = json.loads(text)

            for item in lists:
                log.info("[crawler_gitlab] Check item {0}".format(lists.index(item)))
                detail_response = requests.get(
                    "https://gitlab.com/api/v4/projects/{0}?license=True".format(item['id']), headers=headers)
                detail_response_text = detail_response.text
                detail_response_json = json.loads(detail_response_text)
                print("id : " + str(item['id']) +", name : "+ str(item['name']))
                print("status code : " + str(detail_response.status_code))

                # if License Not found, skip it.
                try:
                    license = detail_response_json['license']
                except:
                    #print("License Not Found Skip")
                    continue

                #if detail_response_json['license'] is None:
                #    continue

                if 'forked_from_project' in item.keys():
                    print("Forked From Project Skip")
                    continue

                tag_response = requests.get(
                    "https://gitlab.com/api/v4/projects/{0}/repository/tags".format(item['id']), headers=headers)
                tag_response_text = tag_response.text
                try:
                    tag_response_json = json.loads(tag_response_text)
                except:
                    print("Tag Search Fail Skip")
                    continue
                # if this project haven't any tag, skip it.
                if bool(tag_response_json) is False:
                    print("Tag Not Found Skip")
                    continue

                # if default_branch property not found skip (Maybe Non-public Repo)
                if 'default_branch' not in detail_response_json:
                    print("Default Branch Skip")
                    continue

                projectUrl = item['web_url']
                projectName = (item['name'] if (item['name'] is not None) else "")
                Hash = md5hasher.hashing(item['web_url'])
                description = (item['description'] if (item['description'] is not None) else "").encode('utf-8')
                try:
                    License = detail_response_json['license']['name']
                except:
                    License = ""

                print("[ " + projectName + " ]")

                pl_response = requests.get("https://gitlab.com/api/v4/projects/{0}/languages".format(item['id']), headers=headers)
                pl_response_text = pl_response.text
                pl_response_json = json.loads(pl_response_text)

                programmingLanguage= []
                for key in list(pl_response_json.keys()):
                    # print('Programming Language : ' + key)
                    programmingLanguage.append(key)

                # print("2. programming Language : " + str(programmingLanguage.__len__()))
                # print(programmingLanguage)
                # print("Created at : " + (item['created_at'].split('T')[0] if (item['created_at'] is not None) else ""))
                # print("Clone URL : " + item['http_url_to_repo'])

                createdOn = ""

                command = "git clone {0} {1}".format(item['http_url_to_repo'],
                                                    item['name'].replace(' ', '-') + '_' + str(item['id']))

                # OS에 맞는 경로 설정
                file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                    "\\gitlabDir\\" if platform.system() == "Windows" else "/gitlabDir/")

                self.crawlingList.append(CrawlingInfo(
                    crawlerName="gitlab_re",
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

                try:
                    for rel_item in tag_response_json:
                        remote_repo_revision.append(rel_item["target"])
                        remote_repo_revision.append(rel_item["name"])
                except:
                    remote_repo_revision = GetRepoInfo.getReleaseVersion(command)
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

            if response.headers['x-next-page'] is "":
                log.info("[crawler_gitlab] not exist next page!")
                break

            self.page = response.headers['x-next-page']
            with open('../progress_gitlab.json', 'w') as progress:
                json.dump({'page': self.page}, progress)
            print("page : " + self.page)
            os.chdir(initialPath)

                # print("\r" + self.crawlingList[-1].toString())

                # print('-----------------------------------------------------------------------------------------------------')

        print('done, search {0} pages, newest cloning/pull projects are {1}'.format(self.page, count))

        # progress reset
        self.page = "0"
        os.chdir(initialPath)
        with open('../progress_gitlab.json', 'w') as progress:
            json.dump({'page': self.page}, progress)
        DataBase_Crawler_DB(
            crawlerName="gitlab_re",
            crawlerStatus='0').crawler_db_insert()

crawler = GitlabCrawler()
crawler.crawling()