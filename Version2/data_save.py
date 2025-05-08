import csv
import datetime
import os
import pandas as pd

class DataSave:
    def __init__(self, file_path=None):
       if file_path is None:
            file_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'data_save')
            os.makedirs(file_path, exist_ok=True)
            
    def save_csv(self, raw_data, headers=None, prefix="sweep"):
        # Clean and format the raw data
        formatted_data = self.format_data(raw_data)

        # Generate a filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"{prefix}_{timestamp}.csv")

        # Write the cleaned data to CSV
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            if headers:
                writer.writerow(headers)
            writer.writerows(formatted_data)

        print(f"[CSV] Data saved to: {filename}")
        return filename
    