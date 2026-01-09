
import argparse
import sys
import os
import time
from tqdm import tqdm

# Add current dir to path to find packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.arxiv_service import ArxivService
from services.downloader_service import DownloaderService
from services.pdf_processor import PDFProcessor
from services.analyzer_service import AnalyzerService
from utils.excel_handler import ExcelHandler

def process_paper(title, downloader, pdf_processor, analyzer, prompt_key="default_analysis"):
    """
    Process a single paper: Download -> Extract -> Analyze
    """
    result = {
        "Title": title,
        "Status": "Failed",
        "PDF_Path": "",
        "Analysis": {}
    }
    
    # 1. Download
    print(f"\n[1/3] Downloading '{title[:50]}...'")
    download_res = downloader.download_paper(title)
    
    if not download_res['success']:
        print(f"❌ Download failed: {download_res['message']}")
        result["Error"] = download_res['message']
        return result
        
    pdf_path = download_res['filepath']
    result["PDF_Path"] = pdf_path
    
    # 2. Extract Text
    print(f"[2/3] Extracting text from {os.path.basename(pdf_path)}...")
    text = pdf_processor.extract_text(pdf_path, max_pages=20) # Limit pages for speed/cost
    
    if not text:
        print("❌ Text extraction failed (empty or protected PDF)")
        result["Status"] = "Extraction Failed"
        return result
        
    print(f"✅ Extracted {len(text)} characters")
    
    # 3. Analyze
    print(f"[3/3] Analyzing with AI...")
    analysis = analyzer.analyze_text(text, prompt_key=prompt_key)
    
    if "error" in analysis:
        print(f"❌ Analysis failed: {analysis['error']}")
        result["Status"] = "Analysis Failed"
        result["Error"] = analysis['error']
    else:
        print("✅ Analysis complete")
        result["Status"] = "Success"
        result["Analysis"] = analysis
        # Flatten analysis for Excel
        for k, v in analysis.items():
            result[f"AI_{k}"] = v
            
    return result

def main():
    parser = argparse.ArgumentParser(description="User-Friendly Paper Analyzer")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="Search query for ArXiv")
    group.add_argument("--excel", help="Path to input Excel file with titles")
    
    parser.add_argument("--limit", type=int, default=5, help="Max number of papers to process")
    parser.add_argument("--output", default=Config.OUTPUT_FILE, help="Output Excel file")
    parser.add_argument("--prompt", default="default_analysis", help="Prompt key from prompts.yaml")
    
    args = parser.parse_args()
    
    # Initialize services
    print("Initializing services...")
    search_service = ArxivService()
    downloader = DownloaderService(Config.DOWNLOAD_DIR)
    pdf_processor = PDFProcessor()
    analyzer = AnalyzerService()
    
    papers_to_process = []
    
    # Mode 1: Search
    if args.query:
        print(f"Searching ArXiv for: {args.query}")
        papers = search_service.search_papers(args.query, limit=args.limit)
        # Extract titles
        for p in papers:
            papers_to_process.append(p.get("Title"))
            
    # Mode 2: Excel
    elif args.excel:
        print(f"Reading from Excel: {args.excel}")
        try:
            papers_to_process = ExcelHandler.read_titles(args.excel)
            if args.limit:
                papers_to_process = papers_to_process[:args.limit]
        except Exception as e:
            print(f"Error reading Excel: {e}")
            return

    if not papers_to_process:
        print("No papers found to process.")
        return
        
    print(f"Found {len(papers_to_process)} papers. Starting processing...")
    
    results = []
    for title in tqdm(papers_to_process):
        try:
            res = process_paper(title, downloader, pdf_processor, analyzer, args.prompt)
            results.append(res)
        except Exception as e:
            print(f"Unexpected error for {title}: {e}")
            results.append({"Title": title, "Status": "Error", "Error": str(e)})
            
        # Optional: Save intermediate results
        if len(results) % 5 == 0:
            ExcelHandler.save_results(results, args.output)
            
    # Final save
    ExcelHandler.save_results(results, args.output)
    print(f"\n🎉 Done! Results saved to {args.output}")

if __name__ == "__main__":
    main()
