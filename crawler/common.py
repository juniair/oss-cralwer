# -*- coding: utf-8 -*-

import os
import json
import random
import logging
from datetime import datetime
from dotenv import load_dotenv
from fake_useragent import UserAgent as FakeUserAgent
import tarfile
import zipfile
import py7zr

log = logging.getLogger(__name__)

CRAWLER_ENV = os.getenv("CRAWLER_ENV", "dev")
load_dotenv()

def getenv(key, default=None, debug=False):
    value = os.getenv(key, default)
    if debug:
        print("CRAWLER_ENV=",CRAWLER_ENV)
        print("env", key, value)
    return value

def get_datetime(date_string):
    # '2012-03-19T17:46:53Z' 
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

def get_yyyy_mm_dd(date_string):
    try:
        datetime_data = get_datetime(date_string)
        return str(datetime_data)[:10]
    except Exception as e:
        print(e)
        return "1900-01-01"

class UserAgent(object):
    ATTRIBUTES_MAP = {
        'hardware_types': [],
        'software_types': [],
        'software_names': [],
        'software_engines': [],
        'operating_systems': [],
        'popularity': [],
    }

    def __init__(self, limit=None, *args, **kwargs):
        self.user_agents = []

        for attribute, values in self.ATTRIBUTES_MAP.items():
            setattr(self, attribute, kwargs.get(attribute,[v.lower() for v in values]))

        for user_agent in self.load_user_agents():
            if limit is not None and len(self.user_agents) >= limit:
                break
            if self.hardware_types and user_agent['hardware_type'].lower() not in self.hardware_types:
                continue
            if self.software_types and user_agent['software_type'].lower() not in self.software_types:
                continue
            if self.software_names and user_agent['software_name'].lower() not in self.software_names:
                continue
            if self.software_engines and user_agent['software_engine'].lower() not in self.software_engines:
                continue
            if self.operating_systems and user_agent['operating_system'].lower() not in self.operating_systems:
                continue
            if self.popularity and user_agent['popularity'].lower() not in self.popularity:
                continue
            self.user_agents.append(user_agent)
            
    def load_user_agents(self, limit=None):
        data_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'user_agents.dat')
        with open(data_file_path, "r") as fp:
            for user_agent in fp.readlines():
                if hasattr(user_agent, 'decode'): user_agent = user_agent.decode()
                yield json.loads(user_agent)

    def get_user_agents(self):
        return self.user_agents
    
    def get_random_user_agent(self):
        return random.choice(self.user_agents)['user_agent']
    

ua = UserAgent(limit=100, operating_systems=['windows', 'linux'])
def get_user_agent():
    agent = ua.get_random_user_agent()
    return agent

def get_http_headers():
    headers = {'User-Agent': get_user_agent()}

    return headers

def get_tor_proxy():
    return {
        'http': getenv('TOR_HTTP_PROXY','http://127.0.0.1:8118'),
        'https': getenv('TOR_HTTPS_PROXY','http://127.0.0.1:8118')
    }


def extract_file(name, current_directory):
    filename = os.path.join(current_directory, name)
    result = True
    if filename.endswith('.tar') or filename.endswith('.tar.xz') or filename.endswith('.tar.gz') or filename.endswith('.tgz'):
        with tarfile.open(filename) as tar:
            tar.extractall()
    elif filename.endswith('.zip'):
        with zipfile.ZipFile(filename) as z:
            z.extractall()
    elif filename.endswith('.7z'):
        with py7zr.SevenZipFile(filename, mode="r") as z:
            z.extractall()
    else:
        result = False
    return result


