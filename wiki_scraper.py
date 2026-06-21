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
    info = {}

    # --- Nickname inside bold name with quotes ---
    nickname_match = re.search(r"'''[^']*\"([^\"]+)\"[^']*'''", text)
    if nickname_match:
        info['nickname'] = nickname_match.group(1)

    # --- Months map and helper ---
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    def _norm_date(mon: str, day: str, year: str):
        m = months.get(mon.lower(), "00")
        return f"{year}-{m}-{day.zfill(2)}"

    # --- Birth and death parsing ---

    # 1) full range with month/day -> (June 5, 1940 – March 15, 1997)
    range_re = re.compile(
        r"\(\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*(?:&ndash;|&mdash;|–|—|-)\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*\)",
        re.IGNORECASE
    )
    m = range_re.search(text)
    if m:
        b_mon, b_day, b_year, d_mon, d_day, d_year = m.groups()
        info['birth_day'] = _norm_date(b_mon, b_day, b_year)
        info['died_date'] = _norm_date(d_mon, d_day, d_year)
    else:
        # 2) born immediately after bolded name with place: '''Name''' (born October 4, 1947 in [[Denton, Texas]])
        bold_born_in = re.search(
            r"'''[^']+'''\s*\(\s*born\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s+in\s+\[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*\)",
            text, re.IGNORECASE
        )
        if bold_born_in:
            mon, day, year, place = bold_born_in.groups()
            info['birth_day'] = _norm_date(mon, day, year)
            info['birthplace'] = place
        else:
            # 3) born immediately after bolded name without place: '''Name''' (born June 5, 1940)
            bold_born_md = re.search(r"'''[^']+'''\s*\(\s*born\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*\)", text, re.IGNORECASE)
            if bold_born_md:
                mon, day, year = bold_born_md.groups()
                info['birth_day'] = _norm_date(mon, day, year)
            else:
                # 4) explicit "born Month day, year anywhere"
                born_md = re.search(r"\(born\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\)", text, re.IGNORECASE)
                if born_md:
                    mon, day, year = born_md.groups()
                    info['birth_day'] = _norm_date(mon, day, year)
                else:
                    # 5) born with place anywhere: (born October 4, 1947 in [[Denton, Texas]])
                    born_in_any = re.search(
                        r"\(\s*born\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s+in\s+\[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*\)",
                        text, re.IGNORECASE
                    )
                    if born_in_any:
                        mon, day, year, place = born_in_any.groups()
                        info['birth_day'] = _norm_date(mon, day, year)
                        info['birthplace'] = place
                    else:
                        # 6) short description / circa / year-only
                        short_desc_circa = re.search(r"\{\{\s*short description\s*\|[^}]*\(born\s*(?:c\.|circa)?\s*(\d{4})\)", text, re.IGNORECASE)
                        if short_desc_circa:
                            info['birth_day'] = short_desc_circa.group(1)
                        else:
                            born_year = re.search(r"\(?\s*born\s*(?:c\.|c|circa)?\s*(\d{4})\s*\)?", text, re.IGNORECASE)
                            if born_year:
                                info['birth_day'] = born_year.group(1)
                            else:
                                # fallback: single parenthetical birth like (June 5, 1940)
                                single_birth = re.search(r"\(\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*\)", text)
                                if single_birth:
                                    mon, day, year = single_birth.groups()
                                    info['birth_day'] = _norm_date(mon, day, year)

        # also attempt to extract a death-only date if present outside range
        if 'died_date' not in info:
            died_single = re.search(r"died\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", text, re.IGNORECASE)
            if died_single:
                mon, day, year = died_single.groups()
                info['died_date'] = _norm_date(mon, day, year)

    # --- Birthplace from "was from [[Place]]" if not already set ---
    if 'birthplace' not in info:
        origin_match = re.search(r"was from \[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
        if origin_match:
            info['birthplace'] = origin_match.group(1)

    # --- Occupations: existing heuristic (unchanged) ---
    occupation_keywords = [
        "drummer", "singer", "songwriter", "musician", "bassist", "guitarist",
        "producer", "composer", "vocalist", "pianist", "saxophonist", "keyboardist",
        "record producer", "engineer", "actor", "actor/producer", "conductor", "violinist"
    ]
    occ_kw_pattern = r'(?:[A-Za-z-]+\s)?(?:' + '|'.join(re.escape(k) for k in occupation_keywords) + r')'
    found_occs = []

    short_desc_match = re.search(r'\{\{\s*short description\s*\|\s*([^|\}]+)', text, re.IGNORECASE)
    if short_desc_match:
        desc = short_desc_match.group(1).strip()
        desc = re.sub(r'\s*\(.*\)\s*$', '', desc).strip()
        m = re.search(r'(' + occ_kw_pattern + r')', desc, re.IGNORECASE)
        if m:
            found_occs.append(m.group(1).strip())

    lead_match = re.search(r"'''[^']+'''\s*(?:\([^)]*\)\s*)?is\s+an?\s+([^.]+?)\.", text, re.IGNORECASE)
    if lead_match:
        lead = lead_match.group(1).strip()
        m = re.search(r'(' + occ_kw_pattern + r')', lead, re.IGNORECASE)
        if m:
            found_occs.append(m.group(1).strip())

    for link_target, link_label in re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', text):
        token = (link_label or link_target).strip()
        m = re.search(r'(' + occ_kw_pattern + r')', token, re.IGNORECASE)
        if m:
            found_occs.append(m.group(1).strip())

    try:
        flat_items = parse_flatlist_occups(text)
    except Exception:
        flat_items = []
    if flat_items:
        for it in flat_items:
            if it and it not in found_occs:
                found_occs.append(it.strip())

    nationalities = {'american', 'british', 'english', 'canadian', 'australian', 'irish', 'scottish'}
    cleaned = []
    seen = set()
    for o in found_occs:
        o_norm = o.lower().strip()
        o_norm = re.sub(r'\(.*?\)', '', o_norm).strip()
        o_norm = re.sub(r'[^a-z0-9\s\-]', '', o_norm)
        parts = o_norm.split()
        if parts and parts[0] in nationalities:
            parts = parts[1:]
        o_norm = ' '.join(parts).strip()
        if o_norm and o_norm not in seen:
            seen.add(o_norm)
            cleaned.append(o_norm)

    if cleaned:
        info['occupations'] = cleaned

    # --- Years Active (existing) ---
    years_match = re.search(r"released several singles in the (\d{4}s and \d{4}s)", text)
    if years_match:
        info['years_active'] = years_match.group(1)

    # --- Genres (existing) ---
    genre_match = re.search(r"American\s+([\w&/-]+)\s+(?:singer|songwriter)", text)
    if genre_match:
        genres = genre_match.group(1).replace("bass", "").replace("male", "")
        info['genres'] = []
        if genres:
            info['genres'].append(genres)

    return {'personal_info': info}



def get_table_soup(soup: BeautifulSoup) -> BeautifulSoup:
    table_soup = soup.find('table', attrs={'class': 'infobox biography vcard'})

    if not table_soup:
        return  soup.find('table', attrs={'class': 'infobox vcard plainlist'})

    return table_soup

def get_birthplace(soup: BeautifulSoup, performer_url: Optional[str]) -> str:
    if soup:
        birthplace = soup.find('div', class_='birthplace')
        # todo fix this url https://en.wikipedia.org/wiki/Dub_Jones_(singer)
        custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                             " Chrome/123.0.0.0 Safari/537.36")
        headers = {
            'User-Agent': custom_user_agent
        }
        if not birthplace:
            source_edit_soup = BeautifulSoup(requests.get(performer_url+'?action=edit&veswitched=1', headers=headers).text)
            textarea_edit_soup = source_edit_soup.find(
                'textarea',
                attrs= {'id':'wpTextbox1'}
            )
            textarea_edit_text = textarea_edit_soup.get_text()

            birth_place_unparsed = re.search(r'birth_place (.*)', textarea_edit_text)
            if birth_place_unparsed:
                birth_place = birth_place_unparsed[0]

                for k,v in REPLACE_BIRTH_PLACE_ELEMENTS.items():
                    birth_place = birth_place.replace(k, v)

                return birth_place
            else:
                return ''

        return birthplace.text

    else:
        return ''

