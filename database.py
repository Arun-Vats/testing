# database.py
from pymongo import MongoClient
from config import DATABASE_NAME, COLLECTION_NAME, USERS_COLLECTION_NAME

def get_db(mongo_uri):
    client = MongoClient(mongo_uri)
    db = client[DATABASE_NAME]
    return db

def get_videos_collection(mongo_uri):
    return get_db(mongo_uri)[COLLECTION_NAME]

def get_users_collection(mongo_uri):
    return get_db(mongo_uri)[USERS_COLLECTION_NAME]

def save_video(collection, video_data):
    collection.update_one({"_id": video_data["_id"]}, {"$set": video_data}, upsert=True)

def delete_videos(collection, ids):
    collection.delete_many({"_id": {"$in": ids}})

def add_user(collection, user_id):
    collection.update_one(
        {"_id": user_id},
        {"$set": {"privacy_policy_accepted": False}},
        upsert=True
    )

def check_user_privacy_accepted(collection, user_id):
    user = collection.find_one({"_id": user_id})
    return user and user.get("privacy_policy_accepted", False)

def accept_privacy_policy(collection, user_id):
    collection.update_one(
        {"_id": user_id},
        {"$set": {"privacy_policy_accepted": True}}
    )

def get_user(users_collection, user_id):
    return users_collection.find_one({"_id": user_id}) or {}

def update_user_subscription(users_collection, user_id, subscription_data):
    users_collection.update_one(
        {"_id": user_id},
        {"$set": subscription_data},
        upsert=True
    )