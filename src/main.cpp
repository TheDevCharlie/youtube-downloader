#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <wrl/client.h>
#include <wrl/event.h>
#include <string>
#include <iostream>
#include <thread>

#include "../webview2_sdk/build/native/include/WebView2.h"
#include "downloader_bridge.h"

using namespace Microsoft::WRL;

// Global Windows state
static HWND g_hWnd = NULL;
static ComPtr<ICoreWebView2Controller> g_webviewController;
static ComPtr<ICoreWebView2> g_webview;

// Forward Declarations
LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM);
void InitWebView(HWND hWnd);
void HandleWebMessage(const std::wstring& message);

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    // Set Windows AppUserModelID for synchronized taskbar icon
    SetCurrentProcessExplicitAppUserModelID(L"charlie.yt.downloader.v1");

    // Load App Icon (orange play button on circular black badge)
    HICON hIcon = (HICON)LoadImageW(hInstance, L"app_icon.ico", IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
    if (!hIcon) {
        hIcon = LoadIcon(NULL, IDI_APPLICATION);
    }

    // Register Window Class
    const wchar_t CLASS_NAME[] = L"CharlieYtNativeWindowClass";
    WNDCLASSEXW wc = {0};
    wc.cbSize = sizeof(WNDCLASSEXW);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = CLASS_NAME;
    wc.hIcon = hIcon;
    wc.hIconSm = hIcon;

    RegisterClassExW(&wc);

    // Create Main Window (1040 x 960)
    int screen_w = GetSystemMetrics(SM_CXSCREEN);
    int screen_h = GetSystemMetrics(SM_CYSCREEN);
    int win_w = 1040;
    int win_h = 960;
    int pos_x = (screen_w - win_w) / 2;
    int pos_y = (screen_h - win_h) / 2;

    g_hWnd = CreateWindowExW(
        0,
        CLASS_NAME,
        L"Charlie-yt",
        WS_OVERLAPPEDWINDOW,
        pos_x, pos_y, win_w, win_h,
        NULL,
        NULL,
        hInstance,
        NULL
    );

    if (!g_hWnd) {
        return 0;
    }

    ShowWindow(g_hWnd, nCmdShow);
    UpdateWindow(g_hWnd);

    // Initialize GPU-Accelerated WebView2
    InitWebView(g_hWnd);

    // Standard Win32 Message Loop
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    CoUninitialize();
    return (int)msg.wParam;
}

void InitWebView(HWND hWnd) {
    // Locate local AppData for WebView2 User Data
    wchar_t localAppData[MAX_PATH];
    SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, localAppData);
    std::wstring userDataFolder = std::wstring(localAppData) + L"\\CharlieYtWebView2";

    CreateCoreWebView2EnvironmentWithOptions(
        nullptr,
        userDataFolder.c_str(),
        nullptr,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
            [hWnd](HRESULT result, ICoreWebView2Environment* env) -> HRESULT {
                if (FAILED(result) || !env) return result;

                env->CreateCoreWebView2Controller(
                    hWnd,
                    Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                        [hWnd](HRESULT result, ICoreWebView2Controller* controller) -> HRESULT {
                            if (FAILED(result) || !controller) return result;

                            g_webviewController = controller;
                            g_webviewController->get_CoreWebView2(&g_webview);

                            // Resize WebView to match Client Window Bounds
                            RECT bounds;
                            GetClientRect(hWnd, &bounds);
                            g_webviewController->put_Bounds(bounds);

                            // Configure Settings (DirectX GPU acceleration enabled)
                            ComPtr<ICoreWebView2Settings> settings;
                            g_webview->get_Settings(&settings);
                            if (settings) {
                                settings->put_IsScriptEnabled(TRUE);
                                settings->put_AreDefaultScriptDialogsEnabled(TRUE);
                                settings->put_IsWebMessageEnabled(TRUE);
                                settings->put_AreDevToolsEnabled(FALSE);
                                settings->put_IsStatusBarEnabled(FALSE);
                            }

                            // Register Native Message Handler from JS
                            g_webview->add_WebMessageReceived(
                                Callback<ICoreWebView2WebMessageReceivedEventHandler>(
                                    [](ICoreWebView2* sender, ICoreWebView2WebMessageReceivedEventArgs* args) -> HRESULT {
                                        LPWSTR messageRaw = nullptr;
                                        if (SUCCEEDED(args->get_WebMessageAsJson(&messageRaw)) && messageRaw) {
                                            HandleWebMessage(messageRaw);
                                            CoTaskMemFree(messageRaw);
                                        }
                                        return S_OK;
                                    }
                                ).Get(),
                                nullptr
                            );

                            // Load frontend/index.html
                            wchar_t currentDir[MAX_PATH];
                            GetCurrentDirectoryW(MAX_PATH, currentDir);
                            std::wstring htmlPath = L"file:///" + std::wstring(currentDir) + L"/frontend/index.html";
                            g_webview->Navigate(htmlPath.c_str());

                            return S_OK;
                        }
                    ).Get()
                );
                return S_OK;
            }
        ).Get()
    );
}

