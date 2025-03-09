import os
import json

import dotenv
import  requests
from bs4 import BeautifulSoup

from settings import HALL_OF_FAME_FILE_PATH, WIKI_ROCK_HALL_OF_FAME

# Needs to scrap all urls of the performers or members of band (including band name)




def main():
    response = requests.get(WIKI_ROCK_HALL_OF_FAME).text

    with open(HALL_OF_FAME_FILE_PATH, 'r') as file:
        hall_of_fame_data = json.load(file)

    soup = BeautifulSoup(response, 'html.parser')
    # a = soup.find_all('a', attrs={'title': ''})
    # print(a)


if __name__ == '__main__':
    main()