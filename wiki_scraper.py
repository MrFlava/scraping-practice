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
from replacers import (
    REPLACE_BIRTH_PLACE_ELEMENTS,
    REPLACE_OCCUPATION_ELEMENTS,
    DEATH_DATE_ELEMENTS,
    DEATH_PLACE_ELEMENTS,
    YEARS_ACTIVE_ELEMENTS,
    GENRES_ELEMENTS
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
    print(textarea_edit_text)
    occupations_unparsed = re.search(r'occupation (.*)', textarea_edit_text)
    # print(occupations_unparsed)
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

    genre_unparsed_Flist = re.search(r'genre\s*=\s*\{\{Flatlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL)
    genre_unparsed_flist = re.search(r'genre\s*=\s*\{\{flatlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL)
    genre_unparsed_hlist = re.search(r'genre\s*=\s*\{\{hlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL)
    genre_unparsed_Hlist = re.search(r'genre\s*=\s*\{\{Hlist\|\s*(.*?)\s*\}\}', textarea_edit_text, re.DOTALL)

    genre_unparsed = next((v for v in [
        genre_unparsed_Flist,
        genre_unparsed_flist,
        genre_unparsed_hlist,
        genre_unparsed_Hlist
    ] if v is not None), None)

    if genre_unparsed:
        genre_unparsed_list = genre_unparsed[0].splitlines()

        for genre_unparsed in genre_unparsed_list:
            # todo: move them somehow
            genre_str = (genre_unparsed
                         .replace('Flatlist', '')
                         .replace('flatlist', '')
                         .replace('Hlist', '')
                         .replace('hlist', '')
                         .replace('genre', '')
                         .replace('=', '')
                         .replace('*', '')
                         .replace('[', '')
                         .replace(']', '')
                         .replace('{', '')
                         .replace('}', '')
                         .replace('|', ' ')
                         .replace(' ', '')
                         .replace('<ref>CitewebtitleJerryLeeLewisurlhttps://www.rockhall.com/inductees/jerry-lee-lewisaccess-dateSeptember4,2016websiteRockandRollHallofFameandMuseumarchive-dateOctober1,2021archive-urlhttps://web.archive.org/web/20211001212832/https://www.rockhall.com/inductees/jerry-lee-lewisurl-statuslive', '')
                         .replace('<ref>citeweblastSilvafirstCarlytitleRodStewartAnnouncesHe"sSwitchingMusicGenresurlhttps://www.msn.com/en-us/entertainment/news/rod-stewart-announces-he-s-switching-music-s/ar-AA1cB3el?liBBnb2ghwebsiteParadedate15June2023access-date9July2023viaMSN', '')
                         .replace('<ref>citeweburlhttps://www.allmusic.com/artist/roy-orbison-mn0000852007titleRoyOrbisonSongs,Albums,Reviews,Bio&MorewebsiteAllMusic', '')
                         .replace('<ref>JazzNorthernSoulhttps://lithub.com/dusty-springfield-reluctant-queen-of-blue-eyed-soul/DustySpringfieldqueenofblue-eyed-soulRetrieved12April2022</ref>', '')
                         .replace("<ref>citeweblastSilvafirstCarlytitleRodStewartAnnouncesHe'sSwitchingMusicGenresurlhttps://www.msn.com/en-us/entertainment/news/rod-stewart-announces-he-s-switching-music-s/ar-AA1cB3el?liBBnb2ghwebsiteParadedate15June2023access-date9July2023viaMSN", '')
                         .replace("<ref>citeweburlhttps://www.latimes.com/archives/la-xpm-1995-02-13-ca-31549-story.htmltitleBobMarleyFestivalSpreadsSome'RastamanVibration':Anniversary:Jamaicaconcertmarksthe50thbirthdayofthelatereggaeiconandpoet-musician.authorFreed,Kennethdate13February1995newspaperLosAngelesTimesaccess-date1August2019archive-date2August2019archive-urlhttps://web.archive.org/web/20190802064134/https://www.latimes.com/archives/la-xpm-1995-02-13-ca-31549-story.htmlurl-statuslive", '')
                         .replace('<refname"auto2">Citeweburlhttps://www.allmusic.com/artist/johnny-cash-mn0000816890titleJohnnyCash&#124;Biography,Albums,StreamingLinkswebsiteAllMusic', '')
                         .replace('<refname"Snapes-2019">citeweburlhttps://www.theguardian.com/music/2019/jul/08/stevie-wonder-kidney-transplant-british-summertime-festival-hyde-park-londontitleStevieWondertoundergokidneytransplantworkTheGuardianlocationLondonlastSnapesfirstLauradateJuly8,2019access-dateJuly26,2020', '')
                         )

            if genre_str.startswith('Rockmusicrock<refname"bio-allmusic1"'):
                genre_str = re.sub(r"['\"]","" ,genre_str)
                genre_str = genre_str.replace('<refnamebio-allmusic1/><refnameconcertarchives>citeweburlhttps://www.concertarchives.org/bands/billy-joel--5workConcertArchivestitleBillyJoelsConcertHistoryaccess-dateOctober18,2020archive-dateNovember8,2020archive-urlhttps://web.archive.org/web/20201108053223/https://www.concertarchives.org/bands/billy-joel--5url-statuslive', "")

            if genre_str.startswith('<!--Donotaddslikeart/prog/jazz/experimental/symphonicrock.'):
                genre_str = genre_str.replace('<!--Donotaddslikeart/prog/jazz/experimental/symphonicrock.ThisinfoboxwouldbeenormousifeverystyleZappaeverplayedwasincluded.-->', '')

            genre_str = GENRES_ELEMENTS.get(genre_str)

            if genre_str and  "," in genre_str:
                genre_list += genre_str.split(',')
            elif genre_str:
                genre_list.append(genre_str)


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



def main():
    # hall_of_fame_links_miner()
    # performers_collection =  get_performers_collection(DB_HALL_OF_FAME_PERFORMERS_COLLECTION)
    # performers_list = get_performers_froperformers_collectionm_db(, None)
    # print(mine_performers_wiki_data(performers_list))


    band_members_collection = get_performers_collection(DB_HALL_OF_FAME_BANDS_COLLECTION)
    band_members_list =  get_performers_from_db(band_members_collection, None)
    # todo no occupations (needs to fix not only one row)
    # for cases (
    # https://en.wikipedia.org/wiki/Paul_Williams_(The_Temptations_singer)
    # https://en.wikipedia.org/wiki/Eddie_Kendricks
    # https://en.wikipedia.org/wiki/Otis_Williams
    # https://en.wikipedia.org/wiki/Mike_Love
    # https://en.wikipedia.org/wiki/Paul_McCartney
    # https://en.wikipedia.org/wiki/Ringo_Starr
    # https://en.wikipedia.org/wiki/Mick_Jagger
    # https://en.wikipedia.org/wiki/Paul_Simon
    # https://en.wikipedia.org/wiki/Art_Garfunkel
    # https://en.wikipedia.org/wiki/Jerry_Butler
    # https://en.wikipedia.org/wiki/Curtis_Mayfield
    # https://en.wikipedia.org/wiki/Jack_Bruce
    # https://en.wikipedia.org/wiki/Eric_Clapton
    # https://en.wikipedia.org/wiki/John_Fogerty
    # https://en.wikipedia.org/wiki/Jimmy_Page
    # https://en.wikipedia.org/wiki/John_Paul_Jones_(musician),
    # https://en.wikipedia.org/wiki/Richard_Wright_(musician),
    # https://en.wikipedia.org/wiki/Syd_Barrett
    # https://en.wikipedia.org/wiki/Peter_Green_(musician)
    # https://en.wikipedia.org/wiki/Mick_Fleetwood
    # https://en.wikipedia.org/wiki/Stevie_Nicks
    # https://en.wikipedia.org/wiki/Cindy_Blackman_Santana
    # https://en.wikipedia.org/wiki/Neal_Schon
    # https://en.wikipedia.org/wiki/Gregg_Rolie
    # https://en.wikipedia.org/wiki/Steven_Tyler
    # https://en.wikipedia.org/wiki/Brian_May
    # https://en.wikipedia.org/wiki/Roger_Taylor_(Queen_drummer)
    # https://en.wikipedia.org/wiki/Freddie_Mercury
    # https://en.wikipedia.org/wiki/Bob_Weir
    # https://en.wikipedia.org/wiki/Moe_Tucker
    # https://en.wikipedia.org/wiki/Randy_Meisner
    # )
    # todo find a way to parse years active flatlist
    #(
    # https://en.wikipedia.org/wiki/Moe_Tucker
    # https://en.wikipedia.org/wiki/Randy_Meisner
    # )
    # todo find a method to parse not only tables
    # for cases (
    # https://en.wikipedia.org/wiki/Vernon_Harrell
    # https://en.wikipedia.org/wiki/Harry_McGilberry
    # https://en.wikipedia.org/wiki/Ray_Davis_(musician)
    # https://en.wikipedia.org/wiki/Adolph_Jacobs,
    # https://en.wikipedia.org/wiki/Bobby_Nunn_(doo-wop_musician),
    # https://en.wikipedia.org/wiki/Sonny_Forriest,
    # https://en.wikipedia.org/wiki/Billy_Yule,
    # https://en.wikipedia.org/wiki/Ken_Koblun,
    # https://en.wikipedia.org/wiki/Jim_Fielder
    # )
    custom_user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                         " Chrome/123.0.0.0 Safari/537.36")
    headers = {
        'User-Agent': custom_user_agent
    }
    # soup = BeautifulSoup(requests.get('https://en.wikipedia.org/wiki/Clarence_White', headers=headers).text)
    # print(soup)
    #
    # birth_place = get_birthplace(soup, performer_url="https://en.wikipedia.org/wiki/John_Entwistle")
    # print(birth_place)
    # birth_date = get_birth_day(soup, performer_url='https://en.wikipedia.org/wiki/Clarence_White')
    # print(birth_date)
    # occups = get_occupations("https://en.wikipedia.org/wiki/Bekka_Bramlett")
    # print(occups)
    #
    died_date = get_died_date("https://en.wikipedia.org/wiki/David_Brown_(American_musician)")
    print(died_date)
    #
    # died_place = get_death_place("https://en.wikipedia.org/wiki/John_Weider")
    # print(died_place)

    # years_active = get_years_activity("https://en.wikipedia.org/wiki/Moe_Tucker")
    # print(years_active)

    # nickame = get_nickname(soup, 'https://en.wikipedia.org/wiki/David_Ruffin')
    # print(nickame)
    # mine_bands_wiki_data(band_members_list)





if __name__ == '__main__':
    main()