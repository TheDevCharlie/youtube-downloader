import os
import sys
import subprocess

def build_exe():
    print("Building standalone Windows Executable (.exe)...")
    
    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=YouTubeDownloaderPro",
        "--collect-all=customtkinter",
        "--collect-all=yt_dlp",
        "--collect-all=PIL",
        "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("\n[SUCCESS] Build complete! Executable is located in the 'dist' folder: dist/YouTubeDownloaderPro.exe")

if __name__ == "__main__":
    build_exe()
