from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
# Importing your functions directly from downloader.py
from downloader import extract, download

app = Flask(__name__)
CORS(app) # Allows communication from your front-end

# Temporary directory on the cloud instance to store downloaded files
DOWNLOAD_DIR = "/tmp/mediadrop_downloads"

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
    data = request.json
    url = data.get('url')
    format_id = data.get('format')
    
    if not url or not format_id:
        return jsonify({"success": False, "error": "URL and Format ID are required"}), 400
        
    # Triggering your download function
    result = download(url, format_id, DOWNLOAD_DIR)
    
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
