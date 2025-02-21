import  requests
from bs4 import BeautifulSoup

PAGE_URL = 'https://webscraper.io/test-sites/e-commerce/allinone'

page_data = requests.get(PAGE_URL).text

soup = BeautifulSoup(page_data, 'html.parser')

cards = soup.find_all('div', attrs={'class': 'card thumbnail'})

for card in cards:
    print(card)