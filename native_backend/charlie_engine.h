#ifndef CHARLIE_ENGINE_H
#define CHARLIE_ENGINE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef _WIN32
  #define CHARLIE_API extern "C" __declspec(dllexport)
#else
  #define CHARLIE_API extern "C"
#endif

// Progress metrics calculated by native C++ engine
#pragma pack(push, 8)
typedef struct {
    double percent;             // Download percentage (0.0 - 100.0)
    double speed_bytes_sec;     // Instantaneous EWMA speed in bytes/sec
    double smoothed_speed_mb;   // Smoothed speed in MB/s
    int64_t eta_seconds;        // Estimated time remaining in seconds
    char speed_formatted[32];   // e.g. "14.25 MB/s"
    char eta_formatted[32];     // e.g. "01:24" or "00:35"
    char downloaded_str[32];    // e.g. "45.2 MB"
    char total_str[32];         // e.g. "120.5 MB"
} CharlieProgressResult;
#pragma pack(pop)

// C ABI Exported Functions
CHARLIE_API void Charlie_InitEngine();

CHARLIE_API void Charlie_ResetSpeedTracker();

CHARLIE_API void Charlie_ComputeProgress(
    int64_t downloaded_bytes,
    int64_t total_bytes,
    double elapsed_time_sec,
    CharlieProgressResult* out_result
);

CHARLIE_API int Charlie_GenerateGridPattern(
    int width,
    int height,
    int tile_size,
    uint32_t dot_color_rgba,
    uint32_t bg_color_rgba,
    uint8_t* out_rgba_buffer
);

CHARLIE_API int Charlie_ReorderQueue(
    int32_t* queue_indices,
    int32_t count,
    int32_t from_index,
    int32_t to_index
);

CHARLIE_API int64_t Charlie_FastFileWrite(
    const wchar_t* file_path,
    const uint8_t* buffer,
    int64_t byte_count,
    bool append
);

#endif // CHARLIE_ENGINE_H
