# -*- coding: utf-8 -*-
import os
import re
import subprocess
import platform
import logging

#############################################################################
# logger 세팅.
log = logging.getLogger()
#############################################################################


def download(command):
    # CVS인 경우. Windows에서 실행하면 경고알람이 뜸. Linux로 실행 권장하거나 CVS는 포기한다.
    if command.split(' ')[0] == 'cvs' and platform.system() == 'Windows':
        log.error("CVS Can't checkout/update in Windows Envirionment.")
        return 0

    chdirflag = False
    try:
        try:
            remote_repo_revision = getremoterevision(command)
        except:
            remote_repo_revision = "1"

        # 원격저장소 리비전이 없거나. 리포트저장소의 리비전이 0인경우.
        if remote_repo_revision == "" or remote_repo_revision == "0":
            log.warning(command.split(' ')[-1] + " : this project have empty repository")
            return -1

        # 해당 dir가 존재하는 경우, checkout/clone을 수행하지 않고 update/pull을 수행하도록 변경한다.
        if os.path.isdir(command.split(' ')[-1]):
            chdirflag = True  # pull, update등은 해당 디렉토리로 가서 수행해야하므로. 끝나고 원복 할 수 있어야함.
            os.chdir(command.split(' ')[-1])

            try:
                local_repo_revision = getlocalrevision(command)
            except:
                local_repo_revision = ""

            if remote_repo_revision == local_repo_revision:
                log.info(command.split(' ')[-1] + " : This project is already fully updated.")
                os.chdir('..')
                return 0

            log.info("Start subprocess for download " + command.split(' ')[-1])
            # cvs는 그대로 수행.
            command = command.replace("checkout", "update")  # svn checkout을 svn update로 변경.
            command = command.replace("clone", "pull")  # git clone -> git pull, hg clone -> hg pull
            paramlist = command.split(' ')
            command = paramlist[0] + ' ' + paramlist[1]  # command 재설정 (git/hg pull, svn update)

        log.info("perform : " + command)
        #        p = subprocess.Popen(command, shell=True).communicate(timeout = 3600) # timeout은 1시간으로 설정.
        devnull = open(os.devnull, 'w')
        p = subprocess.Popen(command, shell=True, stdout=devnull, stderr=devnull).communicate(timeout=3600)
        if chdirflag:  # pull, update를 수행 한 후 작업 디렉토리 변경.
            os.chdir('..')
    except subprocess.TimeoutExpired:  # subprocess 실행시 1시간 이상 진행되면 타임아웃을 발생시킴.
        log.error("Occur TimeoutExpired, kill subprocess.")
        subprocess.call(['taskkill', '/f', '/t', '/pid', str(p.pid)], shell=True)
        log.info("kill subprocess, can't fully download " + command.split(' ')[-1])
        if chdirflag:
            os.chdir('..')
        return 0
    except BaseException as e:  # 그 외의 이유로 발생가능한 exception을 일단 처리하기 위함.
        print(e)
        log.error("Exception Occur at " + command.split(' ')[-1])
        import traceback
        traceback.print_exc()
        log.info("kill subprocess, can't download " + command.split(' ')[-1])
        if chdirflag:
            os.chdir('..')
        return 0
    else:  # 다운로드 성공한 경우.
        log.info("End subprocess for downloading complete " + command.split(' ')[-1])
    return 1


# command 인자를 이용하여 원격 저장소의 최신 리비전을 가져온다.
# svn인 경우는 최신 리비전 넘버, hg인 경우는 최신 체인지셋의 해시를 가져온다.
# git인 경우는 최신 커밋의 해시를 가져온다.
def getremoterevision(command):
    remote_revisions = ""
    # 원격 저장소의 리비전을 가져오려고 시도.
    parameters = command.split(' ')
    if parameters[0] == 'svn':
        # svn info를 실행하여 원격 저장소의 리비전 정보 가져옴.
        p = subprocess.Popen(['svn', 'info', parameters[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        revision = result.decode('utf-8') # ('cp949')
        revision = revision.replace('리비전', 'Revision')
        # 디코딩, 대체 후 임시파일에 저장.
        with open('temp.txt', 'w') as tempfile:
            tempfile.write(revision)
        # 임시파일에서 다시 읽어서 grep 실행
        try:
            p = subprocess.Popen(['grep', '-e', 'Revision', '-m', '1', 'temp.txt'], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (result, error) = p.communicate()
            revision = result.decode('utf-8') # ('cp949')
            # 뒷부분 숫자가 필요하므로 이를 가져옴.
            remote_revisions = revision.split(':')[-1].strip()
            os.remove('temp.txt')
        except Exception as e:
            print(e)
            try:
                filePath = str(os.getcwd()) + "\\" if platform.system() == "Windows" else "/" + "temp.txt"
                f = open(filePath, "r")
                lines = []
                for paragraph in f:
                    lines = re.split("\n", paragraph)
                    lines = [x for x in lines if x]
                    for each_line in lines:
                        if "Revision" in each_line:
                            remote_revisions = each_line.split(" ")[-1].strip()
                        else:
                            pass
                f.close()
                os.remove('temp.txt')
            except:
                pass
    elif parameters[0] == 'hg':
        # hg summary를 수행
        p = subprocess.Popen(['hg', 'identify', parameters[2]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        remote_revisions = result.decode('utf-8').strip()  # ('cp949')
    elif parameters[0] == 'git':
        # git ls-remote 수행
        p = subprocess.Popen(['git', 'ls-remote', '-h', parameters[2], 'master'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        remote_revisions = result.decode('utf-8').split('\t')[0].strip() # ('cp949')
    elif parameters[0] == 'cvs':
        remote_revisions = "undefined"
    return remote_revisions


# command 인자를 이용하여 로컬 저장소의 리비전을 가져온다.
# svn의 경우는 로컬 리비전 넘버, hg의 경우는 로컬 체인지셋의 해시. git의 경우에는 로컬 최신 커밋의 해시를 가져온다.
def getlocalrevision(command):
    local_revisions = ""
    # 로컬 저장소의 리비전을 가져오려고 시도.
    parameters = command.split(' ')
    if parameters[0] == 'svn':
        # svn info를 실행하여 원격 저장소의 리비전 정보 가져옴.
        p = subprocess.Popen(['svn', 'info'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        revision = result.decode('utf-8') # ('cp949')
        revision = revision.replace('리비전', 'Revision')
        # 디코딩, 대체 후 임시파일에 저장.
        with open('temp.txt', 'w') as tempfile:
            tempfile.write(revision)
        # 임시파일에서 다시 읽어서 grep 실행
        p = subprocess.Popen(['grep', '-e', 'Revision', '-m', '1', 'temp.txt'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        revision = result.decode('utf-8') # ('cp949')
        # 뒷부분 숫자가 필요하므로 이를 가져옴.
        revision = revision.split(':')[-1].strip()
        local_revisions = revision
        os.remove('temp.txt')
    elif parameters[0] == 'hg':
        # hg identify 수행
        p = subprocess.Popen(['hg', 'identify'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        revision = result.decode('utf-8') # ('cp949')
        local_revisions = revision.strip()
    elif parameters[0] == 'git':
        # git log --pretty=format:"%H" -n 1 수행
        p = subprocess.Popen(['git', 'log', '--pretty=format:"%H"', '-n', '1'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (result, error) = p.communicate()
        revision = result.decode('utf-8') # ('cp949')
        local_revisions = revision.replace('\"', '').strip()
    elif parameters[0] == 'cvs':
        local_revisions = "undefined2"
    return local_revisions
