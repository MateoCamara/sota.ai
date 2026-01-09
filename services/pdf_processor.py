
import fitz  # PyMuPDF
import os

class PDFProcessor:
    @staticmethod
    def extract_text(pdf_path: str, max_pages: int = None) -> tuple:
        """
        Extract text from a PDF file. 
        Returns: (text, error_message)
        """
        if not os.path.exists(pdf_path):
            return None, "File not found"
            
        try:
            doc = fitz.open(pdf_path)
            text = []
            
            for i, page in enumerate(doc):
                if max_pages and i >= max_pages:
                    break
                text.append(page.get_text())
                
            full_text = "\n".join(text)
            doc.close()
            
            if not full_text.strip():
                return None, "PDF contains no extractable text (scanned?)"
                
            return full_text, None
            
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return None, str(e)

    @staticmethod
    def get_token_count_estimate(text: str) -> int:
        """
        Rough estimate of token count (words/0.75).
        """
        return int(len(text.split()) / 0.75)
