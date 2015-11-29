import re
import configparser
import os
import datetime
import time
import json

import requests
from pushbullet import Pushbullet


class HappeningDetector():
    def __init__(self):

        self.config = configparser.ConfigParser()
        self.config_paths = ['%s/config' % (os.getcwd())]

        for path in self.config_paths:
            if os.path.exists(path):
                self.config.read(path)

        self.api_key      = self.config.get('settings', 'api-key')
        self.pages        = int(self.config.get('settings', 'pages'))
        self.tripcodes    = self.config.get('settings', 'tripcodes').split(',')
        self.boards       = self.config.get('settings', 'boards').split(',')
        self.base_url     = self.config.get('settings', 'base_url')
        self.channel_name = self.config.get('settings', "channel_name")
        self.update_interval = float(self.config.get('settings', 'update_interval'))
        self.seen_cache      = []

        self.pb      = Pushbullet(self.api_key)
        self.channel      = None

        self.set_channel()    


    def update_seen_cache(self):
        if not os.path.exists('cache'):
            return 

        with open('cache', 'r') as cache_file:
            self.seen_cache = self.seen_cache + json.loads(cache_file.read())


    def write_cache(self):
        if not os.path.exists('cache'):
            with open('cache', 'w') as cache_file:
                cache_file.write(json.dumps(self.seen_cache))
                return 

        with open('cache', 'w') as cache_file:
                try:
                    cache_file.write(json.dumps(self.seen_cache + self.get_cache()))

                except json.decoder.JSONDecodeError as e:
                    cache_file.write(json.dumps(self.seen_cache))



    def iter_boards(self):
        for board in self.boards:
            self.iter_pages(board)


    def iter_pages(self, board):
        for page in range(self.pages):
            self.iter_threads(board, page) 
        

    def iter_threads(self, board, page):
        url  = 'http://%s/%s/%s.json' % (self.base_url, board, page)
        print(url)

        data = requests.get(url).json()
            # dict_keys(['tn_w', 'tim', 'md5', 'no', 'ext', 'last_modified', 'replies', 'sticky', 'com', 'locked', 'time', 'cyclical', 'h', 'resto', 'fsize', 
            # 'omitted_images', 'name', 'images', 'w', 'omitted_posts', 'filename', 'trip', 'tn_h'])
            #dict_keys(['time', 'omitted_images', 'no', 'last_modified', 'replies', 'images', 'sticky', 'com', 'omitted_posts', 'locked', 'trip', 'cyclical', 'resto'])

        if 'threads' not in data:
            print('no threads: %s' % (url))
            return 

        for thread in data['threads']:
            for post in thread['posts']:
                if 'trip' in post:
                    if post['trip'] in self.tripcodes:
                        com = post['com']
                        r = self.check_regex(com)

                        if r:
                            alert   = com.split('-- BEGIN ALERT --')[1].split(' -- END ALERT --')[0]
                            thread_url  = 'https://%s/%s/res/%s.html' % (self.base_url, board, post['no'])
                            
                            self.update_seen_cache()

                            if post['md5'] in self.seen_cache:
                                continue 

                            self.seen_cache.append(post['md5'])
                            self.write_cache()

                            self.push(alert, thread_url)
    

    def check_regex(self, text):
        reg = re.compile('(.*?)?(-- BEGIN ALERT --)\n*?.*?((\n*?.*?)?)*?\n*?(.*?)?(-- END ALERT --)')

        match = reg.search(text)

        if match:
            return match


        return False



    def push(self, message, url):
        print('pushing: %s' % (message))
        p = self.channel.push_link(message, url)


    def set_channel(self):
        for channel in self.pb.channels:
            if channel.name == self.channel_name:
                self.channel = channel

        if not self.channel:
            print('Could not set the channel')
            exit()

    def set_update_time(self):
        self.update_time = datetime.datetime.now() + datetime.timedelta(0, self.update_interval)


    def run(self):
        
        self.iter_boards()
        self.set_update_time()

        while True:
            print('sleeping..')
            time.sleep(self.update_interval)

            now = datetime.datetime.now()

            if now >= self.update_time:
                self.iter_boards()
                self.set_update_time()


if __name__ == '__main__':
    HD = HappeningDetector()
    HD.run()
