# -*- coding: utf-8 -*-

'''
각 오픈소스의 크롤러 시작 정의
'''
import time

from ow2.crawler import OW2Crawler

if __name__ == '__main__':
    crawler = OW2Crawler()
    print(crawler.name)
    crawler.crawling()
    # while(True):
    #     crawler.crawling()
    #     time.sleep(60*60*24) # 1day wait
