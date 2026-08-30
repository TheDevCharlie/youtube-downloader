# Charlie-yt 🚀
> **Ultra-Fast, 144 FPS Hardware-Accelerated Universal Media & YouTube Downloader for Windows**

![Charlie-yt](app_icon.ico)

Charlie-yt is a high-performance desktop media downloader built with a **Native C++ Win32 host** and **DirectX 12 GPU-Accelerated WebView2 UI**. It starts in under **0.03 seconds (instant)**, consumes only **~35 MB of RAM**, and delivers butter-smooth **144 FPS** animations.

---

## ✨ Features

- **⚡ Instant Launch (< 0.03s)**: Native C++ binary with zero Python decompression overhead.
- **🎮 144+ FPS GPU Acceleration**: Hardware-rendered Bento grid, SVG circular progress rings, and fluid glassmorphism.
- **📌 Picture-in-Picture Mini Widget**: Minimalist floating desktop widget to track speed, ETA, and pause/resume downloads while multitasking.
- **📋 Queue Management & In-Place Reordering**: Prioritize items with `▲` and `▼` buttons; cross-session persistence keeps your queue between restarts.
- **📑 Playlist Item Exclusion & Batch Tracking**: Individual toggle/exclusion for playlist items and aggregate queue progress tracking.
- **🎬 Universal Platform Support**: YouTube, TikTok, Instagram, Twitter/X, Pinterest, Reddit, Vimeo, SoundCloud, and Facebook.
- **📁 Direct Playback & Folder Reveal**: Play finished videos directly with `▶ Play` or reveal them in Windows Explorer with `📂`.
- **🌙 Deep OLED & ☀️ WOVE Porcelain Light Themes**: High-contrast, tear-free monochrome aesthetic with rectangular 8px radius.
- **🛡️ Resize Safety Constraints**: Native `WM_GETMINMAXINFO` prevents window resizing from clipping UI elements.

---

## 📦 Installation & Download

### Option 1: Windows Setup Installer (Recommended)
Download and run the installer:
- 📁 **Installer**: [`installer_dist/Charlie-yt-Setup.exe`](installer_dist/Charlie-yt-Setup.exe) (2.2 MB)
- Creates Desktop & Start Menu shortcuts, sets native orange play badge icon, and adds Windows uninstaller support.

### Option 2: Standalone Portable Executable
Run the lightweight standalone binary directly:
- 📁 **Executable**: [`Charlie-yt.exe`](Charlie-yt.exe) (249 KB)

---

## 🛠️ Building from Source

### Prerequisites
- Windows 10 / 11
- Microsoft Visual C++ (MSVC 2019 / 2022 BuildTools)
- Inno Setup 6 (optional, for installer)

### 1. Build the Native C++ App
```bat
build_native_app.bat
```
Produces `Charlie-yt.exe` in ~2 seconds.

### 2. Build the Setup Installer
```bat
build_installer.bat
```
Produces `installer_dist\Charlie-yt-Setup.exe`.

---

## 🔗 Repository
- **GitHub**: [https://github.com/TheDevCharlie/youtube-downloader](https://github.com/TheDevCharlie/youtube-downloader)
