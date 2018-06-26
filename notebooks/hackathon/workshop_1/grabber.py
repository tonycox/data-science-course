import urllib.request
import json
import os.path
import logger
import sys
from fake_useragent import UserAgent
import re
import random
import time
from threading import Thread
import csv

LOGGER = logger.create_logger('grabber')
_BASE_URL = 'http://gorod.gov.spb.ru'


class JsonGrabber(object):
    _SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, data_dir='.'):
        self._FILES_DIR = os.path.join(data_dir, 'json_sources')
        self._PROBLEMS_FILE = os.path.join(self._FILES_DIR, 'problems.json')
        self._TYPES_FILE = os.path.join(self._FILES_DIR, 'types.json')

        self._API_URL = '%s/public_api/v2/stats' % _BASE_URL
        self._PROBLEMS_URL = '%s/problems/' % self._API_URL
        self._TYPES_URL = '%s/classifier/' % self._API_URL

    # def _save_json(json_data, output_file_path):
    #     LOGGER.debug("Save json data length %d to file %s" % (len(json_data), output_file_path))
    #     os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    #     with codecs.open(output_file_path, 'w', 'utf8') as outfile:
    #         json.dump(json_data, outfile, ensure_ascii=False)
    #         return json_data

    def _load_json_from_file(self, file):
        LOGGER.debug("Load json data from file %s" % file)
        with open(file, encoding='utf-8') as data_file:
            data = json.loads(data_file.read())
            LOGGER.debug("loaded %s data" % ("not empty" if sys.getsizeof(data) > 0 else "empty"))
            return data

    def _get_json(self, url, file):
        LOGGER.debug("Load json from url %s or file %s" % (url, file))
        if os.path.exists(file):
            LOGGER.debug("File %s exist" % file)
            return self._load_json_from_file(file)
        else:
            LOGGER.debug("File %s don't exist, load from url" % file)
            os.makedirs(os.path.dirname(file), exist_ok=True)
            urllib.request.urlretrieve(url, file)
            # with urllib.request.urlopen(url) as url:
            #     data = json.loads(url.read().decode('utf-8'))

            return self._load_json_from_file(file)

    def get_problems(self):
        LOGGER.debug("Load problems")
        return self._get_json(self._PROBLEMS_URL, self._PROBLEMS_FILE)

    def get_types(self):
        LOGGER.debug("Load types")
        return self._get_json(self._TYPES_URL, self._TYPES_FILE)


