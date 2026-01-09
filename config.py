
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Defaults
    DOWNLOAD_DIR = "downloaded_papers"
    OUTPUT_FILE = "results/analysis_results.xlsx"
    
    @staticmethod
    def validate_keys():
        missing = []
        if not Config.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        if missing:
            print(f"Warning: Missing API keys: {', '.join(missing)}")
            print("Please set them in a .env file or environment variables.")
