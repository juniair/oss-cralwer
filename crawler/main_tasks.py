# -*- coding: utf-8 -*-

'''
각 오픈소스의 크롤러 시작 정의
'''

from sourceforge.crawler import SourceForgeCrawler
from github.crawler import GithubCrawler

if __name__ == '__main__':
    crawler = SourceForgeCrawler()
    # crawler = GithubCrawler()
    print(crawler.name)
    crawler.crawling()
