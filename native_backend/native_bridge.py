import os
import sys
import ctypes
from ctypes import (
    c_double, c_int64, c_int32, c_int, c_uint32, c_uint8,
    c_char, c_wchar_p, c_bool, POINTER, Structure
)
from PIL import Image

class CharlieProgressResult(Structure):
    _pack_ = 8
    _fields_ = [
        ("percent", c_double),
        ("speed_bytes_sec", c_double),
        ("smoothed_speed_mb", c_double),
        ("eta_seconds", c_int64),
        ("speed_formatted", c_char * 32),
        ("eta_formatted", c_char * 32),
        ("downloaded_str", c_char * 32),
        ("total_str", c_char * 32),
    ]


class CharlieNativeBridge:
    """
    High-performance Python wrapper around charlie_core_native.dll (C++).
    Provides native EWMA throughput smoothing, sub-millisecond background grid rendering,
    atomic queue priority operations, and direct disk streaming.
    """
    def __init__(self):
        self.dll = None
        self.is_native_available = False
        self._load_dll()

    def _load_dll(self):
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "charlie_core_native.dll"),
            os.path.join(os.path.dirname(__file__), "charlie_core_native.dll"),
            os.path.join(os.getcwd(), "charlie_core_native.dll"),
            os.path.join(getattr(sys, '_MEIPASS', ''), "charlie_core_native.dll")
        ]

        for p in possible_paths:
            abs_p = os.path.abspath(p)
            if os.path.exists(abs_p):
                try:
                    self.dll = ctypes.CDLL(abs_p)
                    self._bind_signatures()
                    self.is_native_available = True
                    self.dll.Charlie_InitEngine()
                    print(f"[Charlie-yt Native] Loaded C++ engine from: {abs_p}")
                    return
                except Exception as e:
                    print(f"[Charlie-yt Native] DLL load note ({abs_p}): {e}")

        print("[Charlie-yt Native] C++ engine not found, fallback to pure Python mode.")

    def _bind_signatures(self):
        # void Charlie_InitEngine()
        self.dll.Charlie_InitEngine.argtypes = []
        self.dll.Charlie_InitEngine.restype = None

        # void Charlie_ResetSpeedTracker()
        self.dll.Charlie_ResetSpeedTracker.argtypes = []
        self.dll.Charlie_ResetSpeedTracker.restype = None

        # void Charlie_ComputeProgress(int64, int64, double, CharlieProgressResult*)
        self.dll.Charlie_ComputeProgress.argtypes = [
            c_int64, c_int64, c_double, POINTER(CharlieProgressResult)
        ]
        self.dll.Charlie_ComputeProgress.restype = None

        # int Charlie_GenerateGridPattern(int, int, int, uint32, uint32, uint8*)
        self.dll.Charlie_GenerateGridPattern.argtypes = [
            c_int, c_int, c_int, c_uint32, c_uint32, POINTER(c_uint8)
        ]
        self.dll.Charlie_GenerateGridPattern.restype = c_int

        # int Charlie_ReorderQueue(int32*, int32, int32, int32)
        self.dll.Charlie_ReorderQueue.argtypes = [
            POINTER(c_int32), c_int32, c_int32, c_int32
        ]
        self.dll.Charlie_ReorderQueue.restype = c_int

        # int64 Charlie_FastFileWrite(wchar_t*, uint8*, int64, bool)
        self.dll.Charlie_FastFileWrite.argtypes = [
            c_wchar_p, POINTER(c_uint8), c_int64, c_bool
        ]
        self.dll.Charlie_FastFileWrite.restype = c_int64

    def reset_speed_tracker(self):
        if self.is_native_available:
            self.dll.Charlie_ResetSpeedTracker()

    def compute_progress(self, downloaded_bytes, total_bytes, elapsed_sec=0.0):
        if not self.is_native_available:
            # Fallback pure Python
            pct = (downloaded_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0
            spd = (downloaded_bytes / elapsed_sec) if elapsed_sec > 0 else 0.0
            eta = int((total_bytes - downloaded_bytes) / spd) if spd > 1024 and total_bytes > downloaded_bytes else 0
            return {
                'percent': min(100.0, max(0.0, pct)),
                'speed_mb': spd / (1024.0 * 1024.0),
                'speed_formatted': f"{spd / (1024.0 * 1024.0):.2f} MB/s",
                'eta_seconds': eta,
                'eta_formatted': f"{eta//60:02d}:{eta%60:02d}",
                'downloaded_str': f"{downloaded_bytes / (1024.0 * 1024.0):.2f} MB",
                'total_str': f"{total_bytes / (1024.0 * 1024.0):.2f} MB" if total_bytes > 0 else "Unknown"
            }

        res = CharlieProgressResult()
        self.dll.Charlie_ComputeProgress(
            int(downloaded_bytes),
            int(total_bytes),
            float(elapsed_sec),
            ctypes.byref(res)
        )
        return {
            'percent': res.percent,
            'speed_mb': res.smoothed_speed_mb,
            'speed_formatted': res.speed_formatted.decode('utf-8', errors='ignore'),
            'eta_seconds': res.eta_seconds,
            'eta_formatted': res.eta_formatted.decode('utf-8', errors='ignore'),
            'downloaded_str': res.downloaded_str.decode('utf-8', errors='ignore'),
            'total_str': res.total_str.decode('utf-8', errors='ignore')
        }

    def generate_grid_image(self, width, height, tile_size=28, is_dark=True):
        """
        Fast native C++ grid rasterization directly returning a PIL RGBA Image in < 1ms.
        """
        if not self.is_native_available:
            return None

        # Pack RGBA into 32-bit uint
        # Windows Little-Endian: R | (G << 8) | (B << 16) | (A << 24)
        if is_dark:
            # dot: (36, 38, 50, 255), bg: (11, 12, 14, 255)
            dot_color = 36 | (38 << 8) | (50 << 16) | (255 << 24)
            bg_color = 11 | (12 << 8) | (14 << 16) | (255 << 24)
        else:
            # dot: (205, 205, 208, 255), bg: (242, 242, 242, 255)
            dot_color = 205 | (205 << 8) | (208 << 16) | (255 << 24)
            bg_color = 242 | (242 << 8) | (242 << 16) | (255 << 24)

        buf_size = width * height * 4
        raw_buffer = (c_uint8 * buf_size)()

        ret = self.dll.Charlie_GenerateGridPattern(
            width, height, tile_size, dot_color, bg_color, raw_buffer
        )
        if ret == 0:
            return Image.frombuffer("RGBA", (width, height), raw_buffer, "raw", "RGBA", 0, 1)
        return None

    def reorder_indices(self, indices_list, from_idx, to_idx):
        if not self.is_native_available or not indices_list:
            if 0 <= from_idx < len(indices_list) and 0 <= to_idx < len(indices_list):
                val = indices_list.pop(from_idx)
                indices_list.insert(to_idx, val)
            return indices_list

        count = len(indices_list)
        arr = (c_int32 * count)(*indices_list)
        self.dll.Charlie_ReorderQueue(arr, count, from_idx, to_idx)
        return list(arr)

# Global singleton
native_engine = CharlieNativeBridge()
