#include "charlie_engine.h"
#include <windows.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <chrono>

// Internal state for EWMA smoothing
static double g_smoothed_speed = 0.0;
static int64_t g_last_downloaded = 0;
static auto g_last_time_point = std::chrono::steady_clock::now();
static bool g_has_prior_sample = false;

static void FormatBytesNative(int64_t bytes, char* out_buf, size_t buf_size) {
    if (bytes <= 0) {
        snprintf(out_buf, buf_size, "0 MB");
        return;
    }
    const char* units[] = {"B", "KB", "MB", "GB", "TB"};
    double val = static_cast<double>(bytes);
    int unit_idx = 0;
    while (val >= 1024.0 && unit_idx < 4) {
        val /= 1024.0;
        unit_idx++;
    }
    snprintf(out_buf, buf_size, "%.2f %s", val, units[unit_idx]);
}

static void FormatDurationNative(int64_t seconds, char* out_buf, size_t buf_size) {
    if (seconds <= 0) {
        snprintf(out_buf, buf_size, "00:00");
        return;
    }
    int64_t m = seconds / 60;
    int64_t s = seconds % 60;
    int64_t h = m / 60;
    m %= 60;

    if (h > 0) {
        snprintf(out_buf, buf_size, "%02lld:%02lld:%02lld", h, m, s);
    } else {
        snprintf(out_buf, buf_size, "%02lld:%02lld", m, s);
    }
}

CHARLIE_API void Charlie_InitEngine() {
    Charlie_ResetSpeedTracker();
}

CHARLIE_API void Charlie_ResetSpeedTracker() {
    g_smoothed_speed = 0.0;
    g_last_downloaded = 0;
    g_has_prior_sample = false;
    g_last_time_point = std::chrono::steady_clock::now();
}

CHARLIE_API void Charlie_ComputeProgress(
    int64_t downloaded_bytes,
    int64_t total_bytes,
    double elapsed_time_sec,
    CharlieProgressResult* out_result
) {
    if (!out_result) return;

    auto now = std::chrono::steady_clock::now();
    double dt = std::chrono::duration<double>(now - g_last_time_point).count();

    double instant_speed = 0.0;
    if (g_has_prior_sample && dt > 0.001) {
        int64_t delta_bytes = downloaded_bytes - g_last_downloaded;
        if (delta_bytes >= 0) {
            instant_speed = static_cast<double>(delta_bytes) / dt;
            // Apply EWMA (alpha = 0.35) for smooth progression
            const double alpha = 0.35;
            g_smoothed_speed = (alpha * instant_speed) + ((1.0 - alpha) * g_smoothed_speed);
        }
    } else {
        if (elapsed_time_sec > 0.001) {
            g_smoothed_speed = static_cast<double>(downloaded_bytes) / elapsed_time_sec;
        }
        g_has_prior_sample = true;
    }

    g_last_downloaded = downloaded_bytes;
    g_last_time_point = now;

    // Percent
    double pct = 0.0;
    if (total_bytes > 0) {
        pct = (static_cast<double>(downloaded_bytes) / static_cast<double>(total_bytes)) * 100.0;
        if (pct > 100.0) pct = 100.0;
        if (pct < 0.0) pct = 0.0;
    }

    // ETA
    int64_t eta = 0;
    if (total_bytes > downloaded_bytes && g_smoothed_speed > 1024.0) {
        eta = static_cast<int64_t>((total_bytes - downloaded_bytes) / g_smoothed_speed);
    }

    out_result->percent = pct;
    out_result->speed_bytes_sec = g_smoothed_speed;
    out_result->smoothed_speed_mb = g_smoothed_speed / (1024.0 * 1024.0);
    out_result->eta_seconds = eta;

    // Formatted strings
    snprintf(out_result->speed_formatted, sizeof(out_result->speed_formatted), "%.2f MB/s", out_result->smoothed_speed_mb);
    FormatDurationNative(eta, out_result->eta_formatted, sizeof(out_result->eta_formatted));
    FormatBytesNative(downloaded_bytes, out_result->downloaded_str, sizeof(out_result->downloaded_str));
    FormatBytesNative(total_bytes, out_result->total_str, sizeof(out_result->total_str));
}

CHARLIE_API int Charlie_GenerateGridPattern(
    int width,
    int height,
    int tile_size,
    uint32_t dot_color_rgba,
    uint32_t bg_color_rgba,
    uint8_t* out_rgba_buffer
) {
    if (!out_rgba_buffer || width <= 0 || height <= 0 || tile_size <= 0) {
        return -1;
    }

    uint32_t* pixel_ptr = reinterpret_cast<uint32_t*>(out_rgba_buffer);
    int center = tile_size / 2;

    for (int y = 0; y < height; ++y) {
        int ty = y % tile_size;
        int dy = ty - center;
        int dy2 = dy * dy;

        for (int x = 0; x < width; ++x) {
            int tx = x % tile_size;
            int dx = tx - center;

            // Dot circle radius = 1.5 px (dx^2 + dy^2 <= 2)
            if (dx * dx + dy2 <= 2) {
                *pixel_ptr++ = dot_color_rgba;
            } else {
                *pixel_ptr++ = bg_color_rgba;
            }
        }
    }
    return 0;
}

CHARLIE_API int Charlie_ReorderQueue(
    int32_t* queue_indices,
    int32_t count,
    int32_t from_index,
    int32_t to_index
) {
    if (!queue_indices || count <= 1 || from_index < 0 || from_index >= count || to_index < 0 || to_index >= count) {
        return -1;
    }

    int32_t val = queue_indices[from_index];
    if (from_index < to_index) {
        for (int i = from_index; i < to_index; ++i) {
            queue_indices[i] = queue_indices[i + 1];
        }
    } else {
        for (int i = from_index; i > to_index; --i) {
            queue_indices[i] = queue_indices[i - 1];
        }
    }
    queue_indices[to_index] = val;
    return 0;
}

CHARLIE_API int64_t Charlie_FastFileWrite(
    const wchar_t* file_path,
    const uint8_t* buffer,
    int64_t byte_count,
    bool append
) {
    if (!file_path || !buffer || byte_count <= 0) return 0;

    DWORD creation_disp = append ? OPEN_ALWAYS : CREATE_ALWAYS;
    HANDLE hFile = CreateFileW(
        file_path,
        GENERIC_WRITE,
        FILE_SHARE_READ,
        NULL,
        creation_disp,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN,
        NULL
    );

    if (hFile == INVALID_HANDLE_VALUE) return -1;

    if (append) {
        SetFilePointer(hFile, 0, NULL, FILE_END);
    }

    DWORD bytesWritten = 0;
    BOOL res = WriteFile(hFile, buffer, static_cast<DWORD>(byte_count), &bytesWritten, NULL);
    CloseHandle(hFile);

    return res ? static_cast<int64_t>(bytesWritten) : -1;
}
