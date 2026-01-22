
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Defaults
    DOWNLOAD_DIR = "downloaded_papers"
    OUTPUT_FILE = "results/analysis_results.xlsx"

    @staticmethod
    def validate_keys(provider="openai"):
        """Validate API keys based on the selected provider."""
        if provider == "openai":
            if not Config.OPENAI_API_KEY:
                print("Warning: Missing OPENAI_API_KEY")
                print("Please set it in a .env file or environment variables.")
        # Ollama doesn't require an API key
