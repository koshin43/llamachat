from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import uuid
from flask_cors import CORS
import randomname
import os
from dotenv import load_dotenv
from langchain.text_splitter import Language
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import LanguageParser
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import shutil
from model import CustomLLM
from langchain.chains import ConversationalRetrievalChain
load_dotenv()


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_sessions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
llm = CustomLLM()
model_name = "sentence-transformers/all-mpnet-base-v2"
model_kwargs = {"device": "cpu"}
embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)

class Session(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, default=lambda: randomname.generate('v/web', 'adj/algorithms', ('n/data_structures')))
    # Modify relationship to include cascade option
    messages = db.relationship('Message', backref='session', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('File', backref='session', lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    sender = db.Column(db.String(100), nullable=False)  # 'user' or 'llm'
    
    # Ensure deletion cascade from the database side
    session_id = db.Column(db.String(36), db.ForeignKey('session.id', ondelete='CASCADE'), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    session_id = db.Column(db.String(36), db.ForeignKey('session.id', ondelete='CASCADE'), nullable=False)



with app.app_context():
    db.create_all()



@app.route('/generate_text', methods=['POST'])
def generate_text():
    input_text = request.json.get('text')
    session_id = request.json.get('session_id')

    session = Session.query.get(session_id)
    messages = [{'role': msg.sender,'text': msg.text} for msg in session.messages]
    tuples_array = [(item['text'] if item['role'] == 'ai' else '',
                        next((usr['text'] for usr in messages if usr['role'] == 'user'), ''))
                        for item in messages if item['role'] == 'ai']
    session_vectorstore  = UPLOAD_FOLDER +"/"+session_id+"/faiss_index"
    result={}
    if os.path.isdir(session_vectorstore):
        vecstore = FAISS.load_local(session_vectorstore, embeddings)
        chain = ConversationalRetrievalChain.from_llm(llm, vecstore.as_retriever(search_type="mmr",search_kwargs={"k": 1}), return_source_documents=True)
        result = chain({"question":input_text, "chat_history":tuples_array})
    else:
        context = '\n'.join([msg.text for msg in session.messages][-4:])
        result['answer']= llm(context +"\n"+input_text)
    # if response.status_code != 200:
    #     return jsonify({'error': 'LLM service unavailable'}), response.status_code

    # Save the input text and generated text as messages in the session
    with app.app_context():
        session = Session.query.get(session_id)
        if session:
            input_message = Message(text=input_text, sender='user', session=session)
            generated_message = Message(text=result['answer'], sender='llm', session=session)
            db.session.add(input_message)
            db.session.add(generated_message)
            db.session.commit()
        else:
            return jsonify({'error': 'Session does not exist'}), 404

    return jsonify({'response': result['answer']})

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
        session_folder = UPLOAD_FOLDER+"/"+str(session_id)
        if os.path.isdir(session_folder):
            try:
                shutil.rmtree(session_folder)
                app.logger.info(f"Session folder {session_folder} deleted successfully.")
            except OSError as e:
                app.logger.error(f"Error deleting session folder {session_folder}: {e}")
        db.session.delete(session)
        db.session.commit()
        return jsonify({'message': f'Session {session_id} deleted.'})
    else:
        return jsonify({'error': 'Session does not exist'}), 404
    
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
@app.route('/upload_file', methods=['POST'])
def upload_file():
    session_id = request.form['session_id']
    files = request.files.getlist('file')

    if not files or session_id is None:
        return jsonify({'error': 'No files or session_id provided'}), 400
    
    for file in files:
        if file.filename == '':
            continue  # Skip empty filenames
        session_folder = UPLOAD_FOLDER+"/"+str(session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        # Read the file content and process as before
        file_path = os.path.join(session_folder, file.filename)
        file.save(file_path)
        
        loader = GenericLoader.from_filesystem(
            session_folder,
            glob="**/*",
            suffixes=[".py"],
            parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
        )
        documents = loader.load()
        python_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON, chunk_size=2000, chunk_overlap=200
        )
        texts = python_splitter.split_documents(documents)
        
        # storing embeddings in the vector store
        vectorstore = FAISS.from_documents(texts, embeddings)
        if os.path.isdir(session_folder+"/faiss_index"):
            existing = FAISS.load_local(session_folder+"/faiss_index", embeddings)
            vectorstore.merge_from(existing)

        vectorstore.save_local(session_folder+"/faiss_index")

        new_file = File(filename=file.filename, session_id=session_id)
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({'message': 'File uploaded and processed successfully'}), 200

    return jsonify({'error': 'Error processing file'}), 400

@app.route('/get_files/<session_id>', methods=['GET'])
def get_files(session_id):
    files = File.query.filter_by(session_id=session_id).all()
    filenames = [f.filename for f in files]
    return jsonify(filenames)

if __name__ == '__main__':
    app.run(debug=True)
