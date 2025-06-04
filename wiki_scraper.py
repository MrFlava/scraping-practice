import re
import json

import  requests
from pymongo.collection import  Collection
from bs4 import BeautifulSoup
from typing_extensions import Optional, List

from db_utils import DbUtils
from settings import (
    HALL_OF_FAME_FILE_PATH,
    WIKI_ROCK_HALL_OF_FAME,
    WIKI_MAIN_URL,
    BAND_NAME_VARIANTS,
    NON_PARSING_ELEMENTS,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_HALL_OF_FAME_BANDS_COLLECTION,
    DB_HALL_OF_FAME_PERFORMERS_COLLECTION,
)
from replacers import REPLACE_BIRTH_PLACE_ELEMENTS, REPLACE_OCCUPATION_ELEMENTS, DEATH_DATE_ELEMENTS, DEATH_PLACE_ELEMENTS

# Needs to scrap all urls of the performers or members of band (including band names).
# Then scrap all the info about performers and store it into Db


def parse_persons(performers: list, persons: list, soup: BeautifulSoup):
    for person in persons:
        url = soup.find_all('a', attrs={'title': person})[0]
        performers.append({'performer': person, 'url': WIKI_MAIN_URL+url['href']})

def parse_band_members(band_performers: list, bands: list, soup: BeautifulSoup):

    for band in bands:

        if band in BAND_NAME_VARIANTS.keys():
            band = BAND_NAME_VARIANTS[band]

        url = WIKI_MAIN_URL+soup.find_all('a', attrs={'title': band})[0]['href']
        band_soup = BeautifulSoup(requests.get(url).text)
        table_soup =  band_soup.find('table', attrs={'class': 'infobox vcard plainlist'}).find_all('tr')

        members_main = []
        for row in table_soup:
            th_row = row.find('th', attrs={'class': 'infobox-label'})
            unparsed_members = []
            if th_row:

                if th_row.text == "Past members" or th_row.text == "Members":
                    unparsed_members += row.find_all('a')

            for member in unparsed_members:
                if member.text not in NON_PARSING_ELEMENTS:
                    members_main.append({
                        'name': member['title'],
                        'url': WIKI_MAIN_URL+member['href']
                    })


        band_performers.append({'band_name': band, 'members': members_main})

def mine_urls() -> tuple[list, list]:
    performers = []
    band_performers = []

    response = requests.get(WIKI_ROCK_HALL_OF_FAME).text

    with open(HALL_OF_FAME_FILE_PATH, 'r') as file:
        hall_of_fame_data = json.load(file)

    soup = BeautifulSoup(response, 'html.parser')
    persons = hall_of_fame_data.get('persons')
    bands = hall_of_fame_data.get('bands')

    print('start to mine persons')
    parse_persons(performers, persons, soup)
    print(f'mine persons finished, length: {len(persons)}')

    print('start to mine band members')
    parse_band_members(band_performers, bands, soup)
    print(f'mine band members finished, length: {len(band_performers)}')

    return performers, band_performers

def insert_performers_into_db(performers: list, db_collection: str):
    db_utils = DbUtils(DB_HOST, DB_PORT, DB_NAME, db_collection)

    collection = db_utils.get_collection()
    collection.insert_many(performers)


def get_performers_collection(db_collection: str) -> Collection:
    db_utils = DbUtils(DB_HOST, DB_PORT, DB_NAME, db_collection)

    return db_utils.get_collection()

def get_performers_from_db(db_collection: Collection, query: Optional[str]) -> list:
    performers = db_collection.find(query).to_list()
    return performers

def get_table_soup(soup: BeautifulSoup) -> BeautifulSoup:
    table_soup = soup.find('table', attrs={'class': 'infobox biography vcard'})

    if not table_soup:
        return  soup.find('table', attrs={'class': 'infobox vcard plainlist'})

    return table_soup