class ProblemsGrabber(Thread):
    # proxies = [{'ip': '87.226.213.86', 'port': '3128'},  # Will contain proxies [ip, port]
    #            {'ip': '149.202.0.60', 'port': '3128'},
    #            {'ip': '118.24.22.152', 'port': '3128'},
    #            {'ip': '194.182.74.110', 'port': '3128'},
    #            {'ip': '202.84.73.146 ', 'port': '42619'},
    #            {'ip': '163.172.217.103', 'port': '3128'},
    #            {'ip': '47.90.72.227', 'port': '8088'},
    #            {'ip': '109.105.199.60', 'port': '53281'},
    #            {'ip': '81.107.70.221', 'port': '80'},
    #            {'ip': '109.195.106.106', 'port': '8080'},
    #            {'ip': '144.76.176.72', 'port': '8080'},
    #            {'ip': '58.187.68.252', 'port': '6868'},
    #            {'ip': '61.220.26.97', 'port': '80'},
    #            {'ip': '194.182.74.151', 'port': '3128'},
    #            {'ip': '5.189.146.57', 'port': '80'},
    #            {'ip': '31.28.5.185', 'port': '63909'},
    #            {'ip': '213.136.86.234', 'port': '80'},
    #            {'ip': '219.127.191.12', 'port': '80'},
    #            {'ip': '185.145.202.171', 'port': '3128'},
    #            {'ip': '51.143.153.167', 'port': '80'},
    #            {'ip': '164.132.98.51', 'port': '80'}
    #            ]
    # n = 0
    # proxy_index = 0
    def __init__(self, numbers, output_file='./problems_meta.csv'):
        super(ProblemsGrabber, self).__init__()
        self.ua = UserAgent()
        self.numbers = numbers
        self.seed = 1.5+random.randint(3, 8)/0.6
        self.results = []
        self.output_file = output_file
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        self.run()
        # todo parse proxies from http://spys.one/aproxy/

    # def random_proxy(self):
    #     if len(self.proxies)>0:
    #         self.proxy_index = random.randint(0, len(self.proxies) - 1)
    #     else:
    #         self.proxy_index =0

    def _get_current_ip(self):
        from bs4 import BeautifulSoup
        content = self.request('http://checkip.dyndns.org')
        return re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
                          BeautifulSoup(content, 'html.parser').find('body').text)[0]

    def run(self):
        self._parse_problems()
        self._persist_result()

    def _parse_problems(self):
        LOGGER.debug("start parse {}".format(self.numbers))
        for n in self.numbers:
            try:
                data = self.request(self._build_url(n))
                json_data = json.loads(data)
            except Exception as e:
                self._persist_result()
                LOGGER.error("error load n = %d  [%s]" % (n,str(e)))

            res = {}
            is_public = True
            # todo refactoring
            for name_attr in ['id', 'district_name', 'watchers_count']:
                try:
                    res.update({name_attr: json_data[name_attr]})
                except:
                    is_public = False
                    break #not public problem
            try:
                if not is_public:
                    slidebar=json_data['sidebar']
                    district = slidebar['district']
                    res.update({'district_name':district['name']})
                else:
                    feed = json_data['feed']
                    create_event = feed[-1]['payload']  # create event is last
                    res.update({'create_date': create_event['dt']})
                    last_event = feed[0]['payload']
                    res.update({'last_update_date':last_event['dt']})
                    res.update({'status_count':len(feed)})
                    for name_attr in ['photos', 'body', 'files']:
                        res.update({name_attr + '_len': len(create_event[name_attr])})
            except Exception as e:
                LOGGER.error("error parse n = %d  [%s]" % (n,str(e)))
                self._persist_result()

            self.results.append(res)
            if len(self.results) >= 5000:
                self._persist_result()

    def _build_url(self, number):
        return 'http://gorod.gov.spb.ru/public_api/problems/%d' % number

    def request(self, url):
        req = self._set_request_prop(urllib.request.Request(url))
        time.sleep(self.seed)
        with urllib.request.urlopen(req) as context:
            return context.read().decode('utf8')
            # while len(self.proxies)>0:
            #     try:
            #         with urllib.request.urlopen(req) as context:
            #             return context.read().decode('utf8')
            #     except:
            #         LOGGER.debug('Proxy ' + self.proxies[self.proxy_index]['ip'] + ':' + self.proxies[self.proxy_index]['port'] + ' deleted.')
            #         del self.proxies[self.proxy_index]
            #         self.random_proxy()

    def _set_request_prop(self, req):
        # if self.n % 10 == 0:
        #     self.n = 0
        #     self.random_proxy()
        # proxy = self.proxies[self.proxy_index]
        req.add_header('User-Agent', self.ua.random)
        # if len(self.proxies)>0:
        #     req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
        #     self.n += 1
        return req

    _keys =['id', 'district_name', 'watchers_count', 'create_date','last_update_date', 'status_count', 'photos_len', 'body_len', 'files_len'] #self.results[0].keys()
    def _persist_result(self):
        if len(self.results) == 0:
            return
        with open(self.output_file, 'a', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, self._keys)
            try:
                if output_file.tell() == 0:
                    dict_writer.writeheader()
                    dict_writer.writerows(self.results)
                else:
                    dict_writer.writerows(self.results)
            except:
                LOGGER.error('Error write %s' % self._keys)
                for r in self.results:
                    try:
                        dict_writer.writerow(r)
                    except:
                        LOGGER.error('Error write {}'.format(r))
        self.results = []

if __name__ == '__main__':
    import pandas as pd
    from multiprocessing.dummy import Pool as ThreadPool
    import logging

    LOGGER.setLevel(logging.DEBUG)
    df = pd.DataFrame.from_csv('../../data/workshop_1/csv/problems.csv')
    ids=df.index.values
    thread_count =10
    step=len(ids)//thread_count+1
    array=[]
    for i in range(thread_count):
        start=step*i
        array.append(ids[start:start + step])

    pool = ThreadPool(thread_count)
    results = pool.map(ProblemsGrabber, array)
    pool.close()
    pool.join()


#     LOGGER.setLevel(logging.DEBUG)
#     DATA_FOLDER = os.path.join('..','..', 'data', 'workshop_1')
#     problems_json = BaseGrabber(DATA_FOLDER).get_problems()
