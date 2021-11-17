import os
import re
import platform
import logging
import subprocess
from datetime import datetime

log = logging.getLogger(__name__)

def isUsableVersion(version, default_branch, project_name):
    patternString = '^refs\/(tags|heads)\/(v|ver|version|master|main'

    if (default_branch or None):
        patternString = patternString + "|" + default_branch

    if(project_name or None):
        patternString = patternString + "|" + project_name

    patternString = patternString + ")"

    partten = re.compile(patternString, re.IGNORECASE)
    return partten.search(version)


class GetRepoInfo:
    # git 릴리즈 버전구분하여 다운로드 하기위하여
    # 다운로드 전 ls-remote 명령어로 tags, head 정보 등을 가져온다.
    # git을 제외한 다른 vcs들은 다운로드 전 커맨드만으로 릴리즈 버전을 구분하기 어려워 최신버전을 다운로드하고 버전은 UnKnown으로 한다.
    def getReleaseVersion(command, default_branch = None):
        remote_revisions = []
        # 원격 저장소의 리비전을 가져오려고 시도
        parameters = command.split(' ')
        if parameters[0] == 'git':
            try:
                # master barnch부터 추가
                master_branch = GetRepoInfo.get_master_branch(command, default_branch)
                if len(master_branch) > 0:
                    for item in master_branch:
                        remote_revisions.append(item)

                # git ls-remote 수행
                log.debug("git ls-remote -t --refs --sort=-v:refname {}".format(parameters[2]))
                p = subprocess.Popen(['git', 'ls-remote', '-t', '--refs', "--sort=-v:refname", parameters[2]], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (result, error) = p.communicate()
                log.debug("ls-remote -t : result="+result.decode('utf-8'))
                # print("decode utf-8")
                if result.decode('utf-8') != '':
                    remote_revisions.extend(re.split('\s', result.decode('utf-8')))
                    # print(remote_revisions)
                    # 개행문자 삭제
                    remote_revisions.pop()

                
            except Exception as e:
                print(e)
                log.error(e)
                print("git remote Error")
                log.error("git remote Error")
        elif parameters[0] == 'hg':
            # hg summary를 수행
            p = subprocess.Popen(['hg', 'identify', parameters[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (result, error) = p.communicate()
            remote_revisions.append(result.decode('utf-8').strip())  # ('cp949')
            remote_revisions.append(result.decode('utf-8').strip())  # ('cp949')
        else:
            remote_revisions.append("UnKnown")
            remote_revisions.append("UnKnown")
        log.debug("remote_revisions~~~~~~~~~~~~~~:")
        log.debug(remote_revisions)
        return remote_revisions

    def get_master_branch(command, default_branch = None):
        remote_revisions = []
        # 원격 저장소의 리비전을 가져오려고 시도
        parameters = command.split(' ')
        # tag 없이 head만 존재할 경우를 위하여 head master를 리스트에 추가
        try:
            log.debug("git ls-remote -h --refs {}".format(parameters[2]))
            p = subprocess.Popen(['git', 'ls-remote', '-h', '--refs', parameters[2]],  # 파라미터로 브랜치를 지정하지 않는다. 'master', 'main' 
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            (result, error) = p.communicate()
            # print(result)
            log.debug("ls-remote -h : result="+result.decode('utf-8'))
            if result.decode('utf-8') != '':
                temp = re.split('\s', result.decode('utf-8'))
                log.debug(temp)
                head_refs = list(zip(temp[0::2], temp[1::2]))
                log.debug("head_refs=")
                log.debug(head_refs)
                for ref in head_refs:
                    if any([
                        ref[1] == "refs/heads/master", 
                        ref[1] == "refs/heads/main", 
                        ref[1] == "refs/heads/{}".format(default_branch)
                        ]):
                        remote_revisions.append(ref[0])
                        remote_revisions.append(ref[1])
                        break
        except Exception as e:
            log.error(e)
            print("git remote head Error")
            log.error("git remote head Error")
            print(e)
            log.error(e)
        return remote_revisions
            
    # git : 각 릴리즈버전별 tag로 소스코드를 reset하고 해당 버전의 최근커밋 히스토리를 조회한다.
    def ResetHardGit(command, remote_repo_revision, revision, downcnt):
        rel_createdOn = ""
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
                        rel_createdOn = result.decode('utf-8').strip().replace("\"", "")
                    except Exception as e:
                        print(e)
                        print("git log search Error!")
                    os.chdir('..')
                except Exception as e:
                    print(e)
                    print(str(downcnt) + ", git Reset Error!")

        except Exception as e:
            log.error(e)
            rel_createdOn = ""

        return rel_createdOn
    
    def ResetHardGit(command, git_hash, revision):
        rel_createdOn = ""
        try:
            parameters = command.split(' ')
            if parameters[0] == 'git':
                dirname = ((command.split(' ')[-1]).split('/')[-1]).replace(".git", "")
                try:
                    os.chdir(dirname)
                    devnull = open(os.devnull, 'w')
                    # git tag 버전으로 강제 되돌리기
                    p = subprocess.Popen(['git', 'reset', '--hard', git_hash], stdout=devnull,
                                         stderr=devnull).communicate()
                    log.info("git Reset hard {} Complete!".format(revision))
                    try:
                        # git 커밋 히스토리 1행 조회 (Author date)
                        p = subprocess.Popen(['git', 'log', '--pretty=format:\"%ad\"', '--date=short', '-n', '1'],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                        (result, error) = p.communicate()
                        rel_createdOn = result.decode('utf-8').strip().replace("\"", "")
                    except Exception as e:
                        log.error("git log search Error!")
                        log.error(e)
                    os.chdir('..')
                except Exception as e:
                    log.error(revision + ", git Reset Error!")
                    log.error(e)
            else:
                log.error("Only git is ok!")
        except Exception as e:
            log.error(e)
            rel_createdOn = ""

        return rel_createdOn
    
    def getDateSvn(repository):
        rel_createdOn = ""
        try:
            # svn info를 실행하여 원격 저장소의 정보 가져옴.
            log.debug(repository.replace('?p=', '/'))
            p = subprocess.Popen(['svn', 'info', repository.replace('?p=', '/')], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
            (result, error) = p.communicate()
            svninfo = result.decode('utf-8')
            svninfo = svninfo.replace('마지막 수정 일자', 'Last Changed Date')
            # 디코딩, 대체 후 임시파일에 저장.
            filePath = os.path.join(os.getcwd(), "rel_temp.txt")
            with open(filePath, 'w') as tempfile:
                tempfile.write(svninfo)
            # 임시파일에서 다시 읽어서 현재 버전의 마지막 수정 일자 가져오기 실행
            p = subprocess.Popen(['grep', '-e', 'Last Changed Date', '-m', '1', filePath], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (result, error) = p.communicate()
            last_changed_date = result.decode('utf-8')
            # ex) Last Changed Date: 2008-11-18 09:22:04 +0900 (2008-11-18, 화)
            last_changed_date = last_changed_date.split("Last Changed Date:")[-1].strip() # get date+time
            # ex) 2008-11-18 09:22:04 +0900 (2008-11-18, 화)
            rel_createdOn = last_changed_date.split(" ")[0].strip() # get date
            os.remove(filePath)
        except Exception as e:
            log.error("error to getDateSvn: {}".format(repository))
            log.error(e)
            rel_createdOn = ""
        return rel_createdOn


GetRepoInfo.getReleaseVersion("git clone https://github.com/facebook/hhvm hhvm_facebook")

