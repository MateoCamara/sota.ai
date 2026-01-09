
import pandas as pd
import os

class ExcelHandler:
    @staticmethod
    def save_results(data: list, filename: str):
        """
        Save a list of dictionaries to an Excel file.
        """
        df = pd.DataFrame(data)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)) or ".", exist_ok=True)
        
        try:
            df.to_excel(filename, index=False)
            print(f"Results saved to {filename}")
        except Exception as e:
            print(f"Error saving Excel: {e}")

    @staticmethod
    def read_titles(filename: str, title_col: str = "title"):
        """
        Read titles from an Excel file.
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        df = pd.read_excel(filename)
        if title_col not in df.columns:
            # Try case insensitive match
            cols = {c.lower(): c for c in df.columns}
            if title_col.lower() in cols:
                title_col = cols[title_col.lower()]
            else:
                raise ValueError(f"Column '{title_col}' not found in {filename}")
        
        # Return unique, non-empty titles
        return df[title_col].dropna().unique().tolist()
