#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def query_the_sessions(tune_name):
    ret = []
    split_name = [word.lower() for word in tune_name.split()]
    url = f"https://thesession.org/tunes/search?q={split_name.pop(0)}"

    for word in split_name:
        url += f"+{word}"

    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    tune_items = soup.find_all('li', class_='manifest-item')

    print(f"Found {len(tune_items)} tunes matching your query.")
    for tune_data in tune_items:
        # print(tune_data.prettify())

        id = tune_data.find("a-preview").get("data-tuneid")
        name_and_alt = tune_data.find_all('a')
        name = name_and_alt[0] if len(name_and_alt) == 1 else \
            f"{name_and_alt[0]} {name_and_alt[1]}"
        
        ret.append({"name" : name, "id": id})

    return ret

        

def get_abc(tune_id):
    url = f"https://thesession.org/tunes/{tune_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    #divs = soup.find_all('div', class_='setting-abc')
    divs = soup.find_all('div', class_='notes')
    for div in divs:
        print(div.text)
        #print(div.prettify())

def get_abc_by_name(name):
    tunes = query_the_sessions(name)
    get_abc(tunes[0]['id'])

get_abc_by_name("the lark in the morning")

