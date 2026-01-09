
import os
import sys

# Add parent directory to path to import sibling packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from wos_client import create_wos_client
from user_friendly.config import Config

class WosService:
    def __init__(self):
        Config.validate_keys()
        if Config.WOS_API_KEY:
            self.client = create_wos_client(Config.WOS_API_KEY)
        else:
            self.client = None

    def search_papers(self, query: str, limit: int = 10) -> list:
        """
        Search for papers in WoS.
        Returns list of dicts with title, doi, etc.
        """
        if not self.client:
            print("WOS Client not initialized (missing API Key)")
            return []
            
        print(f"Searching WoS for: {query}")
        try:
            results = self.client.search_documents(query=query, limit=limit)
            if 'documents' in results:
                # Extract clean data immediately
                return self.client.extract_document_data(results['documents'])
            return []
        except Exception as e:
            print(f"WOS Search Error: {e}")
            return []