void HandleWebMessage(const std::wstring& message) {
    if (!g_webview) return;

    if (message.find(L"\"type\":\"READY\"") != std::wstring::npos || message.find(L"\"type\": \"READY\"") != std::wstring::npos) {
        wchar_t downloadsPath[MAX_PATH];
        SHGetFolderPathW(NULL, CSIDL_MYDOCUMENTS, NULL, 0, downloadsPath);
        std::wstring msg = L"{\"type\": \"CONFIG_LOADED\", \"download_dir\": \"" + std::wstring(downloadsPath) + L"\"}";
        g_webview->PostWebMessageAsJson(msg.c_str());
    }
    else if (message.find(L"\"type\":\"INSPECT_URL\"") != std::wstring::npos || message.find(L"\"type\": \"INSPECT_URL\"") != std::wstring::npos) {
        size_t u_pos = message.find(L"\"url\":");
        if (u_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", u_pos + 6);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                if (end != std::wstring::npos) {
                    std::wstring url = message.substr(start, end - start);
                    std::thread([url]() {
                        std::wstring res_json = DownloaderBridge::InspectUrl(url);
                        if (g_webview && !res_json.empty()) {
                            std::wstring msg = L"{\"type\": \"INSPECT_RESULT\", " + res_json.substr(1);
                            g_webview->PostWebMessageAsJson(msg.c_str());
                        }
                    }).detach();
                }
            }
        }
    }
    else if (message.find(L"\"type\":\"START_DOWNLOAD\"") != std::wstring::npos || message.find(L"\"type\": \"START_DOWNLOAD\"") != std::wstring::npos) {
        std::wstring url, dir, quality;
        size_t u_pos = message.find(L"\"url\":");
        if (u_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", u_pos + 6);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                url = message.substr(start, end - start);
            }
        }

        size_t d_pos = message.find(L"\"download_dir\":");
        if (d_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", d_pos + 15);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                dir = message.substr(start, end - start);
            }
        }

        size_t q_pos = message.find(L"\"quality\":");
        if (q_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", q_pos + 10);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                quality = message.substr(start, end - start);
            }
        }

        DownloaderBridge::StartDownloadAsync(
            url, dir, quality, L"",
            [](const std::wstring& prog_json) {
                if (g_webview) {
                    std::wstring msg = L"{\"type\": \"PROGRESS\", " + prog_json.substr(1);
                    g_webview->PostWebMessageAsJson(msg.c_str());
                }
            },
            [](bool success, const std::wstring& file_path, const std::wstring& error) {
                if (g_webview) {
                    if (success) {
                        std::wstring msg = L"{\"type\": \"DOWNLOAD_COMPLETE\", \"file_path\": \"" + file_path + L"\"}";
                        g_webview->PostWebMessageAsJson(msg.c_str());
                    } else {
                        std::wstring msg = L"{\"type\": \"DOWNLOAD_ERROR\", \"error\": \"" + error + L"\"}";
                        g_webview->PostWebMessageAsJson(msg.c_str());
                    }
                }
            }
        );
    }
    else if (message.find(L"\"type\":\"CANCEL_DOWNLOAD\"") != std::wstring::npos || message.find(L"\"type\": \"CANCEL_DOWNLOAD\"") != std::wstring::npos) {
        DownloaderBridge::CancelDownload();
    }
    else if (message.find(L"\"type\":\"BROWSE_FOLDER\"") != std::wstring::npos || message.find(L"\"type\": \"BROWSE_FOLDER\"") != std::wstring::npos) {
        std::wstring chosen = DownloaderBridge::BrowseFolderDialog(g_hWnd);
        if (!chosen.empty() && g_webview) {
            std::wstring msg = L"{\"type\": \"CONFIG_LOADED\", \"download_dir\": \"" + chosen + L"\"}";
            g_webview->PostWebMessageAsJson(msg.c_str());
        }
    }
    else if (message.find(L"\"type\":\"OPEN_FOLDER\"") != std::wstring::npos || message.find(L"\"type\": \"OPEN_FOLDER\"") != std::wstring::npos) {
        size_t p_pos = message.find(L"\"path\":");
        if (p_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", p_pos + 7);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                std::wstring path = message.substr(start, end - start);
                DownloaderBridge::OpenFileDirectly(path);
            }
        }
    }
    else if (message.find(L"\"type\":\"OPEN_FILE\"") != std::wstring::npos || message.find(L"\"type\": \"OPEN_FILE\"") != std::wstring::npos) {
        size_t p_pos = message.find(L"\"path\":");
        if (p_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", p_pos + 7);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                std::wstring path = message.substr(start, end - start);
                DownloaderBridge::OpenFileDirectly(path);
            }
        }
    }
    else if (message.find(L"\"type\":\"SHOW_IN_FOLDER\"") != std::wstring::npos || message.find(L"\"type\": \"SHOW_IN_FOLDER\"") != std::wstring::npos) {
        size_t p_pos = message.find(L"\"path\":");
        if (p_pos != std::wstring::npos) {
            size_t start = message.find(L"\"", p_pos + 7);
            if (start != std::wstring::npos) {
                start += 1;
                size_t end = message.find(L"\"", start);
                std::wstring path = message.substr(start, end - start);
                DownloaderBridge::ShowInFolder(path);
            }
        }
    }
    else if (message.find(L"\"type\":\"SET_WINDOW_SIZE\"") != std::wstring::npos || message.find(L"\"type\": \"SET_WINDOW_SIZE\"") != std::wstring::npos) {
        if (message.find(L"\"topmost\":true") != std::wstring::npos || message.find(L"\"topmost\": true") != std::wstring::npos) {
            int screen_w = GetSystemMetrics(SM_CXSCREEN);
            SetWindowPos(g_hWnd, HWND_TOPMOST, screen_w - 360, 40, 340, 160, SWP_SHOWWINDOW);
        } else {
            int screen_w = GetSystemMetrics(SM_CXSCREEN);
            int screen_h = GetSystemMetrics(SM_CYSCREEN);
            SetWindowPos(g_hWnd, HWND_NOTOPMOST, (screen_w - 1040)/2, (screen_h - 960)/2, 1040, 960, SWP_SHOWWINDOW);
        }
    }
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
        case WM_SIZE:
            if (g_webviewController) {
                RECT bounds;
                GetClientRect(hWnd, &bounds);
                g_webviewController->put_Bounds(bounds);
            }
            break;
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}
