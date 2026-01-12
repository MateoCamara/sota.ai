
<p align="center">
  <img src="assets/sota_logo.png" alt="SOTAi Logo" width="300">
</p>

# 📚 SOTAi Paper Analyzer

![Python](https://img.shields.io/badge/python-3.8+-blue) [![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/MateoCamara/sota.ai/pulls) [![Code Style](https://img.shields.io/badge/code%20style-PEP8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

SOTAi is an intelligent tool designed to automate the retrieval, downloading, and analysis of academic papers. It streamlines the research process by connecting to major scientific databases and leveraging Large Language Models (LLMs) to extract key insights from PDF documents.

## 🚀 What it does

This application allows researchers to:
1.  **Search** for scientific papers across multiple sources:
    *   **ArXiv** (Computer Science, Math, Physics)
    *   **PubMed** (Medical & Life Sciences)
    *   **Google Scholar** (General scraping with CAPTCHA handling)
2.  **Download** full-text PDFs automatically, utilizing direct links, deep web crawling, or libraries like `arxiv` and `pypaperretriever`.
3.  **Analyze** the content of the papers using OpenAI's GPT models (configurable). You can define custom extraction fields (e.g., "Main Contribution", "Dataset Used", "Accuracy") to get structured data from unstructured text.
4.  **Export** the results into an Excel report for easy comparison and review.

## 🎬 Demo

Watch the full walkthrough to see SOTAi in action:

[![SOTAi Demo](https://img.youtube.com/vi/aif6k0yzXZw/maxresdefault.jpg)](https://www.youtube.com/watch?v=aif6k0yzXZw)

## ⚙️ How it works

The system is built with a modular architecture:
*   **Search Services**: Specialized modules query APIs (ArXiv, PubMed) or scrape web results (Google Scholar/Selenium) to find paper metadata.
*   **Downloader**: A robust download engine that attempts multiple strategies:
    *   Direct PDF links.
    *   **Deep Crawl**: Visits the paper's landing page to find the PDF button, with capabilities to handle interactive challenges (CAPTCHAs).
    *   DOI resolution via Unpaywall or SciHub fallbacks.
*   **PDF Processor**: Extracts raw text from the downloaded PDF files.
*   **AI Analyzer**: Sends the extracted text to an OpenAI model (default: `gpt-5-mini`) with a dynamically constructed prompt based on your custom questions. It returns structured JSON data.

## 🛠️ How to use

### Prerequisites
*   Python 3.8+
*   An OpenAI API Key (set in `.env`)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/sota.ai.git
    cd sota.ai
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your environment**:
    
    The application requires the `OPENAI_API_KEY` to be set in your **System Environment Variables**. 
    
    *   **Windows (PowerShell)**:
        ```powershell
        $env:OPENAI_API_KEY="your-key-here"
        ```
    *   **Mac/Linux**:
        ```bash
        export OPENAI_API_KEY="your-key-here"
        ```
    
    *(Note: The application also supports `.env` files if you prefer for local development, but system variables are recommended).*

### Running the App

Start the user-friendly Streamlit interface:
```bash
streamlit run app.py
```

1.  **Search & Download**: Go to the first tab, select a source (e.g., ArXiv), enter your query, and click "Start Search & Download".
2.  **Analyze**:
    *   Go to the "AI Analysis" tab.
    *   Define the fields you want to extract (e.g., "Methodology", "Results").
    *   Select the papers you want to analyze.
    *   Configure the OpenAI Model Name (default: `gpt-5-mini`).
    *   Click "Start AI Analysis".
3.  **View Results**: The analysis will be displayed in a table and saved automatically to the `results/` folder as an Excel file.

## 📄 Citation

If you use this tool in your research, please cite the article where it was developed:

```bibtex
@article{camara2025neural,
  title={Neural Audio Synthesis for Sound Effects: A Scope Review},
  author={C{\'a}mara, Mateo and Marcos, Fernando and Bargum, Anders R and Erkut, Cumhur and Reiss, Joshua and Blanco, Jos{\'e} Luis},
  journal={IEEE Transactions on Audio, Speech and Language Processing},
  year={2025},
  publisher={IEEE}
}
```

## ⭐ Support

If you find this project useful, please **give it a star** on GitHub! It helps us keep improving the tool.
