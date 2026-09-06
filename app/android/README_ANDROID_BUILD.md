# AgriSense / AgriSense - Standalone "Run Anywhere" Android Mobile App Guide

This guide explains how to run the **AgriSense Android Application** on any Android smartphone, **anywhere in the world** (on 4G/5G mobile data, offline, or on any Wi-Fi network).

---

## 📱 Option 1: Standalone Offline APK (Runs Anywhere - 100% Offline with Zero Server Required!)

The Android app is configured with **Offline Asset Bundling** (`assets/index.html`).

### Why this is the ultimate "Run Anywhere" solution:
* Runs on **any Android phone** regardless of location.
* Works on **4G / 5G Mobile Data** or **Offline Airplane Mode**.
* Does **NOT** require your PC to be turned on or connected to the same Wi-Fi.

### Steps to Build Standalone APK:
1. Open **Android Studio** -> Click **File -> Open**.
2. Select the folder:
   `C:\Users\tempm\.gemini\antigravity\scratch\agrisense\app\android`
3. Click **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
4. Locate the compiled APK at:
   `app/build/outputs/apk/debug/app-debug.apk`
5. Transfer `app-debug.apk` to your phone via USB or WhatsApp and tap to install!

---

## 🌐 Option 2: 24/7 Global Cloud Deployment (Free Public HTTPS Web URL)

If you want a live public HTTPS website link that anyone can open on any phone anywhere:

1. Upload the `app/` folder to GitHub.
2. Go to **[Render.com](https://render.com)** (Free 24/7 Cloud Host) -> Click **New Web Service**.
3. Connect your GitHub repository. Select **Docker** or **Python**.
4. Click **Deploy**. Render will generate a global HTTPS link (e.g. `https://agrisense-drone.onrender.com`).
5. Open this link on any phone anywhere, tap **"Add to Home Screen"**, and install it as an Android app!
