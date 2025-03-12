import os
import json

import dotenv
import  requests
from bs4 import BeautifulSoup

from settings import HALL_OF_FAME_FILE_PATH, WIKI_ROCK_HALL_OF_FAME, WIKI_MAIN_URL

# Needs to scrap all urls of the performers or members of band (including band name)




def main():
    performers = []

    response = requests.get(WIKI_ROCK_HALL_OF_FAME).text

    with open(HALL_OF_FAME_FILE_PATH, 'r') as file:
        hall_of_fame_data = json.load(file)

    soup = BeautifulSoup(response, 'html.parser')

    persons = hall_of_fame_data.get('persons')
    bands = hall_of_fame_data.get('bands')
    #
    # for person in persons:
    #     url = soup.find_all('a', attrs={'title': person})[0]
    #     performers.append({'performer': person, 'url': WIKI_MAIN_URL+url['href']})

    for band in bands:
        url = WIKI_MAIN_URL+soup.find_all('a', attrs={'title': band})[0]['href']
        band_soup = BeautifulSoup(requests.get(url).text)
        table_soup =  band_soup.find('table', attrs={'class': 'infobox vcard plainlist'}).find_all('tr')
        # print(table_soup)

        for row in table_soup:
            if "Past members" in row.find('th', attrs={'class': 'infobox-label'}):
                print(row)
            # if row.name == "Past members":
            #     print(row)
        # print(table_soup)

if __name__ == '__main__':
    main()