# Charlie-yt
> High-Performance Universal Media Downloader for Windows

Charlie-yt is a lightweight desktop media downloader engineered with a native Win32/C++ application host and a hardware-accelerated WebView2 interface. It provides sub-50ms startup latency, minimal memory consumption (~35 MB RAM), and fluid 144 FPS rendering via DirectX 12 hardware compositing.

---

## Architectural Highlights

- **Instant Execution**: Native Win32 binary entry point bypasses runtime decompression delays, achieving startup in under 30ms.
- **Hardware-Accelerated Compositing**: Direct2D and DirectX 12 GPU acceleration deliver consistent 144 FPS rendering for bento layouts, SVG circular meters, and transition animations.
- **Picture-in-Picture Mini Widget**: Frameless, always-on-top desktop overlay for real-time throughput monitoring and download control during multitasking.
- **Dynamic Queue Management**: In-place item reordering with dedicated priority controls and persistent state serialization across user sessions.
- **Itemized Playlist Filtering**: Granular item exclusion and batch tracking with aggregate size and time estimation.
- **Cross-Platform Extraction**: Support for YouTube, TikTok, Instagram, Twitter/X, Pinterest, Reddit, Vimeo, SoundCloud, and Facebook.
- **Native Shell Integration**: Direct media playback invocation and Windows Explorer location highlighting.
- **Window Safety Constraints**: Native `WM_GETMINMAXINFO` boundary tracking prevents layout clipping across arbitrary window dimensions.
- **Adaptive Visual Theming**: High-contrast monochrome palettes optimized for both OLED dark and porcelain light environments.

---

## Performance Comparison

| Metric | Legacy Architecture (Tkinter) | Charlie-yt Native Architecture |
| :--- | :--- | :--- |
| **Startup Latency** | 3.5 – 5.0 seconds | **< 0.03 seconds** |
| **Rendering Engine** | Single-threaded CPU Canvas | **DirectX 12 GPU Composited** |
| **Executable Size** | ~49 MB | **249 KB** |
| **Memory Footprint** | ~140 MB | **~35 MB** |
| **Frame Pacing** | Variable (20–30 FPS) | **Locked 144+ FPS** |

---

## Installation and Deployment

### 1. Windows Setup Installer
The automated setup wizard configures user-level installation, registers Start Menu and Desktop shortcuts, and provides standard Windows uninstaller integration:
- **Binary**: `installer_dist/Charlie-yt-Setup.exe` (2.2 MB)

### 2. Standalone Portable Executable
The single standalone binary can be executed directly without installation:
- **Binary**: `Charlie-yt.exe` (249 KB)

---

## Building from Source

### Prerequisites
- Microsoft Windows 10 or 11 (x64)
- Microsoft Visual C++ Build Tools (MSVC 2019 or later)
- Inno Setup 6 (optional, required for generating installer package)

### Compilation Steps

#### Build the Native Application
To compile the core executable using MSVC:
```cmd
build_native_app.bat
```
The output binary `Charlie-yt.exe` will be generated in the root directory.

#### Build the Setup Package
To compile the installer executable:
```cmd
build_installer.bat
```
The output package `Charlie-yt-Setup.exe` will be placed in the `installer_dist/` directory.

---

## Repository
- **Source Code**: https://github.com/TheDevCharlie/youtube-downloader
