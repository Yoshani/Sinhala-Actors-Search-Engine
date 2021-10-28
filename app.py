from elasticsearch import Elasticsearch
from flask import Flask
from flask import render_template, request
from search import search_query_faceted, search_query

from config import Config

es = Elasticsearch([{'host': Config.host.value, 'port': Config.port.value}])
app = Flask(__name__)

global_search = "සාරංග දිසාසේකර"
global_names = []
global_gender = []


@app.route('/', methods=['GET', 'POST'])
def index():
    global global_search
    global global_names
    global global_gender
    field_intent = ''
    field_intent_value = ''

    if request.method == 'POST':
        if 'form_1' in request.form:
            if request.form['search']:
                search = request.form['search']
                global_search = search
            else:
                search = global_search
            list_actors, names, gender, field_intent, field_intent_value = search_query(search)
            global_names, global_gender = names, gender
        elif 'form_2' in request.form:
            search = global_search
            names_filter = []
            gender_filter = []
            for i in global_names:
                if request.form.get(i["key"]):
                    names_filter.append(i["key"])
            for i in global_gender:
                if request.form.get(i["key"]):
                    gender_filter.append(i["key"])
            list_actors = search_query_faceted(search, names_filter, gender_filter)
        return render_template('index.html', search_value=global_search, actors=list_actors, names=global_names,
                               gender=global_gender, field_intent=field_intent, field_intent_value=field_intent_value,
                               mode='no_results')
    return render_template('index.html', search_value='', actors='', names='', gender='',
                           field_intent='', field_intent_value='', mode='init')


if __name__ == "__main__":
    app.run(debug=True)
