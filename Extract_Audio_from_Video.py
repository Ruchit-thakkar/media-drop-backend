import os
import sys
import subprocess
import argparse
import json

def log_stderr(message):
    """Write log messages to stderr so stdout remains clean JSON for easy parsing."""
    sys.stderr.write(message + "\n")
    sys.stderr.flush()

def check_ffmpeg():
    """Verify if FFmpeg is installed and accessible in the system path."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def extract_audio(input_path, output_format="mp3", output_path=None, bitrate="192k"):
    """
    Extracts the audio track from a video file using FFmpeg.
    """
    if not os.path.exists(input_path):
        return {"success": False, "error": f"Input video file not found at: {input_path}"}

    if not check_ffmpeg():
        return {"success": False, "error": "FFmpeg utility is not installed or not in system PATH."}

    # Generate default output path if not specified
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_extracted.{output_format.lower()}"

    # Define FFmpeg audio arguments based on requested format
    fmt = output_format.lower()
    codec_args = []

    if fmt == "mp3":
        codec_args = ["-acodec", "libmp3lame", "-b:a", bitrate]
    elif fmt == "wav":
        codec_args = ["-acodec", "pcm_s16le", "-ar", "44100"]
    elif fmt == "m4a" or fmt == "aac":
        # Using m4a extension but native aac codec
        codec_args = ["-acodec", "aac", "-b:a", bitrate]
        if not output_path.endswith(".m4a") and not output_path.endswith(".aac"):
            output_path = os.path.splitext(output_path)[0] + ".m4a"
    elif fmt == "ogg":
        codec_args = ["-acodec", "libvorbis", "-b:a", bitrate]
    elif fmt == "flac":
        codec_args = ["-acodec", "flac"]
    else:
        # Fallback to copy original audio track without transcoding
        codec_args = ["-acodec", "copy"]

    # Construct the full FFmpeg command
    # -y: overwrite output files without asking
    # -i: input file path
    # -vn: disable video recording
    command = ["ffmpeg", "-y", "-i", input_path, "-vn"] + codec_args + [output_path]

    log_stderr(f"Running command: {' '.join(command)}")

    try:
        # Execute FFmpeg subprocess, capturing stderr for troubleshooting
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        
        # Verify the file was created and is not empty
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            return {
                "success": True,
                "output_path": os.path.abspath(output_path),
                "filename": os.path.basename(output_path),
                "filesize": file_size,
                "format": fmt
            }
        else:
            return {"success": False, "error": "FFmpeg completed but the output audio file was empty or not created."}

    except subprocess.CalledProcessError as e:
        error_output = e.stderr or "No error output returned from FFmpeg."
        return {"success": False, "error": f"FFmpeg execution failed: {error_output}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MediaDrop Backend Audio Extractor Engine")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav", "m4a", "aac", "ogg", "flac", "copy"], help="Output audio format")
    parser.add_argument("--output", help="Optional custom path for output file")
    parser.add_argument("--bitrate", default="192k", help="Audio quality bitrate (e.g. 128k, 192k, 320k)")

    args = parser.parse_args()

    result = extract_audio(
        input_path=args.input,
        output_format=args.format,
        output_path=args.output,
        bitrate=args.bitrate
    )

    # Print final result as JSON to stdout
    print(json.dumps(result))
