import os
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from llama_deploy import LlamaDeployClient, ControlPlaneConfig

app = Flask(__name__)

CORS(app)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
DATA_FOLDER = 'data/output'
ALLOWED_EXTENSIONS = {'csv'}

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client['buildathon']
files_collection = db['dataset'] 
query_collection = db['query']


# Function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route for file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    file_record = files_collection.find_one({'filename': file.filename})
    if file_record:
        return jsonify({'error': 'File already exist'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Store file metadata in MongoDB
        file_metadata = {
            'filename': filename,
            'upload_time': datetime.now(),
            'path': file_path
        }
        files_collection.insert_one(file_metadata)

        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 201

    return jsonify({'error': 'File type not allowed'}), 400


# Route for file download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        # Check if the file exists in the database
        # file_record = files_collection.find_one({'filename': filename})
        # if not file_record:
        #     return jsonify({'error': 'File not found in database'}), 404

        return send_from_directory(app.config['DATA_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found on server'}), 404


@app.route('/files', methods=['GET'])
def get_files():
    files = list(files_collection.find({}, {'_id': 0}))
    return jsonify(files)

@app.route('/search', methods=['POST'])
def process_request():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400

    # Validate required fields
    if 'query' not in data or 'filename' not in data:
        return jsonify({'error': 'Missing required fields: query and filename'}), 400

    # Extract fields
    query = data['query']
    filename = data['filename']

    client = LlamaDeployClient(ControlPlaneConfig())

    #session = client.get_or_create_session("session_id")
    session = client.create_session()

    result = session.run("report_gen_flow", query=query, filename=filename)

    client.delete_session(session.session_id)

    
    return jsonify({'message': 'Request processed successfully', 'query': query, 'filename': filename, 'output_file': result}), 200



# Health check route
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'message': 'Welcome to the Flask File Upload, Download, and MongoDB API'})


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
