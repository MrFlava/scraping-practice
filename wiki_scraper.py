import  requests
from bs4 import BeautifulSoup

# Needs to scrap all urls of the performers or members of band (including band name)

WIKI_ROCK_HALL_OF_FAME = 'https://en.wikipedia.org/wiki/List_of_Rock_and_Roll_Hall_of_Fame_inductees'

def main():
    response = requests.get(WIKI_ROCK_HALL_OF_FAME).text

    soup = BeautifulSoup(response, 'html.parser')
    print(soup.prettify())


if __name__ == '__main__':
    main()