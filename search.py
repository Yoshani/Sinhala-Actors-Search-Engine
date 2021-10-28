from elasticsearch import Elasticsearch
import json
import io
from googletrans import Translator
from nltk import word_tokenize
from nltk.corpus import stopwords
import string
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config

'''uncomment these lines when running for the first time'''
# import nltk
# nltk.download('stopwords')
# nltk.download('punkt')

es = Elasticsearch([{'host': Config.host.value, 'port': Config.port.value}])


def translate_to_english(value):
    translator = Translator()
    english_term = translator.translate(value, dest='en')
    return english_term.text


def translate_to_sinhala(value):
    translator = Translator()
    english_term = translator.translate(value, dest='si')
    return english_term.text


def check_similarity(documents):
    tfidfvectorizer = TfidfVectorizer(analyzer="char", token_pattern=u'(?u)\\b\w+\\b')
    tfidf_matrix = tfidfvectorizer.fit_transform(documents)

    cs = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix)
    similarity_list = cs[0][1:]
    return similarity_list


# normal search
def search_query(search_term):
    english_term = translate_to_english(search_term)
    print("english term: ", english_term)

    select_type, strip_term, field_intent = intent_classifier(english_term)  # english term will be classified
    results = 'Nothing matched your search!'
    if select_type == -1:  # query eg: "සාරංග දිසාසේකර"
        results = search_text_multi_match(search_term, select_type)
    elif select_type == 0:  # query eg: "සාරංග දිසාසේකරගේ දෙමාපියන් කවුද?"
        if strip_term:
            results = search_text_multi_match(strip_term, select_type)
        else:
            results = search_text_multi_match(search_term, select_type)
    elif select_type == 1:  # query eg: "\"මල් හතයි\""
        results = search_text_phrase_match(search_term)
    elif select_type == 2:  # query eg: "හොඳම නිළියන් 10 දෙනා"
        results = top_match(strip_term, field_intent)

    if select_type != 0:
        field_intent = ''
    list_actors, names, gender, field_intent, field_intent_value = post_processing_text(results, field_intent)

    return list_actors, names, gender, field_intent, field_intent_value


# faceted search
def search_query_faceted(search_term, actors_filter, gender_filter):
    english_term = translate_to_english(search_term)
    print("english term: ", english_term)

    select_type, strip_term, field_intent = intent_classifier(english_term)
    results = 'Nothing matched your search!'
    if select_type == -1:  # query eg: "සාරංග දිසාසේකර"
        results = search_text_multi_match_faceted(search_term, select_type, actors_filter, gender_filter)
    elif select_type == 0:  # query eg: "සාරංග දිසාසේකරගේ දෙමාපියන් කවුද?"
        if strip_term:
            results = search_text_multi_match_faceted(strip_term, select_type, actors_filter, gender_filter)
        else:
            results = search_text_multi_match_faceted(search_term, select_type, actors_filter, gender_filter)
    elif select_type == 1:  # query eg: "\"මල් හතයි\""
        results = search_text_phrase_match_faceted(search_term, actors_filter, gender_filter)
    elif select_type == 2:  # query eg: "හොඳම නිළියන් 10 දෙනා"
        results = top_match_faceted(strip_term, field_intent, actors_filter, gender_filter)

    if select_type != 0:
        field_intent = ''
    list_actors, names, gender, field_intent, field_intent_value = post_processing_text(results, field_intent)

    return list_actors


def remove_stop_words(search_term):
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(search_term)
    filtered_sentence = [w for w in word_tokens if not w.lower() in stop_words]

    # remove punctuation and possessive terms
    filtered_sentence = [w for w in filtered_sentence if not (w == "'s")]
    filtered_sentence = ' '.join(filtered_sentence).translate(str.maketrans('', '', string.punctuation))
    print("filtered sentence: ", filtered_sentence)
    return filtered_sentence


