
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    WOS_API_KEY = os.getenv("WOS_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Defaults
    DOWNLOAD_DIR = "downloaded_papers"
    OUTPUT_FILE = "analysis_results.xlsx"
    
    @staticmethod
    def validate_keys():
        missing = []
        if not Config.WOS_API_KEY:
            missing.append("WOS_API_KEY")
        if not Config.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        if missing:
            print(f"Warning: Missing API keys: {', '.join(missing)}")
            print("Please set them in a .env file or environment variables.")
