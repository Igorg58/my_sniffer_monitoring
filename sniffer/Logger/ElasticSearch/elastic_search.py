from elasticsearch import Elasticsearch
# from elasticsearch.exceptions import AuthorizationException
# from elasticsearch.exceptions import AuthenticationException
from elasticsearch.exceptions import TransportError
from datetime import datetime
import copy
import os
import json
from Drivers import SnifferCrow


# def read_config_data():
#     working_dir = os.getcwd()
#     config_file = os.path.join(working_dir, 'config.json')
#     with open(config_file) as data_file:
#         return json.load(data_file)


class ElasticSearchLogger(object):
    def __init__(self, index, dock_type):
        try:
            # self.es = Elasticsearch(['http://elastic:changeme@localhost:9200'])
            # self.es = Elasticsearch(['http://localhost:9200'])
            auth = SnifferCrow.read_config_data()['elasticsearch']
            self.es = Elasticsearch(auth)
            pass
        except TransportError, e:
            print e
        self.index = index  # 'sniffer'
        self.doc_type = dock_type  # 'packet

    def add_row(self, msg_dict):
        try:
            row = copy.copy(msg_dict)
            row.update({'timestamp': datetime.utcnow()})
            self.es.index(index=self.index, doc_type=self.doc_type, body=row)
        except TransportError, e:
            print e
        except Exception, e:
            print e