def get_birthplace(soup: BeautifulSoup, performer_url: Optional[str]) -> str:
    birthplace = soup.find('div', class_='birthplace')

    if not birthplace:
        source_edit_soup = BeautifulSoup(requests.get(performer_url+'?action=edit&veswitched=1').text)
        textarea_edit_soup = source_edit_soup.find(
            'textarea',
            attrs= {'id':'wpTextbox1'}
        )
        textarea_edit_text = textarea_edit_soup.get_text()
        birth_place_unparsed = re.search(r'birth_place (.*)', textarea_edit_text)
        birth_place = birth_place_unparsed[0]

        for k,v in REPLACE_BIRTH_PLACE_ELEMENTS.items():
            birth_place = birth_place.replace(k, v)

        return birth_place

    return birthplace.text

def get_nickname(soup: BeautifulSoup, name: str) -> str:
    nickname = soup.find('div', class_='nickname')

    if not nickname:
        return name

    return nickname.text.replace('[a]', '')

def get_birth_day(soup: BeautifulSoup, performer_url: str) -> str:
    birth_day = soup.find('span', class_='bday')

    if not birth_day:
        source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1').text)
        textarea_edit_soup = source_edit_soup.find(
            'textarea',
            attrs= {'id':'wpTextbox1'}
        )
        textarea_edit_text = textarea_edit_soup.get_text()
        birth_day_unparsed = re.search(r'birth_date (.*)', textarea_edit_text)

        return birth_day_unparsed[0].replace('  ', '').replace('birth_date = ', '')
    return birth_day.text

def get_died_date(performer_url: str) -> str:
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1').text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    death_day_unparsed = re.search(r'death_date (.*)', textarea_edit_text)

    if death_day_unparsed:
        death_str = death_day_unparsed[0]

        for k, v in DEATH_DATE_ELEMENTS.items():
            death_str = death_str.replace(k, v)

        if death_str:
            death_date_list = death_str.split('|')
            death_date_list.pop(0)

            death_str = '-'.join(death_date_list[0:3])

        return death_str

    return ''

def get_occupations(performer_url: str) -> List[str]:
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1').text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    occupations_unparsed = re.search(r'occupation (.*)', textarea_edit_text)
    if occupations_unparsed:
        occupations_str = occupations_unparsed[0]

        for k, v in REPLACE_OCCUPATION_ELEMENTS.items():
            occupations_str = occupations_str.replace(k, v)

        occupations_str = occupations_str[1:] if occupations_str[0] == ',' else occupations_str
        if occupations_str != '':
            return [occupation for occupation in occupations_str.split(',')]
    return []

def get_genres(performer_url: str) -> List[str]:
    pass

def get_death_place(performer_url: str) -> str:
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1').text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    death_place_unparsed = re.search(r'death_place (.*)', textarea_edit_text)

    if death_place_unparsed:
        death_place_str = death_place_unparsed[0]

        for k, v in DEATH_PLACE_ELEMENTS.items():
            death_place_str = death_place_str.replace(k, v)

        return death_place_str

    return ''

def get_years_activity(performer_url: str) -> str:
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1').text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    years_active_unparsed = re.search(r'years_active (.*)', textarea_edit_text)

    return ''

def mine_performers_wiki_data(performers: list) -> list:

    for performer in performers:
        url = performer.get('url')
        soup = BeautifulSoup(requests.get(url).text)
        table_soup = get_table_soup(soup)
        died_date = get_died_date(url)
        died_place = get_death_place(url)
        years_active = get_years_activity(url)

        print(url)
        personal_info = {
            "birthplace": get_birthplace(table_soup, url),
            "birth_day": get_birth_day(table_soup, url),
            "genres": [],
            "years_active": years_active,
            "occupations": get_occupations(url),
            "nickname": get_nickname(table_soup, performer.get('performer'))
        }

        if died_date:
            personal_info.update({'died_date': died_date})

        if died_place:
            personal_info.update({'died_place': died_place})

        print(personal_info)

def hall_of_fame_links_miner():
    print('start to mine')
    performers, band_performers = mine_urls()
    print('start to insert into db')
    insert_performers_into_db(performers, DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    insert_performers_into_db(band_performers, DB_HALL_OF_FAME_BANDS_COLLECTION)
    print('done')



def main():
    # hall_of_fame_links_miner()
    performers_collection =  get_performers_collection(DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    performers_list = get_performers_from_db(performers_collection, None)

    mine_performers_wiki_data(performers_list)


if __name__ == '__main__':
    main()