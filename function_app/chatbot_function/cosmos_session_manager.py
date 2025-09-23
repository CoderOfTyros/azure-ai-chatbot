from azure.cosmos import CosmosClient, PartitionKey
import os
from datetime import datetime


class CosmosSessionManager:
    def __init__(self, session_id, db_name="ChatDB", container_name="Sessions"):
        self.session_id = session_id
        self.cosmos_uri = os.environ.get("COSMOS_URI")
        self.cosmos_key = os.environ.get("COSMOS_KEY")

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

    # def list_all_sessions(self):
    #     try:
    #         query = "SELECT * FROM c ORDER BY c.created_at DESC"
    #         items = list(self.container.query_items(query=query, enable_cross_partition_query=True))
            
    #         sessions = []
    #         for item in items:
    #             session_data = {
    #                 "id": item["session_id"],
    #                 "created_at": item.get("created_at", ""),
    #                 "message_count": len(item.get("messages", [])),
    #                 "title": self._generate_title(item.get("messages", []))
    #             }
    #             sessions.append(session_data)
            
    #         return sessions
    #     except Exception as e:
    #         return []

    # def _generate_title(self, messages):
    #     if not messages:
    #         return "New Chat"
        
    #     for message in messages:
    #         if message.get("role") == "user":
    #             content = message.get("content", "")
    #             if content and content.lower() not in ["clear", "restart", "history", "list_sessions"]:
    #                 return content[:50] + "..." if len(content) > 50 else content
        
    #     return "New Chat"