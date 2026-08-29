import re
import json
import resource

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
from replacers import (
    REPLACE_BIRTH_PLACE_ELEMENTS,
    REPLACE_OCCUPATION_ELEMENTS,
    DEATH_DATE_ELEMENTS,
    DEATH_PLACE_ELEMENTS,
    YEARS_ACTIVE_ELEMENTS,
    GENRES_ELEMENTS,
    normalize_genre_string
)

# Needs to scrap all urls of the performers or members of band (including band names).
# Then scrap all the info about performers and store it into Db


def parse_persons(performers: list, persons: list, soup: BeautifulSoup):
    for person in persons:
        url = soup.find_all('a', attrs={'title': person})[0]
        performers.append({'performer': person, 'url': WIKI_MAIN_URL+url['href']})

def parse_band_members(band_performers: list, bands: list, soup: BeautifulSoup):
    def get_band_url(band: str) -> str:
        if band in BAND_NAME_VARIANTS:
            band = BAND_NAME_VARIANTS[band]
        return WIKI_MAIN_URL + soup.find('a', attrs={'title': band})['href']

    def fetch_band_soup(url: str) -> BeautifulSoup:
        response = requests.get(url)
        return BeautifulSoup(response.text, 'html.parser')

    def extract_members(table_soup: BeautifulSoup) -> list:
        members = []
        rows = table_soup.find_all('tr')
        for row in rows:
            th_row = row.find('th', attrs={'class': 'infobox-label'})
            if th_row and th_row.text in {"Past members", "Members"}:
                unparsed_members = row.find_all('a')
                for member in unparsed_members:
                    if member.text not in NON_PARSING_ELEMENTS:
                        members.append({
                            'name': member['title'],
                            'url': WIKI_MAIN_URL + member['href']
                        })
        return members

    for band in bands:
        band_url = get_band_url(band)
        band_soup = fetch_band_soup(band_url)
        table_soup = band_soup.find('table', attrs={'class': 'infobox vcard plainlist'})
        if table_soup:
            members = extract_members(table_soup)
            band_performers.append({'band_name': band, 'members': members})

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

def update_db_performers_info(performer_data: dict, db_collection: str):
    db_utils = DbUtils(DB_HOST, DB_PORT, DB_NAME, db_collection)

    collection = db_utils.get_collection()
    updated_doc = collection.find_one_and_update(
        {"url": performer_data['url']},
        {"$set": performer_data.get("personal_info")}
    )

    return f"Updated document: {updated_doc}"


def get_performers_collection(db_collection: str) -> Collection:
    db_utils = DbUtils(DB_HOST, DB_PORT, DB_NAME, db_collection)

    return db_utils.get_collection()

def get_performers_from_db(db_collection: Collection, query: Optional[str]) -> list:
    performers = db_collection.find(query).to_list()
    return performers