def post_processing_text(results, field_intent):
    list_actors = []
    field_intent_value = ''
    for i in range(len(results['hits']['hits'])):
        actor = results['hits']['hits'][i]['_source']

        actor_si = {'name_si': 'නම', 'birthday': 'උපන්දිනය', 'gender_si': 'ස්ත්‍රී පුරුශහාවය', 'summary_si': 'සාරාංශය',
                    'personal_info_si': 'පෞද්ගලික තොරතුරු', 'parents_si': 'දෙමාපියන්', 'education_si': 'අධ්‍යාපනය',
                    'career_si': 'වෘත්තිය', 'movies_si': 'චිත්‍රපට', 'views': 'පිටු දසුන්'}

        actor_translated = {}  # translate the keys into Sinhala
        for key, value in actor.items():
            if key in actor_si.keys():
                actor_translated[actor_si[key]] = value
            # if key == 'birthday' or key == 'views':
            #     actor_translated[translate_to_sinhala(key)] = value
            # elif key[-3:] != '_en':
            #     actor_translated[translate_to_sinhala(key[:-3])] = value

        list_actors.append(actor_translated)
        if i == 0 and field_intent:
            if field_intent == 'birthday':
                field_intent_value = results['hits']['hits'][i]['_source']['birthday']
            else:
                field_intent_value = results['hits']['hits'][i]['_source'][field_intent + '_si']

    names = results['aggregations']['name']['buckets']
    gender = results['aggregations']['gender']['buckets']

    if field_intent and len(list_actors) > 0:
        field_intent = translate_to_sinhala(field_intent)
        field_intent = list_actors[0]['නම'] + " / " + field_intent

    return list_actors, names, gender, field_intent, field_intent_value


def intent_classifier(search_term):
    """
    type 0 : multi match search
    type 1: phrase query search
    type 2: top results search
    """
    select_type = -1
    result_word = ''
    field_intent = ''

    keyword_birthday = ["birthday", "age", "birth", "dob", "date"]
    keyword_summary = ["summary", "about"]
    keyword_personal_information = ["personal_info", "personal", "self", "information"]
    keyword_parents = ["parents", "mother", "father"]
    keyword_education = ["education", "school", "university", "learn"]
    keyword_career = ["career", "profession", "job"]
    keyword_movies = ["movies", "dramas", "plays", "films", "played"]
    keyword_fields = [keyword_birthday, keyword_summary, keyword_parents,
                      keyword_education, keyword_career, keyword_movies, keyword_personal_information]

    keyword_top = ["top", "best", "popular", "good", "great", "famous"]
    keyword_act = ["actors", "actresses", "act", "acting", "acts", "acted"]
    keyword_actor = ["actors", "actor"]
    keyword_actress = ["actress", "actresses"]

    # phrase search
    if (search_term.startswith("'") and search_term.endswith("'")) \
            or search_term.startswith('"') and search_term.endswith('"'):
        select_type = 1

        print("select_type: {}, result_word: {}, field_intent: {} ".format(select_type, result_word, field_intent))
        return select_type, result_word, field_intent

    search_term = remove_stop_words(search_term)

    search_term_list = search_term.split()

    # top search
    for j in search_term_list:
        documents = [j]
        documents.extend(keyword_top)
        documents.extend(keyword_act)

        max_val = max(check_similarity(documents))
        if max_val > 0.9:
            select_type = 2

    if select_type == 2:
        male, female = False, False
        query_words = search_term.split()
        query_words = [word for word in query_words if word.lower() not in keyword_top]
        for w in query_words:
            if w in keyword_actor:
                male = True
            if w in keyword_actress:
                female = True
        if male * female:
            field_intent = "all"
        elif male:
            field_intent = "male"
        else:
            field_intent = "female"
        query_words = [word for word in query_words if word.lower() not in keyword_act]
        result_word = ' '.join(query_words)

        print("select_type: {}, result_word: {}, field_intent: {} ".format(select_type, result_word, field_intent))
        return select_type, result_word, field_intent

    # field search
    query_words = search_term_list.copy()
    for i in search_term_list:
        for keyword_list in keyword_fields:
            documents = [i]
            documents.extend(keyword_list)

            max_val = max(check_similarity(documents))
            if max_val > 0.8:
                select_type = 0
                field_intent = keyword_list[0]
                print("field intent: " + field_intent)
                query_words.remove(i)

    result_word = ' '.join(query_words)

    print("select_type: {}, result_word: {}, field_intent: {} ".format(select_type, result_word, field_intent))
    return select_type, result_word, field_intent


