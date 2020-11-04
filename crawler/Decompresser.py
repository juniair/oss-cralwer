#폴더를 재귀로 돌면서, 압축해제시켜주는 프로그램.
#지원 확장자는 compressedList 배열 참조.

import sys
import os
import zipfile, tarfile, py7zr

compressedList = [".zip", ".7z", ".tar", ".tgz", ".xz", ".gz", ".bz", ".bz2"]
home = os.path.expanduser("~")  # 홈 경로
sys.setrecursionlimit(10**6)

#common.py의 동명 함수를 가져옴. 단, 압축해제 경로를 current_directory로 지정함.
def extract_file(name, current_directory):
    filename = os.path.join(current_directory, name)
    try:
        os.mkdir(current_directory)
    except FileExistsError:
        pass

    try:
        if "."+filename.split(".")[-1] in compressedList[2:]:
            if "."+filename.split(".")[-2] == ".tar":
                with tarfile.open(filename) as tar:
                    tar.extractall(current_directory)

            elif "."+filename.split(".")[-2] in compressedList:
                with zipfile.ZipFile(filename) as z:
                    z.extractall(current_directory)
            os.remove(filename)

        elif filename.endswith('.zip'):
            with zipfile.ZipFile(filename) as z:
                z.extractall(current_directory)
            os.remove(filename)

        elif filename.endswith('.7z'):
            with py7zr.SevenZipFile(filename, mode="r") as z:
                z.extractall(current_directory)
            os.remove(filename)
    except RuntimeError:
        print(">>> 암호화된 파일이에요.")
        pass
    except zipfile.BadZipFile:
        print(">>> 손상된 파일이에요.")
        pass
    except EOFError:
        print(">>> 손상된 압축 파일이에요.")
        pass
    except IndexError:
        print(">>> 압축 해제된 파일 중 이름이 잘못된 파일이 있어요.")                  #ex) \Apple_Crawling\macOS\10.10\10.10.5\apache_mod_php-99.tag\apache_mod_php-99\php-5.5.27\php-5.5.27\ext\phar\tests\zip\files\stdin.zip
        pass
    except OSError:
        print(">>> 압축 해제된 파일 중 이름이 잘못된 파일이 있어요.")                  #ex) \Apple_Crawling\macOS\10.10\10.10.5\apache_mod_php-99.tag\apache_mod_php-99\php-5.5.27\php-5.5.27\ext\phar\tests\zip\files\pecl12414.zip
        pass
    except tarfile.ReadError:  # C:\Users\CODEMIND-dev12\Apple_Crawling\macOS\10.14\10.14.5\tcl-118\tcl-118.250.1\tcl_ext\tclxml\tclxml\tclxml-2.6.tar.gz 이게 문제였음.
        print(">>> 손상된 tar 파일이에요.")
        pass

    else:
        pass

def flatten(target_file):
    try:
        if os.path.basename(target_file)[0] != ".":
            pass
        elif len(target_file) != 1:
                pass
        else:
            print("오류!(1번)")
    except IndexError:
        print("오류!(2번)")
        return

    if (os.path.isfile(target_file)):  # 압축파일일 때
        external = os.path.splitext(target_file)[1]  # 압축파일의 확장자를 가져오는 부분.
        print("이런 파일을 찾았어요. : " + target_file)

        if (os.path.splitext(os.path.basename(target_file))[1] in compressedList[4:]):
            pureFileName = ".".join(os.path.splitext(os.path.basename(target_file))[0].split('.')[:-2])

        else:
            pureFileName = os.path.splitext(os.path.basename(target_file))[0]
        unzip_dir = f"{os.path.abspath(os.path.dirname(target_file))}" + os.sep + pureFileName  # 파일 경로에다 파일 이름으로 압축 풀기
        print("\t\t -> 압축 풀 곳은 여기. : " + unzip_dir)

        if any(map(lambda x: target_file.endswith(x), compressedList)):
            extract_file(target_file, unzip_dir)
            flatten(unzip_dir)
        else:
            print(">>식별되지 않은 확장자가 검출되었습니다. 이름은.. " + external)

        print("=== === === === ===\n")


    elif os.path.isdir(target_file):  # 압축파일이 아닐 때(경로일 때)
        root_dir = os.path.abspath(target_file)
        print("폴더였네요. 경로는.. " + root_dir)
        print(os.listdir(target_file))

        for i in os.listdir(target_file):
           flatten(root_dir + os.sep + i)