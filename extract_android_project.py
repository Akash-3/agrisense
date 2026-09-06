import os
import zipfile

zip_path = r"C:\Users\tempm\Downloads\AgriSense_Android_App.zip"
extract_dir = r"C:\Users\tempm\Downloads\AgriSense_Android_App"

os.makedirs(extract_dir, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

print(f"Extracted Android Studio project to: {extract_dir}")