def get_nickname(soup: BeautifulSoup, name: str) -> str:
    if soup:
        nickname = soup.find('div', class_='nickname')

        if not nickname:
            return name

        return nickname.text.replace('[a]', '').replace('[citation needed]', '').replace('[1]', '')
    else:
        return ''

def get_birth_day(soup: BeautifulSoup, performer_url: str) -> str:
    if soup:
        birth_day = soup.find('span', class_='bday')

        custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                             " Chrome/123.0.0.0 Safari/537.36")
        headers = {
            'User-Agent': custom_user_agent
        }

        if not birth_day:
            source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
            textarea_edit_soup = source_edit_soup.find(
                'textarea',
                attrs= {'id':'wpTextbox1'}
            )
            textarea_edit_text = textarea_edit_soup.get_text()
            print(textarea_edit_text)
            birth_day_unparsed = re.search(r'birth_date (.*)', textarea_edit_text)
            return birth_day_unparsed[0].replace('  ', '').replace('birth_date = ', '').replace('birth_date= June 30, 1941', '1941-06-30').replace('birth_date= June 7, 1944', '1944-07-30')
        return birth_day.text

    else:
        return ''

def get_died_date(performer_url: str) -> str:
    print(performer_url + '?action=edit&veswitched=1')
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )
    if not textarea_edit_soup:
        print(performer_url + '?action=edit&veswitched=1')
    textarea_edit_text = textarea_edit_soup.get_text()

    death_day_unparsed = re.search(r'death_date (.*)', textarea_edit_text)
    death_day_unparsed_v2 = re.search(r'death_date=(.*)', textarea_edit_text)

    if death_day_unparsed:
        death_str = death_day_unparsed[0]

        for k, v in DEATH_DATE_ELEMENTS.items():
            death_str = death_str.replace(k, v)

        if death_str:
            death_date_list = death_str.split('|')
            if death_date_list[0] == '  November 8, 2011 (aged&nbsp;74)':
                return "2011-11-08"
            death_date_list.pop(0)
            if death_date_list[0] != '':
                if death_date_list[0] != "mfyes":
                    if death_date_list[0] == "dfy":
                        death_str = '-'.join(death_date_list[1:4])
                    else:
                        death_str = '-'.join(death_date_list[0:3])
                else:

                    death_str = '-'.join(death_date_list[1:4])
            else:
                if death_date_list[0] == '' and death_date_list[1] == '':
                    death_str = '-'.join(death_date_list[2:5])
                else:
                    death_str = '-'.join(death_date_list[1:4])

        return death_str

    elif death_day_unparsed_v2:

        death_str = death_day_unparsed_v2[0]

        for k, v in DEATH_DATE_ELEMENTS.items():
            death_str = death_str.replace(k, v)

        if death_str:
            death_date_list = death_str.split('|')
            death_date_list.pop(0)

            death_str = '-'.join(death_date_list[0:3])

        return death_str

    return ''