def parse_wiki_text_personal_info(text: str):
    def extract_nickname(text: str) -> Optional[str]:
        match = re.search(r"'''[^']*\"([^\"]+)\"[^']*'''", text)
        return match.group(1) if match else None

    def normalize_date(month: str, day: str, year: str) -> str:
        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        return f"{year}-{months.get(month.lower(), '00')}-{day.zfill(2)}"

    def extract_birth_and_death_dates(text: str) -> dict:
        info = {}
        range_re = re.compile(
            r"\(\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*(?:&ndash;|&mdash;|–|—|-)\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*\)",
            re.IGNORECASE
        )
        match = range_re.search(text)
        if match:
            b_mon, b_day, b_year, d_mon, d_day, d_year = match.groups()
            info['birth_day'] = normalize_date(b_mon, b_day, b_year)
            info['died_date'] = normalize_date(d_mon, d_day, d_year)
        else:
            birth_match = re.search(r"\(born\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", text, re.IGNORECASE)
            if birth_match:
                mon, day, year = birth_match.groups()
                info['birth_day'] = normalize_date(mon, day, year)
            death_match = re.search(r"died\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", text, re.IGNORECASE)
            if death_match:
                mon, day, year = death_match.groups()
                info['died_date'] = normalize_date(mon, day, year)
        return info

    def extract_birthplace(text: str) -> Optional[str]:
        match = re.search(r"was from \[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
        return match.group(1) if match else None

    def extract_occupations(text: str) -> List[str]:
        occupation_keywords = [
            "drummer", "singer", "songwriter", "musician", "bassist", "guitarist",
            "producer", "composer", "vocalist", "pianist", "saxophonist", "keyboardist",
            "record producer", "engineer", "actor", "conductor", "violinist"
        ]
        pattern = r'(?:[A-Za-z-]+\s)?(?:' + '|'.join(re.escape(k) for k in occupation_keywords) + r')'
        found = set(re.findall(pattern, text, re.IGNORECASE))
        return sorted(found)

    def extract_years_active(text: str) -> Optional[str]:
        match = re.search(r"released several singles in the (\d{4}s and \d{4}s)", text)
        return match.group(1) if match else None

    def extract_genres(text: str) -> List[str]:
        match = re.search(r"American\s+([\w&/-]+)\s+(?:singer|songwriter)", text)
        if match:
            genres = match.group(1).replace("bass", "").replace("male", "").strip()
            return [genres] if genres else []
        return []

    info = {
        'nickname': extract_nickname(text),
        **extract_birth_and_death_dates(text),
        'birthplace': extract_birthplace(text),
        'occupations': extract_occupations(text),
        'years_active': extract_years_active(text),
        'genres': extract_genres(text)
    }

    return {'personal_info': {k: v for k, v in info.items() if v}}

def get_table_soup(soup: BeautifulSoup) -> BeautifulSoup:
    table_soup = soup.find('table', attrs={'class': 'infobox biography vcard'})

    if not table_soup:
        return  soup.find('table', attrs={'class': 'infobox vcard plainlist'})

    return table_soup

def get_birthplace(soup: BeautifulSoup, performer_url: Optional[str]) -> str:
    if not soup:
        return ''

    birthplace = soup.find('div', class_='birthplace')
    if birthplace:
        return birthplace.text.strip()

    # Fetch edit page and parse birthplace
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    edit_soup = BeautifulSoup(response.text, 'html.parser')
    textarea = edit_soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return ''

    birth_place_match = re.search(r'birth_place\s*=\s*(.*)', textarea.get_text())
    if birth_place_match:
        birth_place = birth_place_match.group(1)
        for k, v in REPLACE_BIRTH_PLACE_ELEMENTS.items():
            birth_place = birth_place.replace(k, v)
        return birth_place.strip()

    return ''

def get_nickname(soup: BeautifulSoup, name: str) -> str:
    if not soup:
        return name

    nickname = soup.find('div', class_='nickname')
    if nickname:
        return re.sub(r'\[.*?\]', '', nickname.text).strip()

    return name

def get_birth_day(soup: BeautifulSoup, performer_url: str) -> str:
    if not soup:
        return ''

    # Check for 'bday' span in the soup
    birth_day = soup.find('span', class_='bday')
    if birth_day:
        return birth_day.text

    # If not found, fetch the edit page and parse the birth date
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {'User-Agent': custom_user_agent}
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    edit_soup = BeautifulSoup(response.text, 'html.parser')
    textarea = edit_soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return ''

    # Extract birth date using regex
    birth_date_match = re.search(r'birth_date\s*=\s*\{\{birth date\|(\d{4})\|(\d{2})\|(\d{2,3})\}\}', textarea.get_text())
    if birth_date_match:
        year, month, day = birth_date_match.groups()
        day = day.zfill(2)[-2:]  # Normalize day to two digits
        return f"{year}-{month}-{day}"

    return ''

def get_died_date(performer_url: str) -> str:
    headers = {
        'User-Agent': ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    }
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    textarea = soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return ''

    text = textarea.get_text()
    death_date_match = re.search(r'death_date\s*=\s*\{\{.*?\|(\d{4})\|(\d{2})\|(\d{2})\}\}', text)
    if death_date_match:
        year, month, day = death_date_match.groups()
        return f"{year}-{month}-{day}"

    return ''

def parse_flatlist_occups(wikitext: str) -> list:
    patterns = [
        r'\|\s*occupation\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}',
        r'\|\s*occupation\s*=\s*\{\{flat list\s*\|\s*(.*?)\}\}',
        r'\|\s*occupation\s*=\s*\{\{plainlist\s*\|\s*(.*?)\}\}',
        r'\|\s*occupations\s*=\s*\{\{flat list\s*\|\s*(.*?)\}\}',
        r'\|\s*occupation\s*=\s*\{\{hlist\s*\|\s*(.*?)\}\}',
        r'\|\s*occupations\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}'
    ]

    for pattern in patterns:
        match = re.search(pattern, wikitext, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
            raw_items = re.split(r'\n\*|\*|\n\||\|', content)
            return [
                re.sub(r'\[\[[^|\]]+\|([^\]]+)\]\]|\[\[([^\]]+)\]\]|\{\{.*?\}\}', '', item).strip()
                for item in raw_items if item.strip()
            ]
    return []

def get_occupations(performer_url: str) -> List[str]:
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    edit_soup = BeautifulSoup(response.text, 'html.parser')
    textarea = edit_soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return []

    text = textarea.get_text()
    occupations = parse_flatlist_occups(text)
    if occupations:
        return occupations

    occupation_match = re.search(r'(?:occupation|occupations)\s*=\s*(.*)', text)
    if occupation_match:
        occupations_str = occupation_match.group(1)
        for k, v in REPLACE_OCCUPATION_ELEMENTS.items():
            occupations_str = occupations_str.replace(k, v)
        return [occ.strip() for occ in occupations_str.split(',') if occ.strip()]

    return []


def get_genres(performer_url: str) -> List[str]:
    headers = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                      " (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    edit_soup = BeautifulSoup(response.text, 'html.parser')
    textarea = edit_soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return []

    text = textarea.get_text()
    genre_match = re.search(r'\|\s*genre\s*=\s*\{\{hlist\s*\|(.+?)\}\}', text, re.DOTALL | re.IGNORECASE)
    if genre_match:
        raw_genres = genre_match.group(1)
        raw_genres = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', lambda m: m.group(2) or m.group(1), raw_genres)
        genres = [re.sub(r'\s*\(.*?\)\s*', '', g.strip()) for g in raw_genres.split('|') if g.strip()]
        return list(set(genres))  # Remove duplicates

    return []


def get_death_place(performer_url: str) -> str:
    headers = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36"
    }
    source_edit_soup = BeautifulSoup(
        requests.get(
            performer_url + '?action=edit&veswitched=1',
            headers=headers
        ).text
    )
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    death_place_unparsed = re.search(r'death_place\s*=\s*(.*)', textarea_edit_text)

    if death_place_unparsed:
        death_place_str = death_place_unparsed.group(1)

        for k, v in DEATH_PLACE_ELEMENTS.items():
            death_place_str = death_place_str.replace(k, v)

        # Remove duplicate words
        death_place_str = re.sub(r'\b(\w+)\b\s*(?=.*\b\1\b)', '', death_place_str).strip()

        # Normalize commas and spaces
        death_place_str = re.sub(r'\s*,\s*', ', ', death_place_str)
        death_place_str = re.sub(r'\s+', ' ', death_place_str)

        # Ensure proper formatting for "City, State, Country"
        death_place_str = re.sub(r'(, )+', ', ', death_place_str)

        return death_place_str.replace("WestPhiladelphiaWestPhiladelphia", "West Philadelphia")

    return ''



def get_years_active_flatlist(wikitext: str):
    pattern = re.compile(
        r'\|\s*years_active\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    match = pattern.search(wikitext)

    if not match:
        return []

    content = match.group(1)

    raw_items = re.split(r'\n\*|\*', content)

    years_active = []
    for item in raw_items:
        # Очищення від вікі-посилань: [[Стаття|Текст]] -> Текст
        item = re.sub(r'\[\[[^|\]]+\|([^\]]+)\]\]', r'\1', item)
        # Очищення від простих посилань: [[Стаття]] -> Стаття
        item = re.sub(r'\[\[([^\]]+)\]\]', r'\1', item)
        # Видалення залишків шаблонів та зайвих символів
        item = re.sub(r'\{\{.*?\}\}', '', item)

        clean_name = item.strip()
        if clean_name:
            clean_name = clean_name.replace('{{circa|', '')
            years_active.append(clean_name)

    return ",".join(years_active)

def get_years_activity(performer_url: str) -> str:
    headers = {
        'User-Agent': ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    }
    response = requests.get(f"{performer_url}?action=edit&veswitched=1", headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    textarea = soup.find('textarea', attrs={'id': 'wpTextbox1'})

    if not textarea:
        return ''

    wikitext = textarea.get_text()

    # Check for years active in flatlist format
    years_active = get_years_active_flatlist(wikitext)
    if years_active:
        return years_active

    # Extract years active directly
    match = re.search(r'years_active\s*=\s*(.*)', wikitext, re.IGNORECASE)
    if match:
        years_active = match.group(1).strip()

        # Replace unwanted elements
        for key, value in YEARS_ACTIVE_ELEMENTS.items():
            years_active = years_active.replace(key, value)

        # Normalize spaces and line breaks
        years_active = years_active.replace('<br>', ' ').strip()
        return years_active

    return ''

def mine_performers_wiki_data(performers: list) -> str:
    for performer in performers:
        url = performer.get('url')
        soup = BeautifulSoup(requests.get(url).text)
        table_soup = get_table_soup(soup)
        died_date = get_died_date(url)
        died_place = get_death_place(url)
        years_active = get_years_activity(url)
        genres = get_genres(url)

        personal_info = {
            "birthplace": get_birthplace(table_soup, url),
            "birth_day": get_birth_day(table_soup, url),
            "years_active": years_active,
            "occupations": get_occupations(url),
            "nickname": get_nickname(table_soup, performer.get('performer'))
        }

        if died_date:
            personal_info.update({'died_date': died_date})

        if died_place:
            personal_info.update({'died_place': died_place})

        if genres:
            personal_info.update({'genres': genres})

        performer.update({"personal_info": personal_info})
        # todo check the logic
        update_db_performers_info(performer, DB_HALL_OF_FAME_PERFORMERS_COLLECTION)

    return "All performers are updated"

def mine_bands_wiki_data(bands: list) -> str:
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }

    for band in bands:
        members  = band.get('members')
        print(members)

        for member in members:
            print(member)
            url = member.get('url')
            print(url)
            soup = BeautifulSoup(requests.get(url, headers=headers).text)
            table_soup = get_table_soup(soup)
            died_date = get_died_date(url)
            died_place = get_death_place(url)
            years_active = get_years_activity(url)
            genres = get_genres(url)
            personal_info = {
                "birthplace": get_birthplace(table_soup, url),
                "birth_day": get_birth_day(table_soup, url),
                "years_active": years_active,
                "occupations": get_occupations(url),
                "nickname": get_nickname(table_soup, member.get('performer'))
            }

            if died_date:
                personal_info.update({"died_place": died_place})

            if died_place:
                personal_info.update({"died_date": died_date})

            if genres:
                personal_info.update({"genres": genres})

            member.update({"personal_info": personal_info})
            print(member)



def hall_of_fame_links_miner():
    print('start to mine')
    performers, band_performers = mine_urls()
    print('start to insert into db')
    insert_performers_into_db(performers, DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    insert_performers_into_db(band_performers, DB_HALL_OF_FAME_BANDS_COLLECTION)
    print('done')

def main():
    # hall_of_fame_links_miner()
    # performers_collection =  get_performers_collection(DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    # performers_list = get_performers_froperformers_collectionm_db(, None)
    # print(mine_performers_wiki_data(performers_list))


    band_members_collection = get_performers_collection(DB_HALL_OF_FAME_BANDS_COLLECTION)
    band_members_list =  get_performers_from_db(band_members_collection, None)

    # custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    #                      " Chrome/123.0.0.0 Safari/537.36")
    # headers = {
    #     'User-Agent': custom_user_agent
    # }
    # source_edit_soup = BeautifulSoup(requests.get('https://en.wikipedia.org/wiki/Barbara_Martin_(singer)' + '?action=edit&veswitched=1', headers=headers).text)
    # textarea_edit_soup = source_edit_soup.find(
    #     'textarea',
    #     attrs={'id': 'wpTextbox1'}
    # )
    # textarea_edit_text = textarea_edit_soup.get_text()
    # print(textarea_edit_text)

    # personal_info = parse_wiki_text_personal_info(textarea_edit_text)
    # print(personal_info)
    #
    # birth_place = get_birthplace(soup, performer_url="https://en.wikipedia.org/wiki/John_Entwistle")
    # print(birth_place)
    # birth_date = get_birth_day(source_edit_soup, performer_url='https://en.wikipedia.org/wiki/Barbara_Martin_(singer)')
    # print(birth_date)

    # needs to check
    # genres = get_genres("https://en.wikipedia.org/wiki/Robin_Gibb")
    # print(genres)
    # occups = get_occupations("https://en.wikipedia.org/wiki/John_Lennon")
    # print(occups)

    # died_date = get_died_date("https://en.wikipedia.org/wiki/David_Brown_(American_musician)")
    # print(died_date)

    # died_place = get_death_place("https://en.wikipedia.org/wiki/David_Ruffin")
    # print(died_place)
    # years_active = get_years_activity("https://en.wikipedia.org/wiki/Cindy_Birdsong")
    # print(years_active)
    # nickame = get_nickname(source_edit_soup, 'https://en.wikipedia.org/wiki/Johnny_Moore_(singer)')
    # print(nickame)

    mine_bands_wiki_data(band_members_list)





if __name__ == '__main__':
    main()