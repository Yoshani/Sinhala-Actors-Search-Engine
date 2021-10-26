from elasticsearch import Elasticsearch, helpers
import json
import io

from config import Config

es = Elasticsearch([{'host': Config.host.value, 'port': Config.port.value}])


def data_upload():
    f = io.open('C:\\Yoshi\\My Aca\\Data Mining\\IR\\Project\\SearchActors\\actor_corpus\\actors.json', mode="r",
                encoding="utf-8")
    data = json.loads(f.read())

    helpers.bulk(es, data, index=Config.index.value)


if __name__ == "__main__":
    data_upload()
