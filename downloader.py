import sys
import json
import argparse
import os
import urllib.request
import yt_dlp

class MyLogger:
    def debug(self, msg):
        # Redirect yt-dlp logs to stderr so stdout has only our JSON output
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()
    def info(self, msg):
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()
    def warning(self, msg):
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()
    def error(self, msg):
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()

def format_duration(d):
    if not d:
        return "0:00"
    seconds = int(d)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def get_format_size(f, duration=None):
    if not f:
        return None
    if f.get('filesize'):
        return f['filesize']
    if f.get('filesize_approx'):
        return f['filesize_approx']
    if duration and f.get('tbr'):
        return int(duration * f['tbr'] * 1000 / 8)
    return None

def get_media_formats(media_info, platform):
    duration = media_info.get('duration')
    info_formats = media_info.get('formats', [])
    
    # Find best audio-only size to add to video size for video-only formats
    audio_formats = [f for f in info_formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    best_audio = None
    if audio_formats:
        audio_formats.sort(key=lambda x: x.get('abr') or x.get('tbr') or 0, reverse=True)
        best_audio = audio_formats[0]
    best_audio_size = get_format_size(best_audio, duration) if best_audio else 0

    def estimate_video_size(target_height):
        # Find video format closest or equal to target_height
        v_formats = [f for f in info_formats if f.get('height') == target_height and f.get('vcodec') != 'none']
        if not v_formats:
            v_formats = [f for f in info_formats if f.get('vcodec') != 'none']
            if not v_formats:
                return None
            v_formats.sort(key=lambda x: abs((x.get('height') or 0) - target_height))
        # Prefer progressive (vcodec != 'none' and acodec != 'none')
        v_formats.sort(key=lambda x: (x.get('acodec') != 'none', x.get('tbr') or 0), reverse=True)
        best_f = v_formats[0]
        vid_size = get_format_size(best_f, duration)
        if vid_size:
            if best_f.get('acodec') != 'none':
                return vid_size
            else:
                return vid_size + (best_audio_size or 0)
        return None

    def estimate_hq_video_size():
        # Find best progressive or video+audio format size
        v_formats = [f for f in info_formats if f.get('vcodec') != 'none']
        if not v_formats:
            return None
        v_formats.sort(key=lambda x: (x.get('acodec') != 'none', x.get('height') or 0, x.get('tbr') or 0), reverse=True)
        best_f = v_formats[0]
        vid_size = get_format_size(best_f, duration)
        if vid_size:
            if best_f.get('acodec') != 'none':
                return vid_size
            else:
                return vid_size + (best_audio_size or 0)
        return None

    def estimate_audio_size(bitrate_kbps):
        if duration:
            return int(duration * bitrate_kbps * 1000 / 8)
        return best_audio_size if best_audio_size else None

    formats = []
    
    # 1. Video formats
    if platform == 'youtube':
        formats.extend([
            {"id": "1080p", "name": "1080p Full HD", "type": "video", "ext": "mp4", "quality": "1080p", "note": "Best quality", "filesize": estimate_video_size(1080)},
            {"id": "720p", "name": "720p HD", "type": "video", "ext": "mp4", "quality": "720p", "note": "Fast download", "filesize": estimate_video_size(720)},
            {"id": "480p", "name": "480p SD", "type": "video", "ext": "mp4", "quality": "480p", "note": "Standard quality", "filesize": estimate_video_size(480)},
            {"id": "360p", "name": "360p", "type": "video", "ext": "mp4", "quality": "360p", "note": "Low data", "filesize": estimate_video_size(360)}
        ])
    else:
        formats.append({
            "id": "hq-video",
            "name": "High Quality Video",
            "type": "video",
            "ext": "mp4",
            "quality": "HD/Source",
            "note": "Original source quality",
            "filesize": estimate_hq_video_size()
        })
        
    # 2. Audio formats (MP3 conversion)
    formats.extend([
        {"id": "mp3-320", "name": "320kbps HQ Audio", "type": "audio", "ext": "mp3", "quality": "320kbps", "note": "Studio quality MP3", "filesize": estimate_audio_size(320)},
        {"id": "mp3-128", "name": "128kbps Audio", "type": "audio", "ext": "mp3", "quality": "128kbps", "note": "Standard quality MP3", "filesize": estimate_audio_size(128)}
    ])
    
    # 3. Thumbnail/Photo format
    formats.append({
        "id": "thumbnail",
        "name": "Max Thumbnail / Cover",
        "type": "image",
        "ext": "jpg",
        "quality": "Original",
        "note": "Cover image",
        "filesize": 153600
    })
    
    return formats

def extract(url):
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'logger': MyLogger(),
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            return {"success": False, "error": str(e)}
            
        if not info:
            return {"success": False, "error": "Could not extract metadata"}
            
        extractor = info.get('extractor_key', '').lower()
        if not extractor:
            # Fallback based on URL
            if 'youtube.com' in url or 'youtu.be' in url:
                extractor = 'youtube'
            elif 'instagram.com' in url:
                extractor = 'instagram'
            elif 'tiktok.com' in url:
                extractor = 'tiktok'
            elif 'facebook.com' in url:
                extractor = 'facebook'
            elif 'twitter.com' in url or 'x.com' in url:
                extractor = 'twitter'
            elif 'pinterest.com' in url:
                extractor = 'pinterest'
            else:
                extractor = 'other'
        else:
            # Map common names
            if extractor == 'twittercard':
                extractor = 'twitter'
            elif extractor == 'pinterestboard' or extractor == 'pinterestpin':
                extractor = 'pinterest'
                
        is_playlist = info.get('_type') == 'playlist'
        
        if is_playlist:
            # Handle playlist (e.g. carousel)
            entries = []
            raw_entries = info.get('entries', [])
            for i, entry in enumerate(raw_entries):
                if not entry:
                    continue
                entry_title = entry.get('title') or f"Item {i+1}"
                entry_url = entry.get('url') or entry.get('webpage_url') or url
                entry_thumb = entry.get('thumbnail') or info.get('thumbnail')
                
                # Check if it has formats
                entries.append({
                    "index": i + 1,
                    "title": entry_title,
                    "url": entry_url,
                    "thumbnail": entry_thumb,
                    "formats": get_media_formats(entry, extractor)
                })
                
            return {
                "success": True,
                "is_playlist": True,
                "title": info.get("title") or "Album / Playlist",
                "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                "platform": extractor,
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description") or "",
                "entries": entries
            }
        else:
            # Get direct playable stream URL for preview in browser (CORS-accessible or direct stream link)
            video_url = info.get('url')
            if not video_url and info.get('formats'):
                # For YouTube, find progressive formats (video + audio) that can play natively in browser
                progressive_formats = [
                    f for f in info.get('formats', [])
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4' and f.get('url')
                ]
                if progressive_formats:
                    progressive_formats.sort(key=lambda x: x.get('height') or 0, reverse=True)
                    video_url = progressive_formats[0].get('url')
                else:
                    both_formats = [
                        f for f in info.get('formats', [])
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url')
                    ]
                    if both_formats:
                        video_url = both_formats[0].get('url')

            return {
                "success": True,
                "is_playlist": False,
                "title": info.get("title") or "Media File",
                "thumbnail": info.get("thumbnail"),
                "duration": format_duration(info.get("duration")),
                "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                "platform": extractor,
                "description": info.get("description") or "",
                "formats": get_media_formats(info, extractor),
                "video_url": video_url
            }

def download(url, format_id, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Standard format downloads
    if format_id == 'thumbnail':
        try:
            # First extract to get thumbnail url
            ydl_opts = {
                'skip_download': True, 
                'quiet': True, 
                'no_warnings': True, 
                'logger': MyLogger(),
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios']
                    }
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb_url = info.get('thumbnail')
                if not thumb_url:
                    return {"success": False, "error": "No thumbnail URL found"}
                    
                title = info.get('title') or 'thumbnail'
                # Clean title for filename
                safe_title = "".join([c for c in title if c.isalnum() or c==' ']).strip()
                if not safe_title:
                    safe_title = 'thumbnail'
                filename = f"{safe_title}.jpg"
                filepath = os.path.join(output_dir, filename)
                
                # Download thumbnail
                urllib.request.urlretrieve(thumb_url, filepath)
                return {"success": True, "filepath": filepath, "filename": filename}
        except Exception as e:
            return {"success": False, "error": f"Failed to download thumbnail: {str(e)}"}
            
    # Video/Audio downloads via yt-dlp
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'logger': MyLogger(),
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    
    # Configure options based on format_id
    if format_id == '1080p':
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_id == '720p':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_id == '480p':
        ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_id == '360p':
        ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_id == 'hq-video':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_id in ['mp3-320', 'mp3-128']:
        bitrate = '320' if format_id == 'mp3-320' else '128'
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': bitrate,
        }]
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloads = info.get('requested_downloads', [])
            if downloads:
                filepath = downloads[0].get('filepath')
                filename = os.path.basename(filepath)
                return {"success": True, "filepath": filepath, "filename": filename}
            else:
                filepath = info.get('_filename')
                if filepath and os.path.exists(filepath):
                    return {"success": True, "filepath": filepath, "filename": os.path.basename(filepath)}
                
                return {"success": False, "error": "No files downloaded"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MediaDrop Downloader Engine")
    parser.add_argument("--action", required=True, choices=["extract", "download"], help="Action to perform")
    parser.add_argument("--url", required=True, help="URL of the media")
    parser.add_argument("--format", help="Format ID (for download)")
    parser.add_argument("--output-dir", help="Output directory (for download)")
    
    args = parser.parse_args()
    
    if args.action == "extract":
        result = extract(args.url)
        print(json.dumps(result))
    elif args.action == "download":
        if not args.format:
            print(json.dumps({"success": False, "error": "--format is required for download action"}))
            sys.exit(1)
        if not args.output_dir:
            print(json.dumps({"success": False, "error": "--output-dir is required for download action"}))
            sys.exit(1)
            
        result = download(args.url, args.format, args.output_dir)
        print(json.dumps(result))
