import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ChatInterface({ sessionId }) {
  const [chats, setChats] = useState([]);
  const [inputText, setInputText] = useState('');

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

    if (sessionId) {
      fetchMessages();
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

  return (
    <div className="chat-interface">
      <div className="chat-message">
        {chats.map((chat, index) => (
          <div key={index} className={`chat-message ${chat.sender}`}>
            {chat.text}
          </div>
        ))}
      </div>
      <div className="chat-input-area">
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={inputText}
            onChange={handleInputChange}
            placeholder="Type a message..."
          />
          <button type="submit">Send</button>
        </form>
      </div>
    </div>
  );
}

export default ChatInterface;