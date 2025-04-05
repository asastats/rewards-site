from utils.csv_from_excel import convert_and_clean_excel
import tempfile
import os
import urllib.request
import urllib.error

class ContributionSyncService:
    def __init__(self):
        pass

    def fetch_and_convert(self, sheet_url):
        xlsx_data = self.fetch_xlsx(sheet_url)
        if not xlsx_data:
            return None
        return self.convert_to_csv(xlsx_data)

    def fetch_xlsx(self, sheet_url):
        try:
            export_url = sheet_url.replace("/edit", "/export?format=xlsx")
            with urllib.request.urlopen(export_url) as response:
                if response.getcode() != 200:
                    return None
                return response.read()
        except urllib.error.URLError:
            return None

    def convert_to_csv(self, xlsx_data):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_xlsx_file:
            temp_xlsx_file.write(xlsx_data)
            temp_xlsx_path = temp_xlsx_file.name

        output_csv = "temp_contributions.csv"
        legacy_csv = "temp_legacy_contributions.csv"

        try:
            convert_and_clean_excel(temp_xlsx_path, output_csv, legacy_csv)
        except Exception:
            if os.path.exists(temp_xlsx_path):
                os.remove(temp_xlsx_path)
            return None

        if os.path.exists(temp_xlsx_path):
            os.remove(temp_xlsx_path)

        return output_csv