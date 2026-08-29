import os
import json
from pathlib import Path

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads")

DEFAULT_CONFIG = {
    "download_dir": DEFAULT_DOWNLOAD_DIR,
    "theme": "Dark",
    "color_theme": "blue",
    "video_quality": "Best Available",
    "video_format": "mp4",
    "audio_format": "mp3",
    "audio_bitrate": "320 kbps",
    "create_playlist_subfolder": True,
    "embed_thumbnail": True,
    "embed_subtitles": False,
    "number_playlist_items": True
}

CONFIG_FILE = Path.home() / ".yt_downloader_config.json"


class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Verify download directory exists, else fallback to default
        if not os.path.exists(self.config.get("download_dir", "")):
            self.config["download_dir"] = DEFAULT_DOWNLOAD_DIR

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()
