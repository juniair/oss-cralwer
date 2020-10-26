#폴더를 재귀로 돌면서, 압축해제시켜주는 프로그램.
#지원 확장자는 compressedList 배열 참조.

import sys
import os
import gzip
import zipfile, tarfile, py7zr

home = os.path.expanduser("~")  # 홈 경로
sys.setrecursionlimit(10**6)

#common.py의 동명 함수를 가져옴. 단, 압축해제 경로를 current_directory로 지정함.
def extract_file(name, current_directory):
    filename = os.path.join(current_directory, name)
    try:
        os.mkdir(current_directory)
    except FileExistsError:
        pass
    if filename.endswith('.tar') or filename.endswith('.tar.xz') or filename.endswith('.tar.gz') or filename.endswith('.tgz'):
        with tarfile.open(filename) as tar:
            tar.extractall(current_directory)
        os.remove(filename)
    elif filename.endswith('.zip'):
        with zipfile.ZipFile(filename) as z:
            z.extractall(current_directory)
        os.remove(filename)
    elif filename.endswith('.7z'):
        with py7zr.SevenZipFile(filename, mode="r") as z:
            z.extractall(current_directory)
        os.remove(filename)
    else:
        pass



def flatten(target_file):
    if os.path.basename(target_file)[0]==".":
        return
    if (os.path.isfile(target_file)):  # 압축파일일 때
        compressedList = [".zip", ".gz", ".tar", ".xz", ".bz2", ".bz", ".tgz"]
        external = os.path.splitext(target_file)[1]  # 압축파일의 확장자를 가져오는 부분.
        print("이런 파일을 찾았어요. : \t\t\t\t\t\t\t\t\t\t" + target_file)

        pureFileName = os.path.splitext(os.path.basename(target_file))[0]  # 파일 이름 가져오기
        unzip_dir = f"{os.path.abspath(os.path.dirname(target_file))}" + os.sep + pureFileName # 파일 경로에다 파일 이름으로 압축 풀기
        print("압축 풀 곳은 여기. : \t\t\t\t\t\t\t\t\t\t\t" + unzip_dir)

        if any(map(lambda x: target_file.endswith(x), compressedList)):
            extract_file(target_file, unzip_dir)
            flatten(unzip_dir)
        else:
            print("식별되지 않은 확장자가 검출되었습니다. 이름은.. " + external)

    elif os.path.isdir(target_file):  # 압축파일이 아닐 때(경로일 때)
        root_dir = os.path.abspath(target_file)
        print("폴더였네요. 경로는.. " + root_dir)
        print(os.listdir(target_file))

        for i in os.listdir(target_file):
           flatten(root_dir + os.sep + i)

