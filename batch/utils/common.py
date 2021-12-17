# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
load_dotenv()


def getenv(key, default=None, is_debug=False):
    value = os.getenv(key, default)
    if is_debug:
        print("Environment - {0} : {1}".format(key, value))

    return value


# 배치 로그 경로
BATCH_LOG_PATH = getenv(
    "BATCH_LOG_PATH", "/HDD2/alice_project/alice_crawler/batch/log/batch"
)

# clare 엔진 경로
CLARE_JAR = getenv(
    "CLARE_FILE_NAME", "/HDD2/alice_project/alice_crawler/Clare-1.0.jar"
)

# codebase 경로
CODE_BASE_PATH = getenv(
    "CLEAR_CODE_BASE_DIR", "/HDD2/alice_project/codebse"
)