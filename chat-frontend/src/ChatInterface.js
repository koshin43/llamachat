import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

function ChatInterface({ sessionId }) {
  const [chats, setChats] = useState([]);
  const [inputText, setInputText] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [popup, setPopup] = useState({ visible: false, message: '' });


  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await axios.post('http://localhost:5000/get_session_messages', { session_id: sessionId });
        const sessionChats = response.data.messages;
        setChats(sessionChats);
      } catch (error) {
        console.error("Error fetching session messages:", error);
      }
    };
    async function fetchFiles() {
      try {
          const response = await axios.get(`http://localhost:5000/get_files/${sessionId}`);
          setUploadedFiles(response.data);
      } catch (error) {
          console.error("Error fetching files:", error);
      }
  }

    if (sessionId) {
      fetchMessages();
      fetchFiles();
    }
  }, [sessionId]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      text: inputText,
      session_id: sessionId
      // Add other payload fields as required by your backend
    };

    try {
      const response = await axios.post('http://localhost:5000/generate_text', payload);
      const generatedText = response.data.response;

      setChats([...chats, { sender: 'user', text: inputText }, { sender: 'llm', text: generatedText }]);
      setInputText('');
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  const onDrop = useCallback(acceptedFiles => {
    // Loop through accepted files
    acceptedFiles.forEach(file => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
  
      axios.post('http://localhost:5000/upload_file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      .then(response => {
        setPopup({ visible: true, message: 'Files uploaded successfully!' });
        console.log('File uploaded successfully:', response.data);
      })
      .catch(error => {
        setPopup({ visible: true, message: 'File upload failed!' });
        console.error('Error uploading file:', error);
      })
      .finally(() => {
        setTimeout(() => setPopup({ visible: false, message: '' }), 3000); // Hide popup after 3 seconds
      });
    });
    acceptedFiles.forEach(file => {
      setUploadedFiles(prevFiles => [...prevFiles, file.name]);
  }); 
  }, [sessionId]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, 
    noClick: true, 
    noKeyboard: true
  });


  return (
    <div className="chat-interface">
      {popup.visible && (
        <div className="popup">
          {popup.message}
        </div>
      )}
      <div className="chat-message">
        {chats.map((chat, index) => (
          <div key={index} className={`chat-message ${chat.sender}`}>
            {chat.text}
          </div>
        ))}
      </div>
      <div className="chat-input-area">
        <form {...getRootProps()} onSubmit={handleSubmit}>
        <input {...getInputProps()} style={{ display: 'none' }} />
          <input
            type="text"
            value={inputText}
            onChange={handleInputChange}
            placeholder="Type a message or drag a file here"
          />
          {isDragActive && <div className="drop-message">Drop the files here...</div>}
          <button type="submit">Send</button>
        </form>
      </div>
      <div className="uploaded-files">
        {uploadedFiles.map((fileName, index) => (
            <div key={index} className="uploaded-file">
                <span className="file-icon">📄</span> {fileName}
            </div>
        ))}
      </div>
    </div>
  );
}

export default ChatInterface;