import os
import zipfile

src_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\seashark_dart_app"
output_zip = r"C:\Users\tempm\Downloads\AgriSense_SeaShark_Dart_App.zip"

if os.path.exists(output_zip):
    os.remove(output_zip)

with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, src_dir)
            zipf.write(full_path, rel_path)

print(f"Successfully packaged SeaShark Dart App Zip at: {output_zip} ({os.path.getsize(output_zip)} bytes)")
