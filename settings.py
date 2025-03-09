import os
from dotenv import load_dotenv

load_dotenv()

# db settings
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_NAME = os.getenv("DB_NAME")
DB_COLLECTION = os.getenv("DB_COLLECTION")

# urls and categories
PRODUCT_SOURCES_URLS = {
    'laptops': os.getenv("LAPTOP_URL"),
    'tablets': os.getenv("TABLETS"),
    'phones': os.getenv("PHONES")
}

WIKI_ROCK_HALL_OF_FAME=os.getenv("WIKI_ROCK_HALL_OF_FAME")
HALL_OF_FAME_FILE_PATH=os.getenv("HALL_OF_FAME_FILE_PATH")