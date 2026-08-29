import os
import re
import threading
import yt_dlp

class DownloadCancelledException(Exception):
    """Raised when the user cancels the download."""
    pass

class DownloaderCore:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.is_downloading = False

    def cancel(self):
        self.cancel_event.set()

    def reset_cancel(self):
        self.cancel_event.clear()

    def fetch_info(self, url):
        """
        Extract video or playlist information quickly without downloading.
        """
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("Could not retrieve information for this URL.")
                
                is_playlist = 'entries' in info and info.get('_type') == 'playlist'
                
                if is_playlist:
                    entries = list(info.get('entries', []))
                    valid_entries = [e for e in entries if e is not None]
                    
                    # Grab thumbnail from first entry if playlist has no thumbnail
                    thumb = info.get('thumbnail')
                    if not thumb and valid_entries:
                        thumb = valid_entries[0].get('thumbnail') or (
                            valid_entries[0].get('thumbnails')[-1]['url'] 
                            if valid_entries[0].get('thumbnails') else None
                        )

                    return {
                        'type': 'playlist',
                        'title': info.get('title', 'Unknown Playlist'),
                        'uploader': info.get('uploader') or info.get('channel') or 'Various Artists / Creators',
                        'item_count': len(valid_entries),
                        'thumbnail': thumb,
                        'entries': [
                            {
                                'title': e.get('title', f'Video {i+1}'),
                                'url': e.get('url') or e.get('webpage_url') or f"https://www.youtube.com/watch?v={e.get('id')}",
                                'duration': e.get('duration'),
                                'id': e.get('id')
                            }
                            for i, e in enumerate(valid_entries)
                        ]
                    }
                else:
                    duration = info.get('duration')
                    duration_str = self.format_duration(duration) if duration else "Live / Unknown"
                    
                    thumb = info.get('thumbnail')
                    if not thumb and info.get('thumbnails'):
                        thumb = info.get('thumbnails')[-1]['url']
                        
                    return {
                        'type': 'video',
                        'title': info.get('title', 'Unknown Title'),
                        'uploader': info.get('uploader') or info.get('channel') or 'Unknown Channel',
                        'duration': duration_str,
                        'duration_seconds': duration,
                        'thumbnail': thumb,
                        'view_count': info.get('view_count', 0),
                        'upload_date': info.get('upload_date', '')
                    }
        except Exception as e:
            raise RuntimeError(f"Failed to fetch info: {str(e)}")

    @staticmethod
    def format_duration(seconds):
        if not seconds:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def format_bytes(bytes_num):
        if not bytes_num:
            return "0 MB"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} PB"

    def download(self, url, download_dir, options, progress_callback=None, status_callback=None):
        """
        Execute download with configured options and progress tracking.
        """
        self.reset_cancel()
        self.is_downloading = True

        mode = options.get('mode', 'video')  # 'video' or 'audio'
        quality = options.get('quality', 'Best Available')
        audio_format = options.get('audio_format', 'mp3').lower()
        audio_bitrate = options.get('audio_bitrate', '320').replace(' kbps', '')
        create_subfolder = options.get('create_playlist_subfolder', True)
        number_items = options.get('number_playlist_items', True)
        embed_subtitles = options.get('embed_subtitles', False)
        embed_thumbnail = options.get('embed_thumbnail', True)
        playlist_items = options.get('playlist_items', None) # e.g. "1-5,8,11-13"

        os.makedirs(download_dir, exist_ok=True)

        def check_cancellation(d=None):
            if self.cancel_event.is_set():
                raise DownloadCancelledException("Download was cancelled by user.")

        def yt_hook(d):
            check_cancellation()
            if not progress_callback:
                return

            status = d.get('status')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                percent = 0.0
                if total > 0:
                    percent = (downloaded / total) * 100.0
                elif '_percent_str' in d:
                    try:
                        clean_pct = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str']).replace('%', '').strip()
                        percent = float(clean_pct)
                    except Exception:
                        percent = 0.0

                speed_str = d.get('_speed_str', '')
                if speed_str:
                    speed_str = re.sub(r'\x1b\[[0-9;]*m', '', speed_str).strip()
                else:
                    speed = d.get('speed')
                    speed_str = f"{self.format_bytes(speed)}/s" if speed else "N/A"

                eta_str = d.get('_eta_str', '')
                if eta_str:
                    eta_str = re.sub(r'\x1b\[[0-9;]*m', '', eta_str).strip()
                else:
                    eta = d.get('eta')
                    eta_str = f"{eta}s" if eta else "N/A"

                # Playlist info
                playlist_index = d.get('playlist_index')
                playlist_count = d.get('playlist_count') or d.get('n_entries')

                progress_data = {
                    'status': 'downloading',
                    'percent': percent,
                    'downloaded_bytes': downloaded,
                    'total_bytes': total,
                    'downloaded_str': self.format_bytes(downloaded),
                    'total_str': self.format_bytes(total) if total > 0 else "Unknown",
                    'speed': speed_str,
                    'eta': eta_str,
                    'filename': os.path.basename(d.get('filename', '')),
                    'playlist_index': playlist_index,
                    'playlist_count': playlist_count
                }
                progress_callback(progress_data)

            elif status == 'finished':
                progress_callback({
                    'status': 'processing',
                    'filename': os.path.basename(d.get('filename', '')),
                    'message': 'Converting / Merging streams...'
                })

        # Base YDL options
        ydl_opts = {
            'outtmpl': {},
            'progress_hooks': [yt_hook],
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_warnings': False,
            'quiet': False,
            'windowsfilenames': True,
        }

        # Build output template
        prefix = "%(playlist_index)02d - " if number_items else ""
        if create_subfolder:
            out_tmpl_default = os.path.join(download_dir, "%(playlist_title,uploader|Single Videos)s", f"{prefix}%(title)s.%(ext)s")
        else:
            out_tmpl_default = os.path.join(download_dir, f"{prefix}%(title)s.%(ext)s")
        
        ydl_opts['outtmpl'] = {'default': out_tmpl_default}

        if playlist_items:
            ydl_opts['playlist_items'] = str(playlist_items)

        # Quality & format selection
        if mode == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': audio_bitrate,
                }
            ]
            if embed_thumbnail:
                postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                postprocessors.append({'key': 'EmbedThumbnail'})
            
            ydl_opts['postprocessors'] = postprocessors
            ydl_opts['writethumbnail'] = embed_thumbnail
        else:
            # Video mode
            quality_map = {
                'Best Available': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                '4K (2160p)': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '1440p (2K)': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                '1080p (FHD)': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720p (HD)': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]',
                '480p (SD)': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]',
                '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]',
            }
            selected_fmt = quality_map.get(quality, 'bestvideo+bestaudio/best')
            ydl_opts['format'] = selected_fmt
            ydl_opts['merge_output_format'] = 'mp4'

            postprocessors = []
            if embed_thumbnail:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                postprocessors.append({'key': 'EmbedThumbnail'})
            
            if embed_subtitles:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['en', 'all']
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

        try:
            if status_callback:
                status_callback("Starting download...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if self.cancel_event.is_set():
                raise DownloadCancelledException("Download cancelled.")

            if status_callback:
                status_callback("Download completed successfully!")
            return True

        except DownloadCancelledException:
            if status_callback:
                status_callback("Download cancelled by user.")
            return False
        except Exception as e:
            if self.cancel_event.is_set():
                if status_callback:
                    status_callback("Download cancelled.")
                return False
            if status_callback:
                status_callback(f"Download failed: {str(e)}")
            raise e
        finally:
            self.is_downloading = False
