# Elasticsearch Sinhala Actors Search Engine

This repository contains the source code for a search engine that can be used to query Sri Lankan actors/actresses. The information retrieval system was created using Elasticsearch and Python.

## Directory Structure

```
├── actor-corpus : data scraped from Wikipedia (https://en.wikipedia.org/wiki/List_of_Sri_Lankan_actors)                    
    ├── actors.json : processed actors' data 
    ├── actors_original.csv : original data scraped form the website
    ├── actors_meta_all.json : meta data related to actors
    └── actors_links.csv : contain all links to actors' pages
├── templates : UI related files  
├── app.py : Backend of the web app created using Flask 
├── data_upload.py : File to upload data to Elasticsearch
├── scraper.py :  Source code for the data scraper  
├── search.py : Search functions for processing user queries and returning results
├── queries.txt :  Example queries supported by search engine  
├── config.py :  ES configuration with host, port, and index name        
```

## Data Fields

Each actor entry contains the following data fields. <br /> All text fields are included in both languages English and Sinhala. Summary, personal information and career are long text fields

* Name
* Birthday
* Gender
* Summary
* Personal Information
* Parents
* Education
* Career
* Movies
* Views

## Data Scraping

The data scraping process was done starting from the Wikipedia page [List of Sri Lankan actors - Wikipedia](https://en.wikipedia.org/wiki/List_of_Sri_Lankan_actors).
The Python package BeautifulSoup was used for parsing HTML documents. Next, the scraped data was processed and refined using both simple techniques such as replacements and complex methods using regex expressions. The cleaned data that is produced during the text processing phase is then passed into the translator to be translated into Sinhala. Here both translation and transliteration takes place. Then the translated data is post processed to create the data in necessary formats and the final aggregated dataset containing all required actor information is generated.

Note: The scraper code in ```scraper.py``` was originally written and executed in Google Colaboratory. You can visit it [here](https://colab.research.google.com/drive/1EQsLLQgj6U7eADus8jw39x4NE2BcIjce?usp=sharing). 

![](images/Scraping.png)

## Search Process

Elasticsearch was used for indexing and querying where the standard indexing methods, mapping and the analyzer of Elasticsearch were used. The user query is first pre-processed and passed through an intent classification unit where the intent of the query is identified. Inside the intent classifier, stop words are removed. Then the similarity of the resulting query words is checked against a list of synonyms using TF-IDF vectorization and cosine similarity. Using the intent classifier results, the related search query is first checked for spelling corrections, then converted to Elasticsearch query DSL. The user may override the predefined size of results using the query. The final processed query including facet filters, if any, is executed in Elasticsearch search engine. The types of queries supported fall under the following 4 categories.

```
* Type 1: Field filtered multi-match queries (eg: සාරංගගේ පෞද්ගලික තොරතුරු, සාරංග කොහෙද පාසල් ගියේ?, සාරංගගේ උපන් දිනය කුමක්ද?)

* Type 2: Top search queries (eg: හොඳම නළුවන් සහ නිළියන් 10 දෙනා, ජනප්‍රියම නිළියන් 10 දෙනා)

* Type 3: Phrase queries (eg: "තරුණ චූටි", "මල් හතයි")

* Type 4: Open type multi-match queries (eg: සාරංග දිසාසේකර, මල් හතයි, පබා)
```

For more example queries, refer to ```queries.txt``` file

## Advanced Features

The following advanced features were integrated

* Text mining and text preprocessing 
  * User search queries are preprocessed prior to intent classification. For field-filtered queries, stop words and punctuation are removed to obtain the keywords. Spell correction is also done. During the post processing phase the extracted data is cleaned and processed to be displayed on the web app.<br /> 
  <br /> 
* Intent Classification 
  * After preprocessing, the query is passed to an intent classification unit to extract the user intent. Here the intent can be related to the 4 types of queries supported by the system. Word tokenization, TF-IDF vectorization and cosine similarity are used to classify intents.<br /> 
  <br /> 
* Faceted Search
  * Faceted search is supported for actor name and gender where the returned results can be filtered using facets displayed on the web app.<br />
  <br /> 
* Synonyms support
  * Synonyms support is guaranteed where analogous queries such as ‘සාරංග දිසාසේකර කොහෙද පාසල් ගියේ?’ and ‘සාරංග දිසාසේකර ඉගෙනගත්තේ කොහේද?’ will map to the same result. Also the top search queries can use similar words such as හොඳ, ජනප්‍රිය, ප්‍රසිද්ධ, etc.<br /> 
  <br /> 
* Resistance to simple spelling errors
  * The use of TF-IDF vectorization and cosine similarity calculation ensures that simple spelling errors generate the same result as expected.

![](images/Search.jpg)
