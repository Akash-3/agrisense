import os
import shutil
import glob
import time
import docx
from docx import Document

def update_drone_image(docs_dir, brain_dir):
    # Copy newly generated custom drone image
    new_drone_img = os.path.join(brain_dir, "agrisense_custom_drone_1786084782681.jpg")
    drone_dst = os.path.join(docs_dir, "agrisense_drone_payload.jpg")
    
    if os.path.exists(new_drone_img):
        shutil.copy(new_drone_img, drone_dst)
        print(f"Updated agrisense_drone_payload.jpg from: {new_drone_img}")
    else:
        matches = glob.glob(os.path.join(brain_dir, "agrisense_custom_drone*.jpg"))
        if matches:
            shutil.copy(matches[0], drone_dst)
            print(f"Updated agrisense_drone_payload.jpg from: {matches[0]}")

if __name__ == "__main__":
    docs_dir = r"C:\Users\tempm\.gemini\antigravity\scratch\agrisense\docs"
    brain_dir = r"C:\Users\tempm\.gemini\antigravity\brain\674aae1c-2705-4eac-b2ee-f2be6b55fad5"
    
    update_drone_image(docs_dir, brain_dir)
