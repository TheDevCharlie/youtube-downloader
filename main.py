import sys
import os

# Add local path to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_ui import YouTubeDownloaderApp

def main():
    app = YouTubeDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
