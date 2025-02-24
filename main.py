import  requests
from bs4 import BeautifulSoup

MAIN_PAGE_URL = 'https://webscraper.io/test-sites/e-commerce/allinone'

page_data = requests.get(MAIN_PAGE_URL).text

soup = BeautifulSoup(page_data, 'html.parser')

cards = soup.find_all('div', attrs={'class': 'card thumbnail'})

items = []

for card in cards:
    items.append(
        {
            'price': float(card.find('h4', class_='price').text.replace('$', '')),
            'title': card.find('a', class_='title').get('title'),
            'description': card.find('p', class_='description').text,
            'reviews_count': int(card.find('p', class_='review-count').text.replace('reviews', '')),
        }
    )

print(items)