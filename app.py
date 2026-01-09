
import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime

# Fix import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config
from services.arxiv_service import ArxivService
from services.pubmed_service import PubMedService
from services.scholar_service import ScholarService
from services.deep_crawler import DeepPDFCrawler

from services.downloader_service import DownloaderService
from services.pdf_processor import PDFProcessor
from services.analyzer_service import AnalyzerService
from utils.excel_handler import ExcelHandler

st.set_page_config(page_title="SOTAi Paper Analyzer", layout="wide")

def get_services():
    """Initialize services"""
    if 'services' not in st.session_state:
        st.session_state.services = {}

    services = st.session_state.services
    
    # Lazy initialization of services to handle reloads/updates

    if 'arxiv' not in services: services['arxiv'] = ArxivService()
    if 'pubmed' not in services: services['pubmed'] = PubMedService()
    if 'scholar' not in services: services['scholar'] = ScholarService()
    if 'deep_crawler' not in services: services['deep_crawler'] = DeepPDFCrawler()
    
    # Check if downloader is stale (missing new method)
    if 'downloader' in services and not hasattr(services['downloader'], 'download_from_url'):
        print("🔄 Updating stale DownloaderService...")
        services['downloader'] = DownloaderService(Config.DOWNLOAD_DIR)
    elif 'downloader' not in services:
        services['downloader'] = DownloaderService(Config.DOWNLOAD_DIR)

    if 'pdf_processor' not in services: services['pdf_processor'] = PDFProcessor()
    if 'analyzer' not in services: services['analyzer'] = AnalyzerService()

    return services

def run_analysis(files_to_process, fields, services, model_name):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, filepath in enumerate(files_to_process):
        filename = os.path.basename(filepath)
        status_text.text(f"Analyzing {i+1}/{len(files_to_process)}: {filename}...")
        
        # Extract
        text, error = services['pdf_processor'].extract_text(filepath, max_pages=15)
        
        if text:
            # Analyze with CUSTOM FIELDS
            analysis = services['analyzer'].analyze_text(text, custom_fields=fields, model=model_name)
            
            res_entry = {"Filename": filename}
            if "error" not in analysis:
                res_entry.update(analysis)
            else:
                res_entry["Error"] = analysis.get("error")
                
            results.append(res_entry)
        else:
            # Clean error message
            error_msg = f"Extraction failed: {error}" if error else "Extraction failed (Unknown reason)"
            results.append({"Filename": filename, "Error": error_msg})
        
        progress_bar.progress((i + 1) / len(files_to_process))
    
    # Save results
    if results:
        df_res = pd.DataFrame(results)
        st.dataframe(df_res)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"results/analysis_results_{timestamp}.xlsx"
        ExcelHandler.save_results(results, output_filename)
        st.success(f"Analysis complete! Saved to {output_filename}")
        
        with open(output_filename, "rb") as f:
            st.download_button("📥 Download Excel Report", f, file_name=output_filename)

