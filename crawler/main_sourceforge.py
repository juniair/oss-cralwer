# -*- coding: utf-8 -*-

'''
각 오픈소스의 크롤러 시작 정의
'''
import time

from sourceforge.crawler import SourceForgeCrawler

if __name__ == '__main__':
    crawler = SourceForgeCrawler()
    print(crawler.name)
    while(True):
        crawler.crawling()
        time.sleep(60*60*24) # 1day wait
