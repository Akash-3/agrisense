import os
import shutil

src_html = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\frontend\index.html"
dst_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\android\app\src\main\assets"
dst_html = os.path.join(dst_dir, "index.html")

os.makedirs(dst_dir, exist_ok=True)
shutil.copy(src_html, dst_html)
print(f"Copied standalone HTML asset to: {dst_html}")