def main():
    st.title("📚 SOTAi Paper Analyzer")
    
    # Check API Keys
    if not Config.OPENAI_API_KEY:
        st.error("❌ OPENAI_API_KEY missing in .env")


    services = get_services()
    
    # Tabs for different modes
    tab1, tab2, tab3 = st.tabs(["🔍 Search & Download", "📂 Local Excel", "🤖 AI Analysis"])
    
    # --- TAB 1: Search & Download ---
    with tab1:
        st.header("Search Papers")
        
        # Source Selector
        source = st.selectbox("Select Source", [
            "ArXiv (Free - CS/Math/Physics)", 
            "PubMed (Free - Medical)",
            "Google Scholar (Free - Scraper w/ Captcha)"
        ])
        
        query_placeholder = '("Artificial Intelligence" OR "Machine Learning") AND "Medicine"'
        if "ArXiv" in source:
             query_placeholder = 'ti:LLM AND abs:medicine'
        
        query = st.text_area("Search Query", height=100, placeholder=query_placeholder)
        limit = st.number_input("Max Papers to Download", min_value=1, max_value=1000, value=5)
        
        # Interactive Mode Toggle
        col_inter, col_sound = st.columns([3, 1])
        with col_inter:
            interactive_mode = st.checkbox("🙋‍♂️ Interactive Mode (I am present to solve CAPTCHAs)", value=True, help="If checked, the system will pause and wait for you when it detects a CAPTCHA or Cloudflare block.")
        with col_sound:
            sound_alert = st.checkbox("🔔 Sound Alert", value=False, help="Play a sound when a CAPTCHA is detected.")
        
        if st.button("🚀 Start Search & Download", type="primary"):
            if not query:
                st.error("Please enter a query")
            else:
                papers = []
                with st.spinner(f"Searching {source}..."):
                    if "ArXiv" in source:
                        papers = services['arxiv'].search_papers(query, limit=limit)
                    elif "PubMed" in source:
                        papers = services['pubmed'].search_papers(query, limit=limit)
                    elif "Google Scholar" in source:
                        st.info("ℹ️ A browser window will open. Please solve any CAPTCHAs manually if they appear.")
                        papers = services['scholar'].search_papers(query, limit=limit)
                
                if not papers:
                    st.error("No papers found.")
                else:
                    st.success(f"Found {len(papers)} papers!")
                    
                    df_papers = pd.DataFrame(papers)
                    # Safe column selection
                    cols_to_show = [c for c in ['Title', 'DOI', 'Publication_Year', 'Authors', 'PDF_Link'] if c in df_papers.columns]
                    st.dataframe(df_papers[cols_to_show])
                    
                    # Download process
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    downloaded_count = 0
                    
                    for i, paper in enumerate(papers):
                        title = paper.get('Title', 'Unknown')
                        status_text.text(f"Downloading {i+1}/{len(papers)}: {title[:50]}...")
                        
                        # SPECIAL CASE: ArXiv (Use library as requested)
                        if "ArXiv" in paper.get('Source', ''):
                             status_text.text(f"Using ArXiv Library for: {title[:30]}...")
                             # Construct generic filename path first to pass to downloader
                             import re
                             safe_title = re.sub(r'[^\w\s-]', '', title).strip() + ".pdf"
                             output_path = os.path.join(Config.DOWNLOAD_DIR, safe_title)
                             
                             res = services['arxiv'].download_paper(paper.get('URL', ''), output_path)
                             if res['success']:
                                 downloaded_count += 1
                                 st.toast(f"✅ Downloaded (ArXiv Lib): {title[:30]}...", icon="✅")
                                 continue

                        # 1. Try Direct PDF Link from Scholar
                        if paper.get('PDF_Link'):
                             status_text.text(f"Trying Direct Link for: {title[:30]}...")
                             # Check if it's potentially an HTML page masquerading as PDF link
                             res = services['downloader'].download_from_url(paper['PDF_Link'], title)
                             if res['success']:
                                 downloaded_count += 1
                                 st.toast(f"✅ Downloaded: {title[:30]}...", icon="✅")
                                 continue # Skip to next paper if successful

                        # 1.5 Try Deep Page Crawl
                        if paper.get('URL') and paper['URL'].startswith('http'):
                             status_text.text(f"🕵️ Deep Crawling: {title[:30]}...")
                             found_pdf = services['deep_crawler'].find_pdf_link(paper['URL'], interactive=interactive_mode, sound_alert=sound_alert)
                             if found_pdf:
                                 status_text.text(f"   found: {found_pdf[:30]}...")
                                 res = services['downloader'].download_from_url(found_pdf, title)
                                 if res['success']:
                                     downloaded_count += 1
                                     st.toast(f"✅ Downloaded via Deep Crawl: {title[:30]}...", icon="✅")
                                     continue

                        # 2. Try Download by DOI (PyPaperRetriever)
                        doi = paper.get('DOI', 'N/A')
                        if doi != 'N/A':
                             status_text.text(f"Trying DOI Download ({doi}) for: {title[:30]}...")
                             res = services['downloader'].download_by_doi(doi, title)
                             if res['success']:
                                 downloaded_count += 1
                                 st.toast(f"✅ Downloaded via DOI: {title[:30]}...", icon="✅")
                                 continue
                             else:
                                 st.warning(f"❌ Failed via DOI: {title[:30]}...")
                        else:
                             st.warning(f"⚠️ No DOI found for: {title[:30]}...")

                        # REMOVED: Step 3 Fallback (PyPaperBot) as requested by user
                        
                        progress_bar.progress((i + 1) / len(papers))
                    
                    status_text.text("Download complete!")
                    st.success(f"Downloaded {downloaded_count}/{len(papers)} papers to '{Config.DOWNLOAD_DIR}'")

    # --- TAB 2: Local Excel ---
    with tab2:
        st.header("Load from Excel")
        uploaded_file = st.file_uploader("Upload Excel file (must have 'title' column)", type=['xlsx'])
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.info(f"Loaded {len(df)} rows")
                
                # Normalize columns
                df.columns = [c.lower() for c in df.columns]
                
                if 'title' in df.columns:
                    if st.button("⬇️ Download Papers from List"):
                        rows = df.to_dict('records')
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        downloaded_count = 0
                        
                        for i, row in enumerate(rows):
                            # Normalize keys
                            row = {k.lower(): v for k, v in row.items()}
                            title = str(row.get('title', 'Unknown'))
                            doi = str(row.get('doi', 'N/A')).strip()
                            
                            status_text.text(f"Processing {i+1}/{len(rows)}: {title[:50]}...")
                            
                            success = False
                            
                            # Try DOI first if valid
                            if doi and doi.lower() != 'nan' and doi.lower() != 'n/a':
                                res = services['downloader'].download_by_doi(doi, title)
                                if res['success']:
                                    success = True
                                    st.toast(f"✅ From Excel (DOI): {title[:30]}...", icon="✅")
                            
                            # If we had a URL column we could try that too, but let's stick to DOI for now as requested
                            if not success and doi == 'N/A':
                                st.warning(f"⚠️ No DOI for '{title[:15]}...'. Title download disabled.")

                            if success:
                                downloaded_count += 1
                                
                            progress_bar.progress((i + 1) / len(rows))
                            
                        st.success(f"Downloaded {downloaded_count}/{len(titles)} papers")
                else:
                    st.error("Excel must contain a 'title' column")
            except Exception as e:
                st.error(f"Error reading file: {e}")

    # --- TAB 3: Analysis (Decoupled) ---
    with tab3:
        st.header("Analyze Downloaded Papers")
        
        # List files in download directory
        if os.path.exists(Config.DOWNLOAD_DIR):
            files = []
            for root, _, filenames in os.walk(Config.DOWNLOAD_DIR):
                for f in filenames:
                    if f.endswith('.pdf'):
                        files.append(os.path.join(root, f))
            
            st.info(f"Found {len(files)} PDFs in '{Config.DOWNLOAD_DIR}'")
            
            # --- Field Configuration ---
            st.subheader("📝 define Extraction Fields")
            st.markdown("Add specific questions or fields you want to extract from each paper (e.g. 'Main Contribution', 'Accuracy', 'Dataset').")
            
            # Initialize session state for fields
            if 'extraction_fields' not in st.session_state:
                st.session_state.extraction_fields = ["Summary", "Methodology", "Key Findings"] # Defaults
            
            # Add new field input
            col1, col2 = st.columns([2, 1])
            with col1:
                new_field = st.text_input("New Field Name/Question")
            with col2:
                options = st.text_input("Options (optional, comma-separated)", placeholder="e.g. Yes, No OR Spontaneous, Reading")
            
            if st.button("➕ Add Field"):
                if new_field:
                    final_field_str = new_field
                    
                    if options and options.strip():
                         # process options
                         opts = [o.strip() for o in options.split(',') if o.strip()]
                         if opts:
                              final_field_str = f"{new_field} (Choose one: {', '.join(opts)})"
                    
                    if final_field_str not in st.session_state.extraction_fields:
                        st.session_state.extraction_fields.append(final_field_str)
                        st.balloons()
            
            # Show current fields
            st.markdown("### Current Fields:")
            fields_to_remove = []
            for field in st.session_state.extraction_fields:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.code(field)
                with c2:
                    if st.button("🗑️", key=f"del_{field}"):
                        fields_to_remove.append(field)
            
            # Remove marked fields (after loop to avoid iteration issues)
            if fields_to_remove:
                for f in fields_to_remove:
                    st.session_state.extraction_fields.remove(f)
                st.rerun()

            st.divider()

            # OpenAI Model Selector
            st.markdown("### 🧠 AI Configuration")
            model_name = st.text_input("OpenAI Model Name", value="gpt-5-mini", help="Enter the model ID from OpenAI (e.g., gpt-4o, gpt-4o-mini, gpt-3.5-turbo)")

            # Selection
            selection_mode = st.radio("Selection Mode", ["All", "Pick manually"])
            selected_files = files
            
            if selection_mode == "Pick manually":
                selected_files = st.multiselect("Select papers to analyze", files)
            
            if st.button("🤖 Start AI Analysis", type="primary"):
                if not selected_files:
                    st.error("No files selected")
                elif not st.session_state.extraction_fields:
                    st.error("Please add at least one extraction field.")
                else:
                    run_analysis(selected_files, st.session_state.extraction_fields, services, model_name)
            
            # --- Test Run Feature ---
            if st.button("🧪 Test Run (Analyze 1st Paper Only)", help="Run analysis on just the first paper to verify your fields/prompts without spending too much."):
                if not selected_files:
                    st.error("No files selected")
                elif not st.session_state.extraction_fields:
                    st.error("Please add at least one extraction field.")
                else:
                    target_file = [selected_files[0]]
                    st.toast(f"🧪 Testing on: {os.path.basename(target_file[0])}...", icon="🧪")
                    run_analysis(target_file, st.session_state.extraction_fields, services, model_name)
                        
        else:
            st.warning(f"Download directory '{Config.DOWNLOAD_DIR}' does not exist yet.")

if __name__ == "__main__":
    main()
