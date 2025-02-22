import  requests
from bs4 import BeautifulSoup

PAGE_URL = 'https://webscraper.io/test-sites/e-commerce/allinone'

page_data = requests.get(PAGE_URL).text

soup = BeautifulSoup(page_data, 'html.parser')

cards = soup.find_all('div', attrs={'class': 'card thumbnail'})

items = []

for card in cards:
    print(card )
    items.append(
        {
            'price': float(card.find('h4', class_='price').text.replace('$', '')),
            'title': card.find('a', class_='title').text,
            'description': card.find('p', class_='description').text,
            'reviews_count': int(card.find('p', class_='review-count').text.replace('reviews', '')),
        }
    )
