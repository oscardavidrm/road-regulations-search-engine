"""conector.py - One stop connector for external
services/databases"""
import requests  # pylint: disable=import-error
import logging
import numpy as np  # pylint: disable=import-error
import pymongo
import constants
import env

logging.basicConfig(level=logging.INFO)
db = pymongo.MongoClient('mongodb://localhost:27017/')

articles_in_memory = {}
keywords_in_memory = {}


def get_documents_to_parse():
    # When database is integrated, this will go away
    document_list = []
    document_list.append(constants.mty_document)
    return document_list


def get_keywords(text):
    """Get keywords that relate to this article (from NLP service)
    Args:
        text (sting): text to extract keywords from
    Returns:
        [list]: list of extracted keywords
    """
    extracted_keywords = []
    request = {'text': text}
    nlp_output = requests.post(env.get_keywords_endpoint(), json=request)
    json_output = nlp_output.json()
    if 'error' in json_output:
        raise Exception(json_output['error']['message'])
    for keyword in json_output["tokens"]:
        extracted_keywords.append(keyword["lemma"])
    return extracted_keywords


def get_article_by_number(art_num):
    if art_num in articles_in_memory:
        return articles_in_memory[art_num]
    return None


def get_articles_that_match_keywords(keywords_list):
    """Returns articles that match the the given keyword(s)

    Args:
        keywords_list (list): Keyword(s) to look for

    Returns:
        list: articles that match such keyword(s)
    """
    matching_articles = {}
    for keyword in keywords_list:
        articles_that_match_keyword = {}
        if keyword in keywords_in_memory:
            for article in keywords_in_memory[keyword]:
                articles_that_match_keyword[str(article["id"])] = {"weight": article["frequency"]}
        matching_articles[keyword] = articles_that_match_keyword
    return matching_articles


def get_articles_by_tfidf_value(keywords_list):
    """
    Returns a value for every article based on a keyword
    for a keyword list, value is based on
    term frequency inverse document frequency (tfidf)
    Args:
        keywords_list (list): Keyword(s) to look for

    Returns:
        list: articles and value for such keyword(s)
    """
    matching_articles = {}
    total_articles = db['search-engine']['articles'].count({})
    for keyword in keywords_list:
        articles_that_match_keyword = {}
        total_keywords = db['search-engine']['keywords'].count({})
        if db['search-engine']['keywords'].count({'name': keyword}) > 0:
            for article in db['search-engine']['keywords'].find_one({'name': keyword})['articles']:
                # tfidf computation
                article_dict = db['search-engine']['articles'].find_one({'number': article["number"]})
                term_density_in_article = article["frequency"]/article_dict['wordCount']
                document_frequency = total_articles/total_keywords
                inverse_doc_freq = np.log(document_frequency)
                weight = term_density_in_article * inverse_doc_freq
                articles_that_match_keyword[str(article["number"])] = {"weight": weight}
        matching_articles[keyword] = articles_that_match_keyword
    return matching_articles


def save_keywords_in_memory(keywords, article):
    """Saves the keywords from an article in memory

    Args:
        keywords (JSON): contains keywords
        article (Article): article object
    """
    for keyword in keywords:
        frequency = article["content"].count(keyword)
        if keyword not in keywords_in_memory:
            keywords_in_memory[keyword] = []
        keywords_in_memory[keyword].append({
            "number": article["number"],
            "id": article["id"],
            "frequency": frequency
        })


def store_article(article_dict):
    articles_in_memory[article_dict["id"]] = article_dict
    save_keywords_in_memory(get_keywords(article_dict["content"]), article_dict)
    logging.info('Article ' + article_dict["id"] + ' assigned keywords')
