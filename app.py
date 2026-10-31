"""
Azentio.ai Claims Leakage Prevention Agent — Application Runner.
Launches the interactive dashboard and opens it in your default browser.
"""

import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import webbrowser
import threading
import time
import uvicorn

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import settings


def open_browser(port):
    time.sleep(1.2)
    url = f"http://localhost:{port}"
    print(f"\n🌐 Opening Azentio.ai Dashboard in default browser: {url} ...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please open your browser manually at: {url}")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else settings.PORT

    # Start browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Run the unified FastAPI server
    print(f"\n🚀 Launching Azentio.ai Claims Leakage Detection Studio on port {port}...")
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
