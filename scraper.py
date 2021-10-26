import requests
import urllib.request
import time
import random
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from urllib.request import urlopen
from googletrans import Translator
import json, re
import wikipedia
from google.colab import files

'''
** The following code was written to be run on Google Colaboratory
The code can be found at: https://colab.research.google.com/drive/1EQsLLQgj6U7eADus8jw39x4NE2BcIjce?usp=sharing
'''

wikipedia.set_lang("en")


def translate_to_sinhala(value):
    translator = Translator()
    sinhala_val = translator.translate(value, src='en', dest='si')
    return sinhala_val.text


def translate_to_english(value):
    translator = Translator()
    english_val = translator.translate(value, src='si', dest='en')
    return english_val.text


def removeNumbers(value):
    return re.sub(r'[0-9]+', '', value)


def removeSquareBrackets(value):
    return re.sub(r'\[.*?\]', "", value)


def removeBrackets(value):
    return re.sub(r"\([^()]*\)", "", value)


def removeAllBrackets(value):
    return re.sub(r"\(.*\)", "", value)


url = 'https://en.wikipedia.org/wiki/List_of_Sri_Lankan_actors'
html = urlopen(url)
soup = BeautifulSoup(html, 'html.parser')

names = []
dobs = []
summary = []
personal_life = []
education = []
parents = []
career = []
films = []
views = []
genders = []

# Get all the links
allLinks = soup.find(id="bodyContent").find_all("a", {'href': True})
# random.shuffle(allLinks)
linkToScrape = 0
base_url = "https://en.wikipedia.org/"

count = 0
for link in allLinks:
    # we are only interested in other wiki articles
    if link['href'].find("/wiki/") == -1:
        continue

    # use this link to scrape
    linkToScrape = link
    request_href = requests.get(base_url + linkToScrape['href'])
    actorSoup = BeautifulSoup(request_href.content, 'html.parser')

    # remove unnecessary links
    if actorSoup.find(id='Personal_life') is None:
        continue

    # get the name
    name = actorSoup.find(id="firstHeading").text.strip()
    names.append(name)

    # get dob
    dob = actorSoup.find('span', {'class': 'bday'})
    if dob is not None:
        dob = dob.text.strip()
    else:
        dob = '1990-09-09'  # append dummy value for ES indexing
    dobs.append(dob)

    # get summary
    summary_text = wikipedia.WikipediaPage(name).summary
    summary.append(removeAllBrackets(summary_text))

    # get personal life
    personal_life_text = wikipedia.WikipediaPage(name).section('Personal life')
    personal_life_text = removeAllBrackets(personal_life_text)
    personal_life_split = personal_life_text.split('.')
    personal_life.append('.'.join(personal_life_split[0:6]))  # list only first 6 sentences to avoid lengthy text

    # get education/parents
    school = None
    parent = None
    table = actorSoup.find('table', {'class': 'infobox biography vcard'})
    if table is not None:
        ths = table.find_all('th')
        for th in ths:
            tag = th.text.strip()
            if tag == "Education":
                school = removeSquareBrackets(th.nextSibling.text)
                school = school.split('\n')
                if '' in school: school.remove('')
                school = ','.join(school)
            if tag == "Parents" or tag == "Parent(s)":
                parent = removeSquareBrackets(th.nextSibling.text)

    education.append(school)
    parents.append(parent)

    # get career
    career_text = wikipedia.WikipediaPage(name).section('Career')  # wikipedia has career listed under several headings
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Acting career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Cinema career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Theatre career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Television career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Film career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Golden career')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Theater work')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Filmography')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Early days')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('as an actor')
    if career_text is None or career_text == '':
        career_text = wikipedia.WikipediaPage(name).section('Drama career')

    if career_text is not None:
        career_text = removeAllBrackets(career_text)
        career_split = career_text.split('.')
        career_text = '.'.join(career_split[0:6])
    career.append(career_text)

    # get movies
    filmTables = actorSoup.find_all('table', {'class': "wikitable"})
    film_col = -1
    actor_films = []

    for filmTable in filmTables:
        rows = filmTable.find_all('tr')
        for idx, row in enumerate(rows):
            if idx == 0:  # header row
                ths = row.find_all('th')
                for i, th in enumerate(ths):
                    header = th.text.strip()
                    if header == 'Film' or header == 'Tele-film/Teledrama' or header == 'Teledrama':  # get the header name of films
                        film_col = i  # get the header index of films in table
                continue

            if film_col == -1:  # break if not a films table
                break

            cells = row.find_all('td')
            if len(cells) > 1:
                film = cells[film_col].text.strip()
                film = removeNumbers(film)
                film = re.sub(r"[\[\]]", "", film)
                film = removeBrackets(film)
                actor_films.append(film)

    actor_films = list(set(actor_films))
    if '' in actor_films: actor_films.remove('')
    if '–' in actor_films: actor_films.remove('–')
    if len(actor_films) > 10:
        actor_films = actor_films[0:10]
    all_films = ','.join(actor_films)  # get only first 10 films
    if all_films == '':
        all_films = None
    films.append(all_films)

    # get views
    info_url = 'https://en.wikipedia.org/w/index.php?title={}&action=info'.format(name)
    info_request_href = requests.get(info_url)
    infoSoup = BeautifulSoup(info_request_href.content, 'html.parser')
    page_views = infoSoup.find('div', {'class': "mw-pvi-month"}).text.strip()
    views.append(page_views)

    # get gender
    wiki_data_link = infoSoup.find('a', {'class': "extiw wb-entity-link external"})['href']
    data_request_href = requests.get(wiki_data_link)
    dataSoup = BeautifulSoup(data_request_href.content, 'html.parser')
    elements = dataSoup.find_all('div', {'class': "wikibase-snakview-value wikibase-snakview-variation-valuesnak"})
    gender = None
    for element in elements:
        strip = element.text.strip()
        if strip == "male" or strip == "female":
            gender = strip
            genders.append(gender)
            break

# create dataframe with English data
dic = {"names_en": names, "birthday": dobs, "gender_en": genders, "summary_en": summary,
       "personal_info_en": personal_life,
       "parents_en": parents, "education_en": education, "career_en": career, "movies_en": films, "views": views}
df_en = pd.DataFrame(dic)
df_en = df_en.replace('', None)
df_en.head()

# translate to Sinhala

translator = Translator()

df_si = df_en.copy()
df_si.drop(['birthday', 'views'], axis='columns', inplace=True)  # columns that need not be translated

translations = {}
for column in df_si.columns:
    # unique elements of the column
    unique_elements = df_si[column].unique()
    for element in unique_elements:
        # add translation to the dictionary
        if element != None:
            translations[element] = translate_to_sinhala(element)

# modify all the terms of the data frame by using the previously created dictionary
df_si.replace(translations, inplace=True)
df_si.columns = df_si.columns.str.replace("_en", "_si")
df_si.head()

# merge and rearrange
df = pd.concat([df_en, df_si], axis=1)
df = df[["names_si", "names_en", "birthday", "gender_si", "gender_en", "summary_si",
         "summary_en", "personal_info_si", "personal_info_en", "parents_si", "parents_en",
         "education_si", "education_en", "career_si", "career_en", "movies_si", "movies_en", "views"]]
df.head()

# output csv
df.to_csv('actors.csv', index=False)
files.download('actors.csv')

names_si = df['names_si'].tolist()
names_en = df['names_en'].tolist()
meta_data = {'actors_si': names_si, 'actors_en': names_en}
meta_data = json.dumps(meta_data)

with open('actor_meta_all.json', 'w') as f:
    f.write(meta_data)

files.download('actor_meta_all.json')
