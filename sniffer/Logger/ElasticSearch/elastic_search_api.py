import json
import requests


class ElasticSearchAPI(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    # def build_search_str(self):

    def search(self, uri, term):
        """Simple Elasticsearch Query"""
        query = json.dumps({
            "query": {
                "term": {
                    "to": term
                }
            }
        })

        # query = json.dumps({
        #     "query": {
        #         "term": {
        #             "from": term
        #         }
        #     }
        # })

        # query = json.dumps({
        #     "query": {
        #         "match": {
        #             "content": term
        #         }
        #     }
        # })

        response = requests.get(uri, data=query)
        # print response, 'text:', response.text
        results = json.loads(response.text)

        for hit in results['hits']['hits']:
            print hit['_source']

        return results


def main():
    es = ElasticSearchAPI()
    uri = "http://sniffer0.local:9200/_search?size=4&pretty=true&sort=timestamp:desc"
    lst = es.search(uri, '9800040')

if __name__ == '__main__':
    main()