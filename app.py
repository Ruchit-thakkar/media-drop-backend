from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import uuid
import shutil
import time
# Importing your functions directly from downloader.py
from downloader import extract, download

app = Flask(__name__)
CORS(app) # Allows communication from your front-end

# Temporary directory on the cloud instance to store downloaded files
DOWNLOAD_DIR = "/tmp/mediadrop_downloads"

def cleanup_old_downloads(directory, max_age_seconds=1800):
    """Deletes subdirectories in the download path that are older than max_age_seconds."""
    if not os.path.exists(directory):
        return
    try:
        now = time.time()
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                # Check modification time
                mtime = os.path.getmtime(item_path)
                if now - mtime > max_age_seconds:
                    shutil.rmtree(item_path)
    except Exception as e:
        app.logger.error(f"Error cleaning up old downloads: {e}")

@app.route('/wake-up', methods=['GET'])
def wake_up():
    """Triggered instantly by front-end mount to boot server out of sleep mode"""
    return jsonify({"status": "Server is awake and ready!", "code": 200})

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Receives a URL from the front-end and extracts media metadata"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"success": False, "error": "URL parameter is missing"}), 400
        
    result = extract(url)
    return jsonify(result)

@app.route('/api/download', methods=['POST'])
def api_download():
    """Handles the media processing and sends the finished file back to front-end"""
    # Clean up old files to prevent disk usage from growing
    cleanup_old_downloads(DOWNLOAD_DIR)

    data = request.json
    url = data.get('url')
    format_id = data.get('format')
    
    if not url or not format_id:
        return jsonify({"success": False, "error": "URL and Format ID are required"}), 400
        
    # Create a unique isolated subdirectory for this download request
    request_id = str(uuid.uuid4())
    download_subdir = os.path.join(DOWNLOAD_DIR, request_id)

    # Triggering your download function
    result = download(url, format_id, download_subdir)
    
    if result.get("success"):
        filepath = result.get("filepath")
        filename = result.get("filename")
        try:
            # Sends the file securely as an attachment download to your browser
            return send_file(filepath, as_attachment=True, download_name=filename)
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to send file: {str(e)}"}), 500
    else:
        return jsonify(result), 500

if __name__ == '__main__':
    # Railway passes a dynamic port via environment variables
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
