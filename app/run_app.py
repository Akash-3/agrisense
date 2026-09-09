import os
import sys
import socket
import webbrowser
import uvicorn

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_dir)

from main import app

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=================================================================")
    print("AGRISENSE / AGRIVISION FASTAPI BACKEND & MOBILE APP SERVER")
    print("=================================================================")
    print(f"Local PC URL        : http://localhost:8000")
    print(f"Tailnet MagicDNS    : http://agrisense.tail0d103f.ts.net:8000")
    print(f"Tailscale IPv4      : http://100.126.23.88:8000")
    print(f"Local Wi-Fi IP      : http://{local_ip}:8000")
    print("=================================================================")
    print(f"Tip for Android Phone: Open Chrome -> Navigate to http://{local_ip}:8000")
    print("Tap menu -> 'Add to Home Screen' to install native App icon!")
    print("=================================================================")

    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
