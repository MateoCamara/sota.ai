import pandas as pd
import os

class ExcelHandler:
    @staticmethod
    def save_results(data: list, filename: str):
        """
        Save a list of dictionaries to an Excel file.
        """
        import json
        from openpyxl import Workbook

        def _cell_str(v):
            # Make absolutely everything Excel-safe
            try:
                import numpy as np
                if isinstance(v, np.ndarray):
                    v = v.tolist()
                elif isinstance(v, np.generic):
                    v = v.item()
            except Exception:
                pass

            if v is None:
                return ""
            if isinstance(v, (str, int, float, bool)):
                return str(v)
            if isinstance(v, (bytes, bytearray)):
                return v.decode(errors="replace")
            if isinstance(v, (list, dict, tuple, set)):
                # Store structured stuff as JSON text
                try:
                    return json.dumps(v, ensure_ascii=False)
                except Exception:
                    return str(v)
            return str(v)

        rows = data if isinstance(data, list) else [data]

        # Collect all column names (as strings) across rows
        all_cols = []
        col_set = set()
        for r in rows:
            if isinstance(r, dict):
                for k in r.keys():
                    ks = str(k)
                    if ks not in col_set:
                        col_set.add(ks)
                        all_cols.append(ks)
            else:
                if "value" not in col_set:
                    col_set.add("value")
                    all_cols.append("value")

        wb = Workbook()
        ws = wb.active
        ws.title = "Results"

        # Header
        ws.append(all_cols)

        # Data
        for r in rows:
            if isinstance(r, dict):
                ws.append([_cell_str(r.get(c)) for c in all_cols])
            else:
                ws.append([_cell_str(r) if c == "value" else "" for c in all_cols])

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)) or ".", exist_ok=True)

        try:
            wb.save(filename)
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
        