def search_text_multi_match(search_term, select_type):
    query_term = search_term
    if select_type == -1:
        english_term = translate_to_english(search_term)
    else:
        english_term = search_term
    print(english_term)

    f = io.open('C:\\Yoshi\\My Aca\\Data Mining\\IR\\Project\\SearchActors\\actor_corpus\\actor_meta_all.json',
                mode="r",
                encoding="utf-8")
    meta_data = json.loads(f.read())

    actors_list = meta_data["actors_en"]

    documents_actors = [english_term]
    documents_actors.extend(actors_list)

    term_list = english_term.split()
    print(term_list)

    similarity_list = check_similarity(documents_actors)  # check if entered term is listed in actor names

    max_val = max(similarity_list)
    if max_val > 0.85:
        loc = np.where(similarity_list == max_val)
        i = loc[0][0]
        print(actors_list[i])
        query_term = actors_list[i]  # if name is found, search for that to avoid spelling errors

    results = es.search(index=Config.index.value, body={
        "size": 100,
        "query": {
            "multi_match": {
                "query": query_term,
                "type": "best_fields"
            }
        },
        "aggs": {
            "name": {
                "terms": {
                    "field": "name_si.keyword",
                    "size": 200
                }
            },
            "gender": {
                "terms": {
                    "field": "gender_si.keyword",
                    "size": 2
                }
            }
        }
    })
    return results


def search_text_phrase_match(search_term):
    results = es.search(index=Config.index.value, body={
        "size": 100,
        "query": {
            "query_string": {
                "query": search_term
            }
        },
        "aggs": {
            "name": {
                "terms": {
                    "field": "name_si.keyword",
                    "size": 200
                }
            },
            "gender": {
                "terms": {
                    "field": "gender_si.keyword",
                    "size": 2
                }
            }
        }
    })
    return results


def top_match(search_term, field_intent):
    size = 100
    term_list = search_term.split()
    print(term_list)
    size = [int(i) for i in term_list if i.isnumeric()][0]
    print(size)
    if field_intent == "all":
        results = es.search(index=Config.index.value, body={
            "size": size,
            "query": {
                "match_all": {}
            },
            "sort": {
                "views": {"order": "desc"}
            },
            "aggs": {
                "name": {
                    "terms": {
                        "field": "name_si.keyword",
                        "size": size,
                        "order": {"max_views": "desc"}
                    },
                    "aggs": {
                        "max_views": {"max": {"field": "views"}}
                    }
                },
                "gender": {
                    "terms": {
                        "field": "gender_si.keyword",
                        "size": 2
                    }
                }
            }
        })
    else:
        results = es.search(index=Config.index.value, body={
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "term": {"gender_en": field_intent}
                    }
                }
            },
            "sort": {
                "views": {"order": "desc"}
            },
            "aggs": {
                "name": {
                    "terms": {
                        "field": "name_si.keyword",
                        "size": size,
                        "order": {"max_views": "desc"}
                    },
                    "aggs": {
                        "max_views": {"max": {"field": "views"}}
                    }
                },
                "gender": {
                    "terms": {
                        "field": "gender_si.keyword",
                        "size": 2
                    }
                }
            }
        })
    return results


# ------------ faceted search with filters ------------


