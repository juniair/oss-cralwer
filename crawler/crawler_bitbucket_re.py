import platform
import re

import requests
import json
import sys
import signal
import shutil
import ProjectInformationDTO
import time
from crawler import *
import atexit
from signal import *


def handler() :
    DataBase_Crawler_DB(
        crawlerName="bitbucket_re",
        crawlerStatus='0').crawler_db_insert()
    sys.exit(0)
atexit.register(handler)

#for sig in (SIGABRT, SIGFPE, SIGBREAK, SIGILL, SIGINT, SIGSEGV, SIGTERM):
for sig in (SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM):
    signal(sig, handler)

class BitbucketCrawler(Crawler):
    def __init__(self):
        super(BitbucketCrawler,self).__init__(name="bitbucket")
        self.last_seen_info = ''
        self.url = "https://api.bitbucket.org/2.0/repositories?pagelen=100"

    def preCrawling(self):
        try:
            with open('progress_bitbucket.json','r') as progress:
                lastprogress = json.load(progress)
                self.url = lastprogress['last_url']
                self.last_seen_info = lastprogress['last_seen_info']
                print(self.last_seen_info)
        except:
            with open('progress_bitbucket.json','w') as progress:
                json.dump({'last_url':self.url, 'last_seen_info':self.last_seen_info},progress)

    def crawlingAction(self):
        DataBase_Crawler_DB(
            crawlerName="bitbucket_re",
            crawlerStatus='1').crawler_db_insert()

        # OS에 맞는 경로 설정
        #file_dir = os.path.dirname(os.path.abspath(__file__)) + ("\\bitbucketDir\\" if platform.system() == "Windows" else "/bitbucketDir/")
        # file경로가 이상하게 잡히는데 원인파악이 어려워 임시조치함
        file_dir = self.initialpath + (
            "\\bitbucketDir\\" if platform.system() == "Windows" else "/bitbucketDir/")
        print("file_dir : " + file_dir)
        initialPath = os.getcwd()
        while True:
            response = requests.get(self.url)
            text = response.text
            dictionary = json.loads(text)

            skip = True
            for item in dictionary['values']:

                if self.last_seen_info == '':
                    skip = False

                if item['name'] == self.last_seen_info:
                    skip = False

                if skip:
                    continue

                DTO = ProjectInformationDTO.ProjectInformationDTO()
                DTO.setProjectURL(item['links']['html']['href'])
                DTO.setProjectName(item['name'])
                DTO.setSummary(item['description'])
                DTO.setRegDT(item['created_on'].replace('T', ' ').split(' ')[0])
                DTO.setURLHash(md5hasher.hashing(item['links']['html']['href']))
                DTO.setLanguageName(item['language'])
                DTO.setHomepageURL(item['website'])
                DTO.setLastUpdate(item['updated_on'].replace('T', ' ').split(' ')[0])

                # 디렉토리명으로 특수문자 안들어가도록 replace
                projectName = re.sub('[\\\\/:*?"<>|]', '_', item['name'])
                projectUrl = item['links']['html']['href']
                summary = item['description']
                homepageUrl = item['website']
                createdOn = item['created_on'].replace('T', ' ').split(' ')[0]
                createdOn = datetime.strptime(createdOn, "%Y-%m-%d").date()
                programmingLanguage = item['language']
                hashing = md5hasher.hashing(item['links']['html']['href'])
                updated_on = item['updated_on'].replace('T', ' ').split(' ')[0]
                if not updated_on == '':
                    updated_on = datetime.strptime(updated_on, "%Y-%m-%d").date()
                else:
                    updated_on = ''

                # mercurial 의 릴리즈버전 구분을 위하여 tags url 내용을 가져온다.
                # tagList엔 tip(head와 비슷)이 무조건 1개 들어가 있어서 len은 1이상이며
                # release 버전이 있다면 2이상이다.
                try:
                    tag_response = requests.get(item['links']['tags']['href'])
                    tagText = tag_response.text
                    tagList = json.loads(tagText)
                    tagInfo = []
                    for item2 in tagList['values']:
                        # if item2['name'] == "tip":
                        #     continue
                        tagInfo.append(item2['name'])
                        tagInfo.append(item2['target']['date'].replace('T', ' ').split(' ')[0])
                except Exception as e:
                    print(e)
                    print("{0} is Tags Error".format(projectName))
                    continue


        # DAO = ProjectInformationDAO.ProjectInformationDAO()
        # DAO.insert(DTO)
                time.sleep(1)
                try:
                    os.chdir(projectName)
                except:
                    os.mkdir(projectName)
                    os.chdir(projectName)
                command = item['scm'] + " clone " + item['links']['clone'][0]['href'] + ' ' + item['name'].replace(' ', '-')

                try:
                    if  item['scm'] == "hg":
                        remote_repo_revision = tagInfo
                    else:
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

                    rel_createdOn = updated_on if updated_on is not '' else ''
                    if item['scm'] == "hg":
                        revision = remote_repo_revision[downcnt]
                        rel_createdOn = remote_repo_revision[downcnt + 1]
                    else:
                        revision = remote_repo_revision[downcnt + 1].split("/")[-1]

                    #디렉토리명으로 사용할거라서 특수문자 제거
                    revision = re.sub('[\\\\/:*?\"<>|]', '_', revision)

                    try:
                        os.chdir(revision)
                    except:
                        os.mkdir(revision)
                        os.chdir(revision)

                    try:
                        downresult = VCSDownloader.download(command)
                    except Exception as e:
                        print("download Error!")
                        print(e)

                    self.crawlingList.append(CrawlingInfo(
                        crawlerName="bitbucket_re",
                        projectName=projectName,
                        projectUrl=projectUrl,
                        summary=summary,
                        homepageUrl=homepageUrl,
                        createdOn=createdOn,
                        programmingLanguage=programmingLanguage,
                        hasing=hashing,
                        developer=""
                    ))
                    print("\r" + self.crawlingList[-1].toString())

                    pid = self.crawlingList[-1].project_db_insert()
                    if downresult >= 1:
                        if item['scm'] == "hg":
                            # 릴리즈버전으로 update
                            try:
                                os.chdir(item['name'].replace(' ', '-'))
                                p = subprocess.Popen(['hg', 'update', '-r', remote_repo_revision[downcnt]],
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                                (result, error) = p.communicate()
                                resultLog = result.decode('cp949').strip()
                                print("hg update Complete!")
                                print(resultLog)
                            except:
                                print("hg update Error")
                        if item['scm'] == "git":
                            # 릴리즈버전으로 reset 후 최근날짜가져오기
                            rel_createdOn = GetRepoInfo.ResetHardGit(command, remote_repo_revision, revision, downcnt)
                        fileInfo = [file_dir, revision, rel_createdOn]
                        self.crawlingList[-1].project_file_db_insert(fileInfo)
                    downcnt += 2

                os.chdir(initialPath)
                newdirname = str(pid)
                print(str(projectName) + " Rename : " + str(pid))

                if os.path.isdir(newdirname):
                    shutil.rmtree(newdirname)
                    time.sleep(1)
                    os.rename(projectName, newdirname)
                else:
                    os.rename(projectName, newdirname)

                self.last_seen_info = projectName
                with open('../progress_bitbucket.json', 'w') as progress:
                    json.dump({'last_url': self.url, 'last_seen_info': item['name']}, progress)

        # print("----------------------------------------------------")

            if 'next' in dictionary.keys():
                self.url = dictionary['next']
                self.last_seen_info = ''
            else:
                break

            os.chdir(initialPath)
            with open('../progress_bitbucket.json', 'w') as self.progress:
                json.dump({'last_url':self.url, 'last_seen_info':self.last_seen_info}, self.progress)

            DataBase_Crawler_DB(
                crawlerName="bitbucket_re",
                crawlerStatus='0').crawler_db_insert()
                # print('done, search {0} projects. download count = {1}'.format(count, download_count))
                # url = "https://api.bitbucket.org/2.0/repositories?pagelen=100"

crawler = BitbucketCrawler()
crawler.crawling()