from pymongo import MongoClient
from pymongo.collection import Collection


class DbUtils:
    def __init__(self, db_host: str, db_port: int, db_name: str, collection_name: str):
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = MongoClient(db_host, db_port)

    def get_collection(self) -> Collection:
        db = self.client[self.db_name]
        collection = db[self.collection_name]

        return collection
