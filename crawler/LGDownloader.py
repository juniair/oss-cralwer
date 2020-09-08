'''
압축파일 패턴
ZIP ┬─폴더 ─폴더 ┬tar.xz
    │           ├tar.gz
    │           ├zip
    │           ├jar
    ├─폴더 ┬tar.bz2
    │      ├tar.gz
    │      ├tar.gz
    │      ├tgz
    └tar.gz
처리해야할 파일들 목록: 폴더(완료), zip(완료), tar.gz, tar.bz2, tar
혹시 모르니 bz도 풀게 만들자.
'''
import sys
import os
import gzip
import zipfile, gzip

sys.setrecursionlimit(10**6)

def flatten(target_file):
    if (os.path.isfile(target_file)):  # 압축파일일 때
        #compressedList = [".zip", ".gz", ".tar", ".xz", ".bz2", ".bz"]
        external = os.path.splitext(target_file)[1]  # 압축파일의 확장자를 가져오는 부분.
        print("파일을 찾았습니다." + target_file)

        if external == ".zip":
            with zipfile.ZipFile(target_file) as zip_ref:
                pureFileName = os.path.splitext(os.path.basename(target_file))[0]                   #파일 이름 가져오기
                unzip_dir = f"{os.path.abspath(os.path.dirname(target_file))}\\..\\{pureFileName}"  #파일 경로에다 압축 풀기
                print("압축 푼 곳 " + unzip_dir)
                try:
                    os.mkdir(unzip_dir)
                except FileExistsError:
                    print("이미 압축이 풀려있어서 pass가 발동됨")
                print("압축풀기 직전")
                zip_ref.extractall(unzip_dir)
                flatten(unzip_dir)

        elif external == "gz":
            print("gz파일을 찾았습니다. 근데 아직은 구현 안됨.")

        else:
            print("새로운 확장자: " + external)

    #여기부터 짜야함.

    # if(any(lambda x:x==external for elem in compressedList)):
    # ~~~unzip

    elif os.path.isdir(target_file):  # 압축파일이 아닐 때(경로일 때)
        print("폴더임. 경로는..: " + os.path.abspath(target_file))
        print(os.listdir(target_file))
        for i in os.listdir(target_file):
            flatten(os.path.abspath(i))


home = os.path.expanduser("~")  # 홈 경로
flatten(home + "\\Downloads\\HR5xx_HR6xx_OpenSource_V2.0.zip")