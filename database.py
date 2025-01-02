# database.py
from pymongo import MongoClient

class Database:
    def __init__(self, mongo_uri):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['great']
        self.collection = self.db['search']

    def count_documents(self, query):
        return self.collection.count_documents(query)

    def find_documents(self, query, projection, skip, limit):
        return list(self.collection.find(query, projection).skip(skip).limit(limit))

    def close(self):
        self.client.close()