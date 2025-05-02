import os
from dotenv import load_dotenv

load_dotenv()

# db settings
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_ITEMS_COLLECTION = os.getenv("DB_ITEMS_COLLECTION")
DB_HALL_OF_FAME_BANDS_COLLECTION=os.getenv("DB_HALL_OF_FAME_BANDS_COLLECTION")
DB_HALL_OF_FAME_PERFORMERS_COLLECTION=os.getenv("DB_HALL_OF_FAME_PERFORMERS_COLLECTION")

# urls and categories
PRODUCT_SOURCES_URLS = {
    'laptops': os.getenv("LAPTOP_URL"),
    'tablets': os.getenv("TABLETS"),
    'phones': os.getenv("PHONES")
}

WIKI_MAIN_URL = os.getenv("WIKI_MAIN_URL")
WIKI_ROCK_HALL_OF_FAME=os.getenv("WIKI_ROCK_HALL_OF_FAME")
HALL_OF_FAME_FILE_PATH=os.getenv("HALL_OF_FAME_FILE_PATH")


BAND_NAME_VARIANTS =  {
    "The Four Tops": "Four Tops",
    "Cream": "Cream (band)",
    "The Grateful Dead": "Grateful Dead",
    "Eagles": "Eagles (band)",
    "Santana": "Santana (band)",
    "Queen": "Queen (band)",
}

NON_PARSING_ELEMENTS = ["Personnel section", "[2]", "[1]", "[3]", "Early members"]

REPLACE_BIRTH_PLACE_ELEMENTS = {
    ' ': '',
    '[': '',
    ']': '',
    '|': ',',
    ',':', ',
    'birth_place=': ''
}

REPLACE_OCCUPATION_ELEMENTS = {
    '  ': '',
    'hlist': '',
    ' ': '',
    'occupation=': '',
    'Flatlist': '',
    'flatlist': '',
    '{{': '',
    '}}': '',
    '<!--Pleasedonotaddtothislistwithoutfirstdiscussingyourproposalonthetalkpage.-->': '',
    '[[Minister(Christianity)|minister]]': 'minister',
    '|': ','
}

DEATH_DATE_ELEMENTS = {
    '  ': '',
    'death date and age': '',
    'Death date and age': '',
    'death_date': '',
    '=': '',
    '{{': '',
    '}}': '',
    '|mf=yes': ''
}