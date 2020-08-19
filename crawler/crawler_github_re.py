import shutil
import urllib.parse

from crawler import *
import datetime
import md5hasher
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="github_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)
class GithubCrawler(Crawler):
    def __init__(self):
        super(GithubCrawler, self).__init__(name="github")
        self.headers= {'Authorization': "token 1d85c431af3ddeaed5e36c9b1e2dd2956943c661"}
        self.maximum_delta = 730
        self.delta = 1
        self.page = 1
        self.sum_delta = 1
        self.keyword = "Java"

    def preCrawling(self):
        print(os.getcwd())
        try:
            with open('progress_github.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.maximum_delta = lastprogress['maximum_delta']
                self.delta = lastprogress['delta']
                self.sum_delta = lastprogress['sum_delta']
                self.page = lastprogress['page']
                self.keyword = lastprogress['keyword']
        except:
            with open('progress_github.json', 'w') as progress:
                json.dump({'maximum_delta': self.maximum_delta,'delta': self.delta,'sum_delta': self.sum_delta,'page': self.page, 'keyword' : self.keyword}, progress)

    
    def crawlingAction(self):
        self.count = 0
        log = logger.getLogger()
        current = datetime.datetime.utcnow()

        initialPath = os.getcwd()

        # Github 조회리스트
        keyword_list = ["Java", "C++", "C#", "C", "JavaScript", "Python", "Ruby", "PHP", "Objective-C", "Kotlin",
                        "Scala", "Vue", "Haskell", "ActionScript", "Clojure", "Perl", "Swift", "Visual Basic"]

        for gitkeyword in keyword_list:
            # 이미 탐색한 키워드가 있으면 스킵.
            index = keyword_list.index(gitkeyword)
            try:
                compareIndex = keyword_list.index(self.keyword.strip())
            except:
                compareIndex = keyword_list.index(gitkeyword)
            if compareIndex > index:
                continue
            else:
                self.keyword = gitkeyword
                pass

            print("=================Now Keyword : " + self.keyword)

            while self.sum_delta <= self.maximum_delta:
                DataBase_Crawler_DB(
                    crawlerName="github_re",
                    crawlerStatus='1').crawler_db_insert()
                target = current - datetime.timedelta(days=self.sum_delta)
                start = str(target).split('.')[0].replace(' ', 'T')
                target2 = target + datetime.timedelta(days=self.delta)
                end = str(target2).split('.')[0].replace(' ', 'T')
                # page = 1
                while True:
                    url = "https://api.github.com/search/repositories?q=language:{3}+created:{0}..{1}&order=asc&per_page=100&page={2}"\
                        .format(start, end, str(self.page), urllib.parse.quote(self.keyword))
                    log.warning("[crawler_github] " + url + " : Searching...")
                    try:
                        response = requests.get(url, headers=self.headers)
                    except requests.ConnectionError as e:
                        print("Connection Error!")
                        print(str(e))
                        continue
                    except requests.Timeout as e:
                        print("Timeout Error!")
                        print(str(e))
                        continue
                    except requests.RequestException as e:
                        print("General Error!")
                        print(str(e))
                        continue
                    except KeyboardInterrupt:
                        print("Someone closed the program")

                    if response.status_code != 200:
                        print("[crawler_github] Not 200")
                        break

                    text = response.text
                    dictionary = json.loads(text)

                    #  No result -> break.
                    if bool(dictionary['items']) is False:
                        log.info("[crawler_github] No Result")
                        break

                    #  Project information print
                    for item in dictionary['items']:
                        # if item haven't license information, skip this.
                        if item['license'] is None:
                            continue

                        try:
                            response_for_tag = requests.get(item['tags_url'], headers=self.headers)
                            tag_list_json = response_for_tag.text
                            tag_list = json.loads(tag_list_json)
                        except Exception as e:
                            print(e)
                            tag_list = False
                            pass

                        # if project haven't tag skip it.
                        if bool(tag_list) is False:
                            continue
    # projectUrl
                        projectUrl = item['html_url']
    # projectName
                        projectName = item['name']
    # homepageUrl
                        try:
                            homepageUrl = item['homepage']
                        except:
                            homepageUrl = ""
    # Hash
                        try:
                            Hash = md5hasher.hashing(item['html_url'])
                        except:
                            Hash = ""
    # summary
                        try:
                            summary = item['description']
                        except:
                            summary = ""
    # License
                        try:
                            License = item['license']['name']
                        except:
                            License = ""
    # programmingLanguage
                        try:
                            programmingLanguage = item['language']
                        except:
                            programmingLanguage = ""
    # createdOn
                        createdOn = ""

                        #file_dir = os.path.dirname(os.path.realpath(__file__)) + "\\githubDir\\"
                        file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                            "\\githubDir\\" if platform.system() == "Windows" else "/githubDir/")
                        print("[ " + projectName + " ]")
                        if item['clone_url'] is not None:

                            self.crawlingList.append(CrawlingInfo(
                                crawlerName="github_re",
                                projectName=projectName,
                                projectUrl=projectUrl,
                                summary=summary,
                                homepageUrl=homepageUrl,
                                createdOn=createdOn,
                                programmingLanguage=programmingLanguage,
                                License=License
                            ))
                            pid = self.crawlingList[-1].project_db_insert()

                            # print("Clone URL : " + item['clone_url'])
                            command = "git clone {0} {1}".format(item['clone_url'], item['name'] + '_' + str(item['id']))
                            print(command)
                            try:
                                os.chdir(projectName)
                            except:
                                os.mkdir(projectName)
                                os.chdir(projectName)

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
                                    log.warning('[crawler_github] found {0} project. trying to cloning/pull...'.format(
                                        item['name']))
                                    downresult = VCSDownloader.download(command)
                                    self.count += downresult
                                    log.warning(
                                        '[crawler_github] complete download {0}'.format(item['name'].replace(' ', '-')))

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
                                        datetime.datetime.time.sleep(1)
                                        os.rename(projectName, newdirname)
                                    else:
                                        os.rename(projectName, newdirname)
                            except Exception as e:
                                print(e)
                                print('Rename Error')

                    # check next page exist. if not, break.
                    if 'next' in response.links.keys():
                        self.page += 1
                    else:
                        break
                self.sum_delta += self.delta
                #다음날짜 탐색시 1페이지부터 탐색하도록
                self.page = 1
                with open('../progress_github.json', 'w') as progress:
                    json.dump({'maximum_delta': self.maximum_delta,'delta': self.delta,'sum_delta': self.sum_delta,'page': self.page, 'keyword': self.keyword}, progress)
                print("sum_delta : " + str(self.sum_delta))
                os.chdir(initialPath)

            print('done, newest cloning/pull project count = {0}'.format(self.count))
            # 다음 키워드 검색을 위하여 초기화
            self.sum_delta = 1
            self.page = 1

        #완료 후 초기화
        self.maximum_delta = 730
        self.sum_delta = 1
        self.page = 1
        self.keyword = keyword_list[0]
        with open('../progress_github.json', 'w') as progress:
            json.dump({'maximum_delta': self.maximum_delta, 'delta': self.delta, 'sum_delta': self.sum_delta, 'page': self.page,
                       'keyword': self.keyword}, progress)
        DataBase_Crawler_DB(
            crawlerName="github_re",
            crawlerStatus='0').crawler_db_insert()
        # signal_handler(signal.SIGTERM, None)

crawler = GithubCrawler()
crawler.crawling()