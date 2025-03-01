import pymongo

class DbUtils:
    def __init__(self, db_host: str, db_port: int, db_name: str, collection_name: str):
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = pymongo.MongoClient(db_host, db_port)
        # db = client['admin']
        #
        # a = db.scraped_items
        # a.insert_one({'test': 'test'})

