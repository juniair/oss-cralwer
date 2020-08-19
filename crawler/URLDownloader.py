import os
import requests
import logging
import math
import wget_proxy
from common import get_tor_proxy, get_user_agent

#############################################################################
# logger 세팅.
log = logging.getLogger()
#############################################################################

# URLDownloader Module
# download(URL, DownloadFileName, FileSize)
# return : 1 = success, 0 = fail.

# URL을 이용하여 파일 다운로드.
# 같은 이름의 파일이 존재하는 경우는 다운로드 받지 않는다.
# 파일은 해당 프로그램이 실행되는 디렉토리의 Files 안에 다운로드 된다.
# source, sources, src가 존재하면 무조건 받으며, 그렇지 않은 경우는 확장자를 확인하여 exe,msi,md,pdf,dmg면 거부하고 아니면 받는다.
# 반환이 1이면 다운로드 성공, 0이면 다운로드 실패.
def download(url, filename, size, force=False):
    #source, src, sources이 포함되어있으면 무조건 다운로드.
    if 'src' not in filename.lower() and 'source' not in filename.lower() and 'sources' not in filename.lower():
        # source, src, sources가 없고 exe, msi, md확장자면 다운로드 하지 않음.
        denyExtension = ['exe', 'msi', 'md', 'pdf', 'dmg']
        if filename.split('.')[-1] in denyExtension:
            log.warning(filename + " isn't proper extension, and not contain source")
            return False

    # 동일 파일 이름이 존재하면 받지 않는다.
    if not force and os.path.isfile(filename) == True:
        log.warning(filename + " is already exist.")
        return False

    log.info("Try file download using Request.. filename : " + filename)
    log.info("Try file download using Request.. url : " + url)
    try:
        user_agent = "Codemind/1.0" # get_user_agent()
        proxies = None
        result = wget_proxy.download(url, out=filename, proxies=proxies, user_agent=user_agent, bar=None)
        log.info("Complete to download file : " + url)
    except Exception as e:
        log.error(str(e))
        os.remove(filename)
        return False

    log.warning("Download complete, filename : " + filename)
    return True

# 파일 크기 스트링을 입력받아 이를 바이트로 변환하여 리턴해줌, 최대 GB까지 구분
# 파일 크기가 너무 크면 파일 다운로드를 제한 할 목적으로 사용 예정.
def getsize(string):
    separator = ['bytes', 'kB', 'MB', 'GB']

    list = string.split(' ')
    mul = separator.index(list[1])

    size = float(list[0]) * (1024 ** mul)
    size = int(math.ceil(size))
    return size