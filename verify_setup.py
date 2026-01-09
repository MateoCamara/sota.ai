
import sys
import importlib

required_packages = {
    "fitz": "pymupdf", 
    "openai": "openai",
    "yaml": "pyyaml",
    "pandas": "pandas",
    "requests": "requests",
    "openpyxl": "openpyxl",
    "tqdm": "tqdm",
    "arxiv": "arxiv",
    "Bio": "biopython",
    "undetected_chromedriver": "undetected-chromedriver",
    "selenium": "selenium",
    "bs4": "beautifulsoup4"
}

print("Verifying environment...")
missing = []
for module, package in required_packages.items():
    try:
        importlib.import_module(module)
        print(f"✅ {package} found")
    except ImportError:
        print(f"❌ {package} ({module}) NOT found")
        missing.append(package)

if missing:
    print("\nPlease install missing packages:")
    print(f"pip install {' '.join(missing)}")
else:
    print("\nAll dependencies ready!")

print("\nChecking API Keys in .env...")
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OPENAI_API_KEY found")
    else:
        print("❌ OPENAI_API_KEY missing")
        
    if os.getenv("WOS_API_KEY"):
        print("✅ WOS_API_KEY found")
    else:
        print("⚠️ WOS_API_KEY missing (only needed for search, not for local analysis)")
except ImportError:
    print("❌ python-dotenv not found")
