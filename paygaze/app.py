from flask import Flask, render_template, request, jsonify, session
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import os
from pymongo import MongoClient
import base64
from io import BytesIO
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '8e9058d2df2bfec57b0b2f6281d3f39a3e458c2ede6f8840'  

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['facial_recognition_db']
users_collection = db['users']

# Load pre-trained OpenCV models
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route('/')
def index():
    return render_template('index.html')

# Helper function to decode image
def decode_image(image_data):
    img_data = base64.b64decode(image_data.split(',')[1])
    img = Image.open(BytesIO(img_data))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# Helper function for face detection
def detect_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return faces

# Helper function to compute face encoding
def compute_face_encoding(face_img):
    face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    return face_img.flatten().tolist()  # Simplistic encoding for demonstration

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'Username already exists!'}), 400

    hashed_password = generate_password_hash(password)
    users_collection.insert_one({'username': username, 'password': hashed_password, 'faces': []})
    return jsonify({'message': 'Registration successful!'}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        user = users_collection.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return jsonify({'message': 'Login successful!'}), 200
        else:
            return jsonify({'message': 'Invalid credentials!'}), 401
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/enroll', methods=['POST'])
def enroll():
    if 'username' not in session:
        return jsonify({'message': 'User not logged in!'}), 401

    file = request.files.get('file')
    if file:
        img = Image.open(file.stream)
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        faces = detect_faces(img)

        if len(faces) == 0:
            return jsonify({'message': 'No faces detected!'}), 400

        username = session['username']
        user = users_collection.find_one({'username': username})
        
        if user:
            faces_list = user.get('faces', [])
            for (x, y, w, h) in faces:
                face_img = img[y:y+h, x:x+w]
                face_encoding = compute_face_encoding(face_img)
                faces_list.append(face_encoding)
            users_collection.update_one({'username': username}, {'$set': {'faces': faces_list}})
            return jsonify({'message': 'Enrollment successful!'}), 200
        else:
            return jsonify({'message': 'User not found!'}), 404
    return jsonify({'message': 'No file uploaded!'}), 400

@app.route('/authenticate', methods=['POST'])
def authenticate():
    if 'username' not in session:
        return jsonify({'message': 'User not logged in!'}), 401

    file = request.files.get('file')
    if file:
        img = Image.open(file.stream)
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        faces = detect_faces(img)

        if len(faces) == 0:
            return jsonify({'message': 'No faces detected!'}), 400

        username = session['username']
        user = users_collection.find_one({'username': username})
        
        if user:
            faces_list = user.get('faces', [])
            for (x, y, w, h) in faces:
                face_img = img[y:y+h, x:x+w]
                face_encoding = compute_face_encoding(face_img)
                # Simple recognition by checking similarity of face encodings
                for stored_face_encoding in faces_list:
                    if np.linalg.norm(np.array(face_encoding) - np.array(stored_face_encoding)) < 1000:
                        return jsonify({'message': 'Face recognized!'}), 200
            
            return jsonify({'message': 'Face not recognized!'}), 401
        else:
            return jsonify({'message': 'User not found!'}), 404
    return jsonify({'message': 'No file uploaded!'}), 400

@app.route('/payment', methods=['POST'])
def payment():
    if 'username' not in session:
        return jsonify({'message': 'User not logged in!'}), 401

    # Add your payment processing logic here
    # For demonstration purposes, assuming payment is always successful
    return jsonify({'message': 'Payment processed successfully!'}), 200

if __name__ == '__main__':
    app.run()
  