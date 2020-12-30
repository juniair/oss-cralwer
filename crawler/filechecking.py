import os
def breakcheck(path, crawlerName):
    try:
        print("로그파일: " + path + os.sep + crawlerName + "_log.txt")
        f = open(path + os.sep + crawlerName + "_log.txt", 'r')
        status = f.readline().rstrip("\n")

        # 중간에 끊긴 상태라면, 프로젝트명, 파일명 튜플 반환
        if status == "1":
            projectName = f.readline().rstrip("\n")
            fileName = f.readline()
            print(projectName, fileName)
            f.close()

            return projectName, fileName

        elif status == "0":
            return False

    # 처음 실행할 때
    except FileNotFoundError:
        print("로그 파일이 없음. {} 생성.".format(path + os.sep + crawlerName + "_log.txt"))
        f = open(path + os.sep + crawlerName + "_log.txt", 'w')
        f.write("0")
        f.close()
        return False

def writingLog(path, crawlerName , projectName, fileName):
    f = open(path + os.sep + crawlerName + "_log.txt")
    f.write("1\n{}\n{}".format(projectName, fileName))
    f.close()