import platform
import re
import subprocess

from crawler import *
import shutil
import stat
import time
# require svn
import atexit
from signal import *

def handler() :
    DataBase_Crawler_DB(
        crawlerName="apache_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class ApacheCrawler(Crawler):
    def __init__(self):
        super(ApacheCrawler, self).__init__(name="apache")
        self.last_seen_info = ''
        self.dictionary = requests.get("https://projects.apache.org/json/foundation/projects.json").json()

    def preCrawling(self):
        try:
            with open('progress_apache.json', 'r') as progress:
                lastprogress = json.load(progress)
                self.last_seen_info = lastprogress['last_seen_info']
        except:
            with open('progress_apache.json', 'w') as progress:
                json.dump({'last_seen_info': self.last_seen_info}, progress)

    def crawlingAction(self):
        # print("items", len(self.dictionary.items()))
        DataBase_Crawler_DB(
            crawlerName="apache_re",
            crawlerStatus='1').crawler_db_insert()
        skip = True
        for index, project in self.dictionary.items():
            # print(index)

            if (self.last_seen_info == '') or (self.last_seen_info == index):
                skip = False

            if skip:
                print("Skip Condition 1 : name existed")
                continue

            repositories = []
            if 'repository' in project.keys():
                for element in project['repository']:
                    # duplicated repository handling.
                    if element not in repositories:
                        repositories.append(element)
                        break

            if (len(repositories) == 0):
                print("Skip Condition 2 : repository is 0")
                continue

            url = "https://projects.apache.org/project.html?" + index
            projectName = project['name']
            projectUrl = url

            if 'shortdesc' in project.keys():
                summary = project['shortdesc'].strip()
            elif 'description' in project.keys():
                summary = project['description'].strip()

            homepageUrl = project['homepage']

            try:
                createdOn = project['created']
                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
            except:
                createdOn = ""

            #developer = []
            developer = ""
            if 'developer' in project.keys():
                for person in project['developer']:
                    #developer.append(person['name'])
                    if(len(developer) != 0):
                        developer = developer + ','

                    developer = developer + person['name']
                    print(developer)

            try:
                category = project['category']
            except:
                category = ""

            try:
                programmingLanguage = project['programming-language']
            except:
                programmingLanguage = ""

            try:
                project_ver = project['version']
            except:
                project_ver = "UnKnown"

            release_list = []
            if 'release' in project.keys():
                for element in project['release']:
                    # duplicated repository handling.
                    if element not in release_list:
                        release_list.append(element)

            License = "License : Apache License 2.0"

            initialPath = os.getcwd()
            print("now Path : " + initialPath)

            # OS에 맞는 경로 설정
            file_dir = os.path.abspath(os.path.dirname(__file__)) + (
                "\\apacheDir\\" if platform.system() == "Windows" else "/apacheDir/")
            print("file_dir : " + file_dir)

            for repository in repositories:
                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)

                print("[" + projectName + "]")
                self.crawlingList.append(CrawlingInfo(
                    crawlerName="apache_re",
                    projectName=projectName,
                    projectUrl=projectUrl,
                    homepageUrl=homepageUrl,
                    developer=developer,
                    summary=summary,
                    category=category,
                    License=License,
                    createdOn=createdOn,
                    programmingLanguage=programmingLanguage,
                    project_ver=project_ver,
                    hasing=''
                ))

                self.pid = self.crawlingList[-1].project_db_insert()
                ppid = self.crawlingList[-1].project_db_exists()
                # 새 디렉토리 말고 기존 디렉토리에서 이어받기 위하여
                if ppid:
                    if int(ppid) < int(self.pid):
                        self.pid = ppid
                        print("Change pid : {0}".format(self.pid))

                command = "git clone" if repository.split('.')[-1] == 'git' else "svn checkout"
                command = command + ' ' + repository.replace('?p=', '/') + ' ' + index
                print(command)

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

                    revision = ""
                    # git은 tags의 정보를 release 버전으로 사용할수 있으나 svn은 리비전말고 다른정보가 없어서
                    # api에서 제공해주는 버전정보가 있다면 해당정보를 릴리즈버전으로 사용하고 없다면 UnKnown으로 한다.
                    if len(release_list) > 0 and (repository.split('.')[-1] != 'git'):
                        for rel in release_list:
                            if revision < rel['revision']:
                                revision = rel['revision']
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
                        #git을 제외한 다른 다운로드 방식은 릴리즈 버전별 작업이 어려워 git만 작업한다.
                        #svn은 최종 수정날짜를 조회하여 rel_createdOn 로 사용한다.
                        try:
                            parameters = command.split(' ')
                            if parameters[0] == 'git':
                                dirname = ((command.split(' ')[-1]).split('/')[-1]).replace(".git", "")
                                try:
                                    os.chdir(dirname)
                                    devnull = open(os.devnull, 'w')
                                    # git tag 버전으로 강제 되돌리기
                                    p = subprocess.Popen(['git', 'reset', '--hard', remote_repo_revision[downcnt]], stdout=devnull,
                                                         stderr=devnull).communicate()
                                    print("git Reset hard " + str(revision) + " Complete!")
                                    try:
                                        # git 커밋 히스토리 1행 조회 (Author date)
                                        p = subprocess.Popen(['git', 'log', '--pretty=format:\"%ad\"', '--date=short', '-n', '1'],
                                                             stdout=subprocess.PIPE,
                                                             stderr=subprocess.PIPE)
                                        (result, error) = p.communicate()
                                        rel_createdOn = result.decode('cp949').strip().replace("\"", "")
                                    except Exception as e:
                                        print(e)
                                        print("git log search Error!")
                                    os.chdir('..')
                                except Exception as e:
                                    print(e)
                                    print(str(downcnt) + ", git Reset Error!")
                            elif parameters[0] == 'svn':
                                if not len(release_list) > 0:
                                    # svn info를 실행하여 원격 저장소의 정보 가져옴.
                                    print(repository.replace('?p=', '/'))
                                    p = subprocess.Popen(['svn', 'info', repository.replace('?p=', '/')], stdout=subprocess.PIPE,
                                                         stderr=subprocess.PIPE)
                                    (result, error) = p.communicate()
                                    svninfo = result.decode('cp949')
                                    svninfo = svninfo.replace('마지막 수정 일자', 'Last Changed Date')
                                    # 디코딩, 대체 후 임시파일에 저장.
                                    with open('rel_temp.txt', 'w') as tempfile:
                                        tempfile.write(svninfo)
                                    # 임시파일에서 다시 읽어서 현재 버전의 마지막 수정 일자 가져오기 실행
                                    filePath = str(os.getcwd()) + "\\rel_temp.txt" if platform.system() == "Windows" else "/rel_temp.txt"
                                    f = open(filePath, "r")
                                    lines = []
                                    for paragraph in f:
                                        lines = re.split("\n",paragraph)
                                        lines = [x for x in lines if x]
                                        for each_line in lines:
                                            if "Last Changed Date" in each_line:
                                                svninfo = each_line.split(" ")[0].strip()
                                            else:
                                                pass
                                    f.close()
                                    # 날짜만 가져옴.
                                    rel_createdOn = svninfo.split("+")[0].split(': ')[1].strip()
                                    os.remove('rel_temp.txt')
                                else:
                                    try:
                                        rel_createdOn = release_list[0]['created']
                                    except:
                                        pass

                        except Exception as e:
                            print(e)
                            pass

                        fileInfo = [file_dir, revision, rel_createdOn]
                        self.crawlingList[-1].project_file_db_insert(fileInfo)
                    downcnt += 2
                os.chdir(initialPath)
                self.last_seen_info = index
                with open('../progress_apache.json', 'w') as progress:
                    json.dump({'last_seen_info': index}, progress)
            os.chdir(initialPath)

            self.last_seen_info = index
            with open('../progress_apache.json', 'w') as progress:
                json.dump({'last_seen_info': index}, progress)

            dirpath = file_dir + str(self.pid)
            newdirname = str(self.pid)

            # shutil.rmtree 작업 실패시 다시 삭제할 수 있게 하는 handler
            def set_rw(operation, name, exc):
                os.chmod(name, stat.S_IWRITE)
                return True
            print("newdir_name : " + newdirname)
            if os.path.isdir(newdirname):
                shutil.rmtree(newdirname, onerror = set_rw)
                time.sleep(1)
                os.rename(projectName, newdirname)
            else:
                os.rename(projectName, newdirname)

        os.chdir(initialPath)
        self.last_seen_info = ''
        with open('../progress_apache.json', 'w') as progress:
            json.dump({'last_seen_info': index}, progress)

        DataBase_Crawler_DB(
            crawlerName="apache_re",
            crawlerStatus='0').crawler_db_insert()

crawler = ApacheCrawler()
crawler.crawling()
