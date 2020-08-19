import os
import re
import subprocess
from datetime import datetime


class GetRepoInfo:
    # git 릴리즈 버전구분하여 다운로드 하기위하여
    # 다운로드 전 ls-remote 명령어로 tags, head 정보 등을 가져온다.
    # git을 제외한 다른 vcs들은 다운로드 전 커맨드만으로 릴리즈 버전을 구분하기 어려워 최신버전을 다운로드하고 버전은 UnKnown으로 한다.
    def getReleaseVersion(command):
        remote_revisions = []
        # 원격 저장소의 리비전을 가져오려고 시도
        parameters = command.split(' ')
        if parameters[0] == 'git':
            try:
                # git ls-remote 수행
                p = subprocess.Popen(['git', 'ls-remote', '-t', '--refs', parameters[2]], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (result, error) = p.communicate()
                remote_revisions = re.split('\s', result.decode('cp949'))
                # 개행문자 삭제
                remote_revisions.pop()
                # tag 없이 head만 존재할 경우를 위하여 head master를 리스트에 추가
                try:
                    p = subprocess.Popen(['git', 'ls-remote', '-h', '--refs', parameters[2], 'master'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    (result, error) = p.communicate()
                    if not len(result) < 1:
                        if not remote_revisions[-2] == result.decode('cp949').split('\t')[0].strip():
                            remote_revisions.append(result.decode('cp949').split('\t')[0].strip())
                            # head/master가 2건이상 조회되는 프로젝트가 있어서 split 추가
                            remote_revisions.append(result.decode('cp949').split('\t')[1].split('\n')[0])
                except Exception as e:
                    print("git remote head Error")
                    print(e)
            except Exception as e:
                print("git remote Error")
                print(e)
            if len(remote_revisions) < 1:
                remote_revisions.append("UnKnown")
                remote_revisions.append("UnKnown")

        else:
            remote_revisions.append("UnKnown")
            remote_revisions.append("UnKnown")
        return remote_revisions

    # git : 각 릴리즈버전별 tag로 소스코드를 reset하고 해당 버전의 최근커밋 히스토리를 조회한다.
    def ResetHardGit(command, remote_repo_revision, revision, downcnt):
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

        except Exception as e:
            print(e)
            rel_createdOn = ""
            pass

        return rel_createdOn