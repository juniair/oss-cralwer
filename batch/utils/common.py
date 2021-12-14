# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
load_dotenv()


def getenv(key, default=None, is_debug=False):
    value = os.getenv(key, default)
    if is_debug:
        print("Environment - {0} : {1}".format(key, value))

    return value
