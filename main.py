import  requests
from bs4 import BeautifulSoup, ResultSet

PRODUCT_SOURCES_URLS =  {
        'laptops': 'https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops',
        'tablets': 'https://webscraper.io/test-sites/e-commerce/allinone/computers/tablets',
        'phones': 'https://webscraper.io/test-sites/e-commerce/allinone/phones/touch'
}


def get_soup(url: str) -> BeautifulSoup:
    page_data = requests.get(url).text

    soup = BeautifulSoup(page_data, 'html.parser')

    return soup

def find_cards(soup: BeautifulSoup) -> ResultSet:
    return soup.find_all('div', attrs={'class': 'card thumbnail'})

def parse_category(category_cards: list, parsed_items: list ,item_type: str):
    for category_card in category_cards:
        parsed_items.append({
            'price': float(category_card.find('h4', class_='price').text.replace('$', '')),
            'title': category_card.find('a', class_='title').get('title'),
            'description': category_card.find('p', class_='description').text,
            'reviews_count': int(category_card.find('p', class_='review-count').text.replace('reviews', '')),
            'type': item_type,
        })


def mine_items():
    items = []
    cards = []

    for category, url in PRODUCT_SOURCES_URLS.items():
        soup = get_soup(url)
        cards.append({'category': category, 'category_cards': find_cards(soup)})

    for card in cards:
        parse_category(card['category_cards'], items, card['category'])

    return items



def main():
    items = mine_items()
    print(items)

if __name__ == '__main__':
    main()