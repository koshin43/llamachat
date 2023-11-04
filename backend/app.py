from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import uuid
from flask_cors import CORS
import randomname
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_sessions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Session(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, default=lambda: randomname.generate('v/web', 'adj/algorithms', ('n/data_structures')))
    # Modify relationship to include cascade option
    messages = db.relationship('Message', backref='session', lazy=True, cascade='all, delete-orphan')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    sender = db.Column(db.String(100), nullable=False)  # 'user' or 'llm'
    
    # Ensure deletion cascade from the database side
    session_id = db.Column(db.String(36), db.ForeignKey('session.id', ondelete='CASCADE'), nullable=False)


with app.app_context():
    db.create_all()

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")

@app.route('/generate_text', methods=['POST'])
def generate_text():
    input_text = request.json.get('text')
    session_id = request.json.get('session_id')

    # Construct the payload for the LLM
    payload = {
        "inputs": [
            {
                "name": "question",
                "shape": [1,],
                "datatype": "BYTES",
                "data": ["[INST]\n" + input_text + "[\INST]\n"],
                "parameters": {
                    "content_type": "np"
                }
            },
        ]
    }

    # Send POST request to LLM endpoint
    response = requests.post(LLM_ENDPOINT, json=payload, verify=False)
    if response.status_code != 200:
        return jsonify({'error': 'LLM service unavailable'}), response.status_code

    # Extract the generated text from the response
    res = response.json()
    generated_text = res["outputs"][0]["data"][0].split("[\INST]\n")[1]

    # Save the input text and generated text as messages in the session
    with app.app_context():
        session = Session.query.get(session_id)
        if session:
            input_message = Message(text=input_text, sender='user', session=session)
            generated_message = Message(text=generated_text, sender='llm', session=session)
            db.session.add(input_message)
            db.session.add(generated_message)
            db.session.commit()
        else:
            return jsonify({'error': 'Session does not exist'}), 404

    return jsonify({'response': generated_text})

@app.route('/create_session', methods=['POST'])
def create_session():
    session = Session()
    db.session.add(session)
    db.session.commit()
    return jsonify({'message': f'Session {session.id} created.', 'session_id': session.id, 'session_name': session.name})

@app.route('/rename_session', methods=['POST'])
def rename_session():
    data = request.json
    session_id = data['session_id']
    new_name = data['new_name']

    session = Session.query.get(session_id)
    if session:
        session.name = new_name
        db.session.commit()
        return jsonify({'message': 'Session renamed successfully', 'session_id': session_id, 'session_name': new_name})
    else:
        return jsonify({'error': 'Session not found'}), 404


@app.route('/get_session_messages', methods=['POST'])
def get_session_messages():
    session_id = request.json.get('session_id')
    session = Session.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    messages = [{'text': msg.text, 'sender': msg.sender} for msg in session.messages]
    return jsonify({'session_id': session_id, 'messages': messages})

@app.route('/get_sessions', methods=['GET'])
def get_sessions():
    all_sessions = Session.query.all()
    sessions_list = [{'id': session.id, 'name': session.name} for session in all_sessions]
    return jsonify({'sessions': sessions_list})

@app.route('/delete_session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    print(session_id)
    session = Session.query.get(session_id)
    if session:
        db.session.delete(session)
        db.session.commit()
        return jsonify({'message': f'Session {session_id} deleted.'})
    else:
        return jsonify({'error': 'Session does not exist'}), 404

if __name__ == '__main__':
    app.run(debug=True)
