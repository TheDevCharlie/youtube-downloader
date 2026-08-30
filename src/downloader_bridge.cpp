#include "downloader_bridge.h"
#include <shlobj.h>
#include <shlwapi.h>
#include <thread>
#include <atomic>
#include <iostream>
#include <sstream>
#include <vector>

#pragma comment(lib, "Shlwapi.lib")
#pragma comment(lib, "Shell32.lib")
#pragma comment(lib, "Ole32.lib")

static std::atomic<bool> g_is_downloading(false);
static std::atomic<bool> g_cancel_requested(false);
static HANDLE g_hChildProcess = NULL;

static std::wstring ExecuteCommand(const std::wstring& cmd) {
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = NULL;

    HANDLE hRead, hWrite;
    if (!CreatePipe(&hRead, &hWrite, &sa, 0)) return L"";
    SetHandleInformation(hRead, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.hStdError = hWrite;
    si.hStdOutput = hWrite;
    si.dwFlags |= STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    std::vector<wchar_t> cmd_buf(cmd.begin(), cmd.end());
    cmd_buf.push_back(0);

    if (!CreateProcessW(NULL, cmd_buf.data(), NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(hWrite);
        CloseHandle(hRead);
        return L"";
    }

    CloseHandle(hWrite);

    std::string result;
    char buffer[4096];
    DWORD bytesRead;
    while (ReadFile(hRead, buffer, sizeof(buffer) - 1, &bytesRead, NULL) && bytesRead > 0) {
        buffer[bytesRead] = 0;
        result += buffer;
    }

    CloseHandle(hRead);
    WaitForSingleObject(pi.hProcess, 15000);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    int wlen = MultiByteToWideChar(CP_UTF8, 0, result.c_str(), -1, NULL, 0);
    if (wlen > 0) {
        std::wstring wstr(wlen, 0);
        MultiByteToWideChar(CP_UTF8, 0, result.c_str(), -1, &wstr[0], wlen);
        if (!wstr.empty() && wstr.back() == 0) wstr.pop_back();
        return wstr;
    }
    return L"";
}

std::wstring DownloaderBridge::InspectUrl(const std::wstring& url) {
    std::wstringstream ss;
    ss << L"python -c \"import json, sys; from downloader_core import DownloaderCore; core = DownloaderCore(); "
       << L"try:\n"
       << L"  info = core.fetch_info('''" << url << L"''')\n"
       << L"  print(json.dumps({'success': True, 'info': info}))\n"
       << L"except Exception as e:\n"
       << L"  print(json.dumps({'success': False, 'error': str(e)}))\n\"";

    return ExecuteCommand(ss.str());
}

void DownloaderBridge::StartDownloadAsync(
    const std::wstring& url,
    const std::wstring& download_dir,
    const std::wstring& quality,
    const std::wstring& playlist_items,
    ProgressCallback on_progress,
    std::function<void(bool success, const std::wstring& file_path, const std::wstring& error)> on_complete
) {
    g_cancel_requested = false;
    g_is_downloading = true;

    std::thread([=]() {
        SECURITY_ATTRIBUTES sa;
        sa.nLength = sizeof(SECURITY_ATTRIBUTES);
        sa.bInheritHandle = TRUE;
        sa.lpSecurityDescriptor = NULL;

        HANDLE hRead, hWrite;
        if (!CreatePipe(&hRead, &hWrite, &sa, 0)) {
            on_complete(false, L"", L"Pipe creation failed");
            g_is_downloading = false;
            return;
        }
        SetHandleInformation(hRead, HANDLE_FLAG_INHERIT, 0);

        STARTUPINFOW si;
        ZeroMemory(&si, sizeof(si));
        si.cb = sizeof(si);
        si.hStdError = hWrite;
        si.hStdOutput = hWrite;
        si.dwFlags |= STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;

        PROCESS_INFORMATION pi;
        ZeroMemory(&pi, sizeof(pi));

        std::wstringstream ss;
        ss << L"python -u -c \""
           << L"import sys, json, os\n"
           << L"from downloader_core import DownloaderCore\n"
           << L"core = DownloaderCore()\n"
           << L"def on_prog(d):\n"
           << L"  sys.stdout.write('PROGRESS:' + json.dumps(d) + '\\n')\n"
           << L"  sys.stdout.flush()\n"
           << L"try:\n"
           << L"  opts = {'quality': '" << quality << L"', 'mode': 'video' if 'MP3' not in '" << quality << L"' and 'WAV' not in '" << quality << L"' else 'audio', 'audio_format': 'mp3' if 'MP3' in '" << quality << L"' else 'wav', 'playlist_items': '" << playlist_items << L"' or None}\n"
           << L"  res = core.download('''" << url << L"''', r'''" << download_dir << L"''', opts, progress_callback=on_prog)\n"
           << L"  sys.stdout.write('RESULT:' + json.dumps(res) + '\\n')\n"
           << L"  sys.stdout.flush()\n"
           << L"except Exception as e:\n"
           << L"  sys.stdout.write('ERROR:' + str(e) + '\\n')\n"
           << L"  sys.stdout.flush()\n\"";

        std::wstring cmd = ss.str();
        std::vector<wchar_t> cmd_buf(cmd.begin(), cmd.end());
        cmd_buf.push_back(0);

        if (!CreateProcessW(NULL, cmd_buf.data(), NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
            CloseHandle(hWrite);
            CloseHandle(hRead);
            on_complete(false, L"", L"Failed to start download process");
            g_is_downloading = false;
            return;
        }

        g_hChildProcess = pi.hProcess;
        CloseHandle(hWrite);

        char buffer[1024];
        std::string line_accum;
        DWORD bytesRead;
        bool completed = false;
        std::wstring out_file_path;
        std::wstring out_error;

        while (ReadFile(hRead, buffer, sizeof(buffer) - 1, &bytesRead, NULL) && bytesRead > 0) {
            buffer[bytesRead] = 0;
            line_accum += buffer;

            size_t newline_pos;
            while ((newline_pos = line_accum.find('\n')) != std::string::npos) {
                std::string line = line_accum.substr(0, newline_pos);
                line_accum.erase(0, newline_pos + 1);

                if (!line.empty() && line.back() == '\r') line.pop_back();

                if (line.rfind("PROGRESS:", 0) == 0) {
                    std::string payload = line.substr(9);
                    int wlen = MultiByteToWideChar(CP_UTF8, 0, payload.c_str(), -1, NULL, 0);
                    if (wlen > 0) {
                        std::wstring wpayload(wlen, 0);
                        MultiByteToWideChar(CP_UTF8, 0, payload.c_str(), -1, &wpayload[0], wlen);
                        if (!wpayload.empty() && wpayload.back() == 0) wpayload.pop_back();
                        on_progress(wpayload);
                    }
                } else if (line.rfind("RESULT:", 0) == 0) {
                    completed = true;
                    // parse file_path
                    size_t fp_idx = line.find("\"file_path\": \"");
                    if (fp_idx != std::string::npos) {
                        size_t start = fp_idx + 14;
                        size_t end = line.find("\"", start);
                        if (end != std::string::npos) {
                            std::string fp = line.substr(start, end - start);
                            int wlen = MultiByteToWideChar(CP_UTF8, 0, fp.c_str(), -1, NULL, 0);
                            out_file_path = std::wstring(wlen, 0);
                            MultiByteToWideChar(CP_UTF8, 0, fp.c_str(), -1, &out_file_path[0], wlen);
                            if (!out_file_path.empty() && out_file_path.back() == 0) out_file_path.pop_back();
                        }
                    }
                } else if (line.rfind("ERROR:", 0) == 0) {
                    std::string err = line.substr(6);
                    int wlen = MultiByteToWideChar(CP_UTF8, 0, err.c_str(), -1, NULL, 0);
                    out_error = std::wstring(wlen, 0);
                    MultiByteToWideChar(CP_UTF8, 0, err.c_str(), -1, &out_error[0], wlen);
                    if (!out_error.empty() && out_error.back() == 0) out_error.pop_back();
                }
            }
        }

        CloseHandle(hRead);
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        g_hChildProcess = NULL;
        g_is_downloading = false;

        on_complete(completed, out_file_path, out_error);
    }).detach();
}

void DownloaderBridge::CancelDownload() {
    g_cancel_requested = true;
    if (g_hChildProcess) {
        TerminateProcess(g_hChildProcess, 0);
    }
}

void DownloaderBridge::TogglePause(bool pause) {
    // Handled via core pause event or thread suspension
}

void DownloaderBridge::OpenFileDirectly(const std::wstring& path) {
    if (!path.empty()) {
        ShellExecuteW(NULL, L"open", path.c_str(), NULL, NULL, SW_SHOWNORMAL);
    }
}

void DownloaderBridge::ShowInFolder(const std::wstring& path) {
    if (!path.empty()) {
        std::wstring param = L"/select,\"" + path + L"\"";
        ShellExecuteW(NULL, L"open", L"explorer.exe", param.c_str(), NULL, SW_SHOWNORMAL);
    }
}

std::wstring DownloaderBridge::BrowseFolderDialog(HWND hWnd) {
    IFileDialog* pfd = NULL;
    std::wstring chosen_dir;

    if (SUCCEEDED(CoCreateInstance(CLSID_FileOpenDialog, NULL, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&pfd)))) {
        DWORD dwOptions;
        if (SUCCEEDED(pfd->GetOptions(&dwOptions))) {
            pfd->SetOptions(dwOptions | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
        }
        if (SUCCEEDED(pfd->Show(hWnd))) {
            IShellItem* psi = NULL;
            if (SUCCEEDED(pfd->GetResult(&psi))) {
                PWSTR pszPath = NULL;
                if (SUCCEEDED(psi->GetDisplayName(SIGDN_FILESYSPATH, &pszPath))) {
                    chosen_dir = pszPath;
                    CoTaskMemFree(pszPath);
                }
                psi->Release();
            }
        }
        pfd->Release();
    }
    return chosen_dir;
}
