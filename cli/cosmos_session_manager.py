from azure.cosmos import CosmosClient, PartitionKey
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class CosmosSessionManager:
    def __init__(self, session_id, db_name="ChatDB", container_name="Sessions"):
        self.session_id = session_id
        self.cosmos_uri = os.getenv("COSMOS_URI")
        self.cosmos_key = os.getenv("COSMOS_KEY")

        self.client = CosmosClient(self.cosmos_uri, credential=self.cosmos_key)
        self.db = self.client.create_database_if_not_exists(id=db_name)
        self.container = self.db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path="/session_id")
        )

        self.messages = self._load_messages()

    def _load_messages(self):
        try:
            item = self.container.read_item(item=self.session_id, partition_key=self.session_id)
            return item["messages"]
        except Exception:
            return []

    def save(self):
        self.container.upsert_item({
            "id": self.session_id,
            "session_id": self.session_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": self.messages
        })

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        self.save()

    def clear(self):
        self.messages = []
        self.save()
