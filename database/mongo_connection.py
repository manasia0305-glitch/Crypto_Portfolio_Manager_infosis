import os
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "crypto_intelligence_platform"
MOCK_DATA_FILE = "database/offline_storage.json"

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def json_decoder(dct):
    for k, v in dct.items():
        if isinstance(v, str):
            # Try parsing ObjectId
            if len(v) == 24 and all(c in "0123456789abcdef" for c in v):
                try: dct[k] = ObjectId(v)
                except: pass
            # Try parsing datetime
            elif "T" in v and len(v) >= 19:
                try: dct[k] = datetime.fromisoformat(v)
                except: pass
    return dct

class MemoryCollection:
    """Mock MongoDB collection for demonstration if real DB is down."""
    def __init__(self, name, parent_db=None):
        self.name = name
        self.data = []
        self.parent_db = parent_db

    async def _save(self):
        if self.parent_db:
            await self.parent_db.save_to_file()

    async def find_one(self, query=None, projection=None, sort=None):
        if query is None:
            query = {}
        
        # Filter data based on query
        filtered_data = []
        for item in self.data:
            match = True
            for k, v in query.items():
                item_val = item.get(k)
                
                # Handle ObjectId comparison (string vs object)
                if k == "_id" or isinstance(item_val, ObjectId) or isinstance(v, ObjectId):
                    if str(item_val) != str(v):
                        match = False
                        break
                elif item_val != v:
                    match = False
                    break
            if match:
                filtered_data.append(item)

        if not filtered_data:
            return None

        # Simple mock for sort: if sorting by timestamp desc, just use the last one
        if sort:
            # Simple sorting for mock
            sort_field, direction = sort[0]
            filtered_data = sorted(filtered_data, key=lambda x: x.get(sort_field, datetime.min), reverse=(direction == -1))

        if projection:
            result = filtered_data[0].copy()
            if projection.get("_id") == 0:
                result.pop("_id", None)
            return result
            
        return filtered_data[0]

    async def insert_one(self, document):
        if "_id" not in document:
            document["_id"] = ObjectId()
        self.data.append(document)
        await self._save()
        # Add a dummy result object with inserted_id
        from unittest.mock import MagicMock
        res = MagicMock()
        res.inserted_id = document["_id"]
        return res

    def find(self, query=None, projection=None, sort=None):
        # Returns a simple async iterator
        class AsyncIter:
            def __init__(self, data, parent_col, projection=None):
                self.data = data
                self.index = 0
                self.parent_col = parent_col
                self.projection = projection
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.index < len(self.data):
                    val = self.data[self.index].copy()
                    # Apply projection
                    if self.projection:
                        # Simple projection support: only handle {"_id": 0} for now
                        if self.projection.get("_id") == 0:
                            val.pop("_id", None)
                    self.index += 1
                    return val
                raise StopAsyncIteration
            def limit(self, n):
                self.data = self.data[:n]
                return self
            def sort(self, field, direction=1):
                # Simple sort implementation
                self.data = sorted(self.data, key=lambda x: x.get(field, datetime.min), reverse=(direction == -1))
                return self
            async def to_list(self, length=None):
                data_to_return = self.data[:length] if length else self.data
                if self.projection and self.projection.get("_id") == 0:
                    return [{k: v for k, v in d.items() if k != "_id"} for d in data_to_return]
                return data_to_return
        
        # Filter data based on query
        filtered_data = []
        if query is None: query = {}
        for item in self.data:
            match = True
            for k, v in query.items():
                item_val = item.get(k)
                if isinstance(v, dict):
                    # Handle basic $gte, $lte
                    try:
                        if "$gte" in v and item_val < v["$gte"]: match = False
                        if "$lte" in v and item_val > v["$lte"]: match = False
                    except: match = False # In case of type mismatch
                elif k == "_id" or isinstance(item_val, ObjectId) or isinstance(v, ObjectId):
                    if str(item_val) != str(v):
                        match = False
                        break
                elif item_val != v:
                    match = False
                    break
            if match:
                filtered_data.append(item)
        
        return AsyncIter(filtered_data, self, projection)

    async def update_one(self, query, update, upsert=False):
        item = await self.find_one(query)
        if item:
            if "$set" in update:
                item.update(update["$set"])
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k not in item: item[k] = []
                    item[k].append(v)
            if "$pull" in update:
                for k, v in update["$pull"].items():
                    if k in item and isinstance(item[k], list):
                        # Simple criteria matching
                        if isinstance(v, dict):
                            item[k] = [x for x in item[k] if not all(x.get(sk) == sv for sk, sv in v.items())]
                        else:
                            # Direct value match
                            item[k] = [x for x in item[k] if x != v]
            await self._save()
        elif upsert:
            new_item = query.copy()
            if "$set" in update: new_item.update(update["$set"])
            await self.insert_one(new_item)
        return True

    async def insert_many(self, documents):
        for doc in documents:
            if "_id" not in doc: doc["_id"] = ObjectId()
            self.data.append(doc)
        await self._save()
        return True

    async def delete_one(self, query):
        item = await self.find_one(query)
        if item:
            self.data.remove(item)
            await self._save()
            return type('obj', (object,), {'deleted_count': 1})
        return type('obj', (object,), {'deleted_count': 0})

    async def count_documents(self, query=None):
        if query is None:
            return len(self.data)
        count = 0
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

class MemoryDatabase:
    """Mock MongoDB database for demonstration."""
    def __init__(self):
        self.collections = {}
        self.is_mock = True
        self._save_task = None

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MemoryCollection(name, self)
        return self.collections[name]

    async def save_to_file(self):
        """Debounced save to file to prevent excessive disk I/O."""
        if self._save_task:
            self._save_task.cancel()
        
        async def _do_save():
            await asyncio.sleep(0.5) # Wait 500ms for more changes
            try:
                os.makedirs(os.path.dirname(MOCK_DATA_FILE), exist_ok=True)
                serializable_data = {name: col.data for name, col in self.collections.items()}
                # Use a temp file for safer writing
                temp_file = MOCK_DATA_FILE + ".tmp"
                with open(temp_file, "w") as f:
                    json.dump(serializable_data, f, cls=JSONEncoder, indent=2)
                os.replace(temp_file, MOCK_DATA_FILE)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Failed to save offline storage: {e}")
            finally:
                self._save_task = None

        self._save_task = asyncio.create_task(_do_save())

    async def load_from_file(self):
        if os.path.exists(MOCK_DATA_FILE):
            try:
                with open(MOCK_DATA_FILE, "r") as f:
                    loaded_data = json.load(f, object_hook=json_decoder)
                    for name, data in loaded_data.items():
                        col = self[name]
                        col.data = data
                print(f"✅ Loaded persistent offline data from {MOCK_DATA_FILE}")
            except Exception as e:
                print(f"⚠️  Failed to load offline storage: {e}")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None
    is_mock = False

db = MongoDB()

async def connect_to_mongo():
    try:
        # Reduced timeout for connection check
        db.client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
        # Verify connection with a ping
        await db.client.admin.command('ping')
        db.db = db.client[DATABASE_NAME]
        db.is_mock = False
        print(f"✅ Successfully connected to MongoDB at {MONGODB_URL}")
    except Exception as e:
        print(f"⚠️  MongoDB not found: {e}")
        print("💡 Switching to Dynamic JSON Offline Storage...")
        db.db = MemoryDatabase()
        db.is_mock = True
        await db.db.load_from_file()

async def close_mongo_connection():
    if db.client:
        db.client.close()
    print("Closed database connection")

def get_database():
    return db.db