def parse_flatlist_occups(wikitext: str):
    pattern = re.compile(
        r'\|\s*occupation\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern2 = re.compile(
        r'\|\s*occupation\s*=\s*\{\{flat list\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern3 = re.compile(
        r'\|\s*occupation\s*=\s*\{\{plainlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern4 = re.compile(
        r'\|\s*occupations\s*=\s*\{\{flat list\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern5 = re.compile(
        r'\|\s*occupation\s*=\s*\{\{hlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern6 = re.compile(
        r'\|\s*occupations\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    pattern7 = re.compile(
        r'\|\s*occupations\s*=\s*\{\{flatlist\s*\|\s*(.*?)\}\}',
        re.DOTALL | re.IGNORECASE
    )

    match = pattern.search(wikitext) or pattern2.search(wikitext) or pattern3.search(wikitext) or pattern4.search(wikitext) or pattern5.search(wikitext) or pattern6.search(wikitext) or pattern7.search(wikitext)
    if not match:
        return []

    content = match.group(1)

    raw_items = re.split(r'\n\*|\*|\n\||\|', content)

    occupations = []
    for item in raw_items:
        # remove leading/trailing whitespace and any leftover separators
        item = item.strip().lstrip('|').lstrip('*').strip()

        # Очищення від вікі-посилань: [[Стаття|Текст]] -> Текст
        item = re.sub(r'\[\[[^|\]]+\|([^\]]+)\]\]', r'\1', item)
        # Очищення від простих посилань: [[Стаття]] -> Стаття
        item = re.sub(r'\[\[([^\]]+)\]\]', r'\1', item)
        # Видалення залишків шаблонів та зайвих символів
        item = re.sub(r'\{\{.*?\}\}', '', item)

        clean_name = item.strip()
        if clean_name:
            clean_name = clean_name.replace('{{nowrap|', '')
            occupations.append(clean_name)

    return occupations

def get_occupations(performer_url: str) -> List[str]:
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    flatlist_occupations = parse_flatlist_occups(textarea_edit_text)

    if flatlist_occupations:
        return flatlist_occupations

    occupations_unparsed = re.search(r'occupation (.*)', textarea_edit_text)

    occupations_unparsed_v2 = re.search(r'occupations (.*)', textarea_edit_text)

    if occupations_unparsed:
        occupations_str = occupations_unparsed[0]
        for k, v in REPLACE_OCCUPATION_ELEMENTS.items():
            occupations_str = occupations_str.replace(k, v)

        if occupations_str == '':
            return []
        occupations_str = occupations_str[1:] if occupations_str[0] == ',' else occupations_str
        if occupations_str != '':
            return [occupation for occupation in occupations_str.split(',') if occupation]
    elif occupations_unparsed_v2:
        occupations_str = occupations_unparsed_v2[0]
        for k, v in REPLACE_OCCUPATION_ELEMENTS.items():
            occupations_str = occupations_str.replace(k, v)

        if occupations_str == '':
            return []
        occupations_str = occupations_str[1:] if occupations_str[0] == ',' else occupations_str
        if occupations_str != '':
            return [occupation for occupation in occupations_str.split(',') if occupation]
    return []

def get_genres(performer_url: str) -> List[str]:
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )
    genre_list = []

    textarea_edit_text = textarea_edit_soup.get_text()
    # simple inline genre line (now expects possible '=')
    genre_unparsed_usual = re.search(r'genre\s*=\s*(.*)', textarea_edit_text, re.IGNORECASE)

    # flatlist / flat list / hlist variants (capture inner content across lines)
    genre_unparsed_Flist = re.search(r'genre\s*=\s*\{\{Flatlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL | re.IGNORECASE)
    genre_unparsed_flist = re.search(r'genre\s*=\s*\{\{flatlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL | re.IGNORECASE)
    # handle `{{flat list|` with optional spaces between "flat" and "list"
    genre_unparsed_flat_space = re.search(r'genre\s*=\s*\{\{\s*flat\s*list\s*\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL | re.IGNORECASE)

    genre_unparsed_hlist = re.search(r'genre\s*=\s*\{\{hlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL | re.IGNORECASE)
    genre_unparsed_Hlist = re.search(r'genre\s*=\s*\{\{Hlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL | re.IGNORECASE)

    genre_unparsed = next((v for v in [
        genre_unparsed_Flist,
        genre_unparsed_flist,
        genre_unparsed_flat_space,
        genre_unparsed_hlist,
        genre_unparsed_Hlist
    ] if v is not None), None)

    # helper to extract wikilink label/target safely
    def _wikilink_label(m):
        target = m.group(1)
        label = m.group(2)
        out = (label or target)
        out = out.split('/')[-1].split(':')[-1].strip()
        out = re.sub(r'\bmusic\b', '', out, flags=re.IGNORECASE).strip()
        out = re.sub(r'\s*\(.*?\)\s*', '', out).strip()
        return out

    # separators: include pipe as separator but only after wikilinks/templates are replaced
    split_re = r'\s*\|\s*|\s*,\s*|/|;|\n'

    if genre_unparsed:
        # captured inner flatlist content (may contain bullets/lines)
        genre_unparsed_list = genre_unparsed.group(1).splitlines()
        seen = set()
        for genre_unparsed_line in genre_unparsed_list:
            line = genre_unparsed_line.strip()
            if not line:
                continue
            # replace wikilinks with labels first (so internal `|` from `[[a|b]]` won't remain)
            line = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', _wikilink_label, line)
            # remove templates (multi-line aware)
            line = re.sub(r'\{\{.*?\}\}', '', line, flags=re.DOTALL)
            # split by common separators including pipe
            tokens = re.split(split_re, line)
            for t in tokens:
                t = t.strip()
                if not t:
                    continue
                t = re.sub(r'[\[\]]', '', t)
                t = re.sub(r'\s*\(.*?\)\s*', '', t)
                t = re.sub(r'\s+music\b', '', t, flags=re.IGNORECASE)
                t = re.sub(r'\s+', ' ', t).strip()
                norm = normalize_genre_string(t)
                mapped = GENRES_ELEMENTS.get(norm) or GENRES_ELEMENTS.get(t.lower())
                if mapped:
                    items = [g.strip() for g in mapped.split(',')] if "," in mapped else [mapped.strip()]
                else:
                    items = [t]
                for it in items:
                    it_clean = it.replace('=', '').replace('*', '').strip()
                    if it_clean and it_clean not in seen:
                        seen.add(it_clean)
                        genre_list.append(it_clean)

    elif genre_unparsed_usual:
        raw = genre_unparsed_usual.group(1).strip()

        # remove HTML tags and references
        raw = re.sub(r'<ref[^>]*>.*?</ref>', '', raw, flags=re.DOTALL)
        raw = re.sub(r'<.*?>', '', raw)

        # replace wikilinks with their labels before splitting so "and" or internal `|` inside a link doesn't split
        raw = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', _wikilink_label, raw)
        # remove templates (multi-line aware)
        raw = re.sub(r'\{\{.*?\}\}', '', raw, flags=re.DOTALL)

        # split on common separators: pipe, comma, slash, semicolon, newlines
        tokens = re.split(split_re, raw)

        seen = set()

        for t in tokens:
            t = t.strip()
            if not t:
                continue

            # basic cleaning
            t = re.sub(r'[\[\]]', '', t)
            t = re.sub(r'\s*\(.*?\)\s*', '', t)
            t = re.sub(r'\s+music\b', '', t, flags=re.IGNORECASE)
            t = re.sub(r'\s+', ' ', t).strip()

            if not t:
                continue

            norm = normalize_genre_string(t)
            mapped = GENRES_ELEMENTS.get(norm) or GENRES_ELEMENTS.get(t.lower())

            if mapped:
                items = [g.strip() for g in mapped.split(',')] if "," in mapped else [mapped.strip()]
            else:
                items = [t]

            for it in items:
                it_clean = it.replace('=', '').strip()
                if it_clean and it_clean not in seen:
                    seen.add(it_clean)
                    genre_list.append(it_clean)

    return genre_list




def get_death_place(performer_url: str) -> str:
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    death_place_unparsed = re.search(r'death_place (.*)', textarea_edit_text)
    print(death_place_unparsed)

    if death_place_unparsed:
        death_place_str = death_place_unparsed[0]

        for k, v in DEATH_PLACE_ELEMENTS.items():
            death_place_str = death_place_str.replace(k, v)

        return death_place_str

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
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    source_edit_soup = BeautifulSoup(requests.get(performer_url + '?action=edit&veswitched=1', headers=headers).text)
    textarea_edit_soup = source_edit_soup.find(
        'textarea',
        attrs={'id': 'wpTextbox1'}
    )

    textarea_edit_text = textarea_edit_soup.get_text()
    flatlist_years_active = get_years_active_flatlist(textarea_edit_text)

    if flatlist_years_active:
        return flatlist_years_active

    years_active_unparsed = re.search(r'years_active (.*)', textarea_edit_text)

    if years_active_unparsed:
        print(years_active_unparsed)
        years_active_str = years_active_unparsed[0]

        for k, v in YEARS_ACTIVE_ELEMENTS.items():
            years_active_str = years_active_str.replace(k, v)

        # todo: idk why it's not replaced, remove this stuff later
        years_active_str = years_active_str.replace('  ', '')

        return years_active_str

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


# todo check genre parsing for the performers
# (
#   https://en.wikipedia.org/wiki/Ray_Davies,
#   https://en.wikipedia.org/wiki/Dave_Davies,
#   https://en.wikipedia.org/wiki/Mick_Avory,
#   https://en.wikipedia.org/wiki/Jim_Rodford,
#   https://en.wikipedia.org/wiki/Ian_Gibbons_(musician),
#   https://en.wikipedia.org/wiki/Roger_Daltrey,
#   https://en.wikipedia.org/wiki/Pete_Townshend,
#   https://en.wikipedia.org/wiki/John_Entwistle,
#   https://en.wikipedia.org/wiki/Doug_Sandom,
#   https://en.wikipedia.org/wiki/Keith_Moon,
#   https://en.wikipedia.org/wiki/Kenney_Jones,
#   https://en.wikipedia.org/wiki/Roger_McGuinn,
#   https://en.wikipedia.org/wiki/Gene_Clark,
#   https://en.wikipedia.org/wiki/David_Crosby,
#   https://en.wikipedia.org/wiki/Chris_Hillman,
#   https://en.wikipedia.org/wiki/Gram_Parsons,
#   https://en.wikipedia.org/wiki/Fred_Cash,
#   https://en.wikipedia.org/wiki/Sam_Gooden,
#   https://en.wikipedia.org/wiki/Curtis_Mayfield,
#   https://en.wikipedia.org/wiki/John_Fogerty,
#   https://en.wikipedia.org/wiki/Jim_Morrison,
#   https://en.wikipedia.org/wiki/Ray_Manzarek,
#   https://en.wikipedia.org/wiki/Robby_Krieger,
#   https://en.wikipedia.org/wiki/John_Densmore,
#   https://en.wikipedia.org/wiki/Eric_Burdon,
#   https://en.wikipedia.org/wiki/Alan_Price,
#   https://en.wikipedia.org/wiki/Mick_Gallagher,
#   https://en.wikipedia.org/wiki/Zoot_Money,
#   https://en.wikipedia.org/wiki/Andy_Summers,
#   https://en.wikipedia.org/wiki/Jerry_Garcia,
#   https://en.wikipedia.org/wiki/Bob_Weir,
#   https://en.wikipedia.org/wiki/Ron_%22Pigpen%22_McKernan,
#   https://en.wikipedia.org/wiki/Donna_Jean_Godchaux,
#   https://en.wikipedia.org/wiki/Robert_Plant,
#   https://en.wikipedia.org/wiki/Martha_Reeves,
#   https://en.wikipedia.org/wiki/John_Paul_Jones_(musician),
#   https://en.wikipedia.org/wiki/Sandra_Tilley,
#   https://en.wikipedia.org/wiki/Signe_Toly_Anderson,
#   https://en.wikipedia.org/wiki/Paul_Kantner,
#   https://en.wikipedia.org/wiki/Jorma_Kaukonen,
#   https://en.wikipedia.org/wiki/Skip_Spence,
#   https://en.wikipedia.org/wiki/David_Gilmour,
#   https://en.wikipedia.org/wiki/Nick_Mason,
#   https://en.wikipedia.org/wiki/Roger_Waters,
#   https://en.wikipedia.org/wiki/Syd_Barrett,
#   https://en.wikipedia.org/wiki/Lou_Reed,
#   https://en.wikipedia.org/wiki/John_Cale,
#   https://en.wikipedia.org/wiki/Sterling_Morrison,
#   https://en.wikipedia.org/wiki/Angus_MacLise,
#   https://en.wikipedia.org/wiki/Moe_Tucker,
#   https://en.wikipedia.org/wiki/Doug_Yule,
#   https://en.wikipedia.org/wiki/Barry_Gibb,
#   https://en.wikipedia.org/wiki/Robin_Gibb,
#   https://en.wikipedia.org/wiki/Maurice_Gibb,
#   https://en.wikipedia.org/wiki/Vince_Melouney,
#   https://en.wikipedia.org/wiki/Colin_Petersen,
#   https://en.wikipedia.org/wiki/Richie_Furay,
#   https://en.wikipedia.org/wiki/Stephen_Stills,
#   https://en.wikipedia.org/wiki/Neil_Young,
#   https://en.wikipedia.org/wiki/Jackie_Jackson,
#   https://en.wikipedia.org/wiki/Tito_Jackson,
#   https://en.wikipedia.org/wiki/Michael_Jackson,
#   https://en.wikipedia.org/wiki/Randy_Jackson_(Jacksons_singer),
#   https://en.wikipedia.org/wiki/Don_Henley,
#   https://en.wikipedia.org/wiki/Joe_Walsh,
#   https://en.wikipedia.org/wiki/Vince_Gill,
#   https://en.wikipedia.org/wiki/Glenn_Frey,
#   https://en.wikipedia.org/wiki/Don_Felder,
#   https://en.wikipedia.org/wiki/Bernie_Leadon,
#   https://en.wikipedia.org/wiki/John_McVie,
#   https://en.wikipedia.org/wiki/Danny_Kirwan,
#   https://en.wikipedia.org/wiki/Christine_McVie,
#   https://en.wikipedia.org/wiki/Dave_Walker,
#   https://en.wikipedia.org/wiki/Billy_Burnette,
#   https://en.wikipedia.org/wiki/Dave_Mason,
#   https://en.wikipedia.org/wiki/Neil_Finn,
#   https://en.wikipedia.org/wiki/Cass_Elliot,
#   https://en.wikipedia.org/wiki/Michelle_Phillips,
#   https://en.wikipedia.org/wiki/Carlos_Santana,
#   https://en.wikipedia.org/wiki/Cindy_Blackman_Santana,
#   https://en.wikipedia.org/wiki/Neal_Schon,
#   https://en.wikipedia.org/wiki/Gregg_Rolie,
#   https://en.wikipedia.org/wiki/Jos%C3%A9_Areas,
#   https://en.wikipedia.org/wiki/Brian_May,
#   https://en.wikipedia.org/wiki/Brian_May,
# )
# todo https://en.wikipedia.org/wiki/Ben_E._King fix genres
# todo https://en.wikipedia.org/wiki/Dub_Jones_(singer) fix birthdate parsing
# todo https://en.wikipedia.org/wiki/Barbara_Martin_(singer) fix birthdate parsing
def main():
    # hall_of_fame_links_miner()
    # performers_collection =  get_performers_collection(DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    # performers_list = get_performers_froperformers_collectionm_db(, None)
    # print(mine_performers_wiki_data(performers_list))


    band_members_collection = get_performers_collection(DB_HALL_OF_FAME_BANDS_COLLECTION)
    band_members_list =  get_performers_from_db(band_members_collection, None)

    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    # source_edit_soup = BeautifulSoup(requests.get('https://en.wikipedia.org/wiki/Dub_Jones_(singer)' + '?action=edit&veswitched=1', headers=headers).text)
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
    # birth_date = get_birth_day(source_edit_soup, performer_url='https://en.wikipedia.org/wiki/Dub_Jones_(singer)')
    # print(birth_date)

    # needs to check
    genres = get_genres("https://en.wikipedia.org/wiki/Renaldo_Benson")
    print(genres)
    # occups = get_occupations("https://en.wikipedia.org/wiki/Bob_Weir")
    # print(occups)

    # died_date = get_died_date("https://en.wikipedia.org/wiki/David_Brown_(American_musician)")
    # print(died_date)

    # died_place = get_death_place("https://en.wikipedia.org/wiki/John_Weider")
    # print(died_place)
    # years_active = get_years_activity("https://en.wikipedia.org/wiki/Moe_Tucker")
    # print(years_active)
    # nickame = get_nickname(soup, 'https://en.wikipedia.org/wiki/David_Ruffin')
    # print(nickame)
    # mine_bands_wiki_data(band_members_list)





if __name__ == '__main__':
    main()