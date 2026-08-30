#ifndef DOWNLOADER_BRIDGE_H
#define DOWNLOADER_BRIDGE_H

#include <windows.h>
#include <string>
#include <functional>

typedef std::function<void(const std::wstring& json_event)> ProgressCallback;

class DownloaderBridge {
public:
    static std::wstring InspectUrl(const std::wstring& url);
    static void StartDownloadAsync(
        const std::wstring& url,
        const std::wstring& download_dir,
        const std::wstring& quality,
        const std::wstring& playlist_items,
        ProgressCallback on_progress,
        std::function<void(bool success, const std::wstring& file_path, const std::wstring& error)> on_complete
    );
    static void CancelDownload();
    static void TogglePause(bool pause);
    static void OpenFileDirectly(const std::wstring& path);
    static void ShowInFolder(const std::wstring& path);
    static std::wstring BrowseFolderDialog(HWND hWnd);
};

#endif // DOWNLOADER_BRIDGE_H