def search_text_multi_match_faceted(search_term, select_type, actors_filter, gender_filter):
    query_term = search_term
    if select_type == -1:
        english_term = translate_to_english(search_term)
    else:
        english_term = search_term
    print(english_term)
    print(actors_filter)

    f = io.open('C:\\Yoshi\\My Aca\\Data Mining\\IR\\Project\\SearchActors\\actor_corpus\\actor_meta_all.json',
                mode="r",
                encoding="utf-8")
    meta_data = json.loads(f.read())

    actors_list = meta_data["actors_en"]

    documents_actors = [english_term]
    documents_actors.extend(actors_list)

    term_list = english_term.split()
    print(term_list)

    similarity_list = check_similarity(documents_actors)

    max_val = max(similarity_list)
    if max_val > 0.85:
        loc = np.where(similarity_list == max_val)
        i = loc[0][0]
        print(actors_list[i])
        query_term = actors_list[i]  # if name is found, search for that to avoid spelling errors

    # form filtered query
    should_list = []

    if len(actors_filter) != 0:
        for i in actors_filter:
            should_list.append({"match": {"name_si": i}})
    if len(gender_filter) != 0:
        for i in gender_filter:
            should_list.append({"match": {"gender_si": i}})

    results = es.search(index=Config.index.value, body={
        "size": 100,
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query_term,
                        "type": "best_fields"
                    }
                },
                "filter": [{
                    "bool": {
                        "should": should_list
                    }
                }]
            }
        },
        "aggs": {
            "name": {
                "terms": {
                    "field": "name_si.keyword",
                    "size": 200
                }
            },
            "gender": {
                "terms": {
                    "field": "gender_si.keyword",
                    "size": 2
                }
            }
        }
    })
    return results


def search_text_phrase_match_faceted(search_term, actors_filter, gender_filter):
    # form filtered query
    should_list = []

    if len(actors_filter) != 0:
        for i in actors_filter:
            should_list.append({"match": {"name_si": i}})
    if len(gender_filter) != 0:
        for i in gender_filter:
            should_list.append({"match": {"gender_si": i}})

    results = es.search(index=Config.index.value, body={
        "size": 100,
        "query": {
            "bool": {
                "must": {
                    "query_string": {
                        "query": search_term
                    }
                },
                "filter": [{
                    "bool": {
                        "should": should_list
                    }
                }]
            }
        },
        "aggs": {
            "name": {
                "terms": {
                    "field": "name_si.keyword",
                    "size": 200
                }
            },
            "gender": {
                "terms": {
                    "field": "gender_si.keyword",
                    "size": 2
                }
            }
        }
    })
    return results


def top_match_faceted(search_term, field_intent, actors_filter, gender_filter):
    size = 100
    term_list = search_term.split()
    print(term_list)
    size = [int(i) for i in term_list if i.isnumeric()][0]

    # form filtered query
    should_list = []

    if len(actors_filter) != 0:
        for i in actors_filter:
            should_list.append({"match": {"name_si": i}})
    if len(gender_filter) != 0:
        for i in gender_filter:
            should_list.append({"match": {"gender_si": i}})

    if field_intent == "all":

        results = es.search(index=Config.index.value, body={
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": [{
                        "bool": {
                            "should": should_list
                        }
                    }]
                }
            },
            "sort": {
                "views": {"order": "desc"}
            },
            "aggs": {
                "name": {
                    "terms": {
                        "field": "name_si.keyword",
                        "size": size,
                        "order": {"max_views": "desc"}
                    },
                    "aggs": {
                        "max_views": {"max": {"field": "views"}}
                    }
                },
                "gender": {
                    "terms": {
                        "field": "gender_si.keyword",
                        "size": 2
                    }
                }
            }
        })

    else:

        results = es.search(index=Config.index.value, body={
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "term": {"gender_en": field_intent}
                    },
                    "filter": [{
                        "bool": {
                            "should": should_list
                        }
                    }]
                }
            },
            "sort": {
                "views": {"order": "desc"}
            },
            "aggs": {
                "name": {
                    "terms": {
                        "field": "name_si.keyword",
                        "size": size,
                        "order": {"max_views": "desc"}
                    },
                    "aggs": {
                        "max_views": {"max": {"field": "views"}}
                    }
                },
                "gender": {
                    "terms": {
                        "field": "gender_si.keyword",
                        "size": 2
                    }
                }
            }
        })
    return results
