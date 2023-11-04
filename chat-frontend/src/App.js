import React, { useState, useEffect } from 'react';
import './App.css';
import ChatInterface from './ChatInterface';
import axios from 'axios';

function App() {
  const [currentSession, setCurrentSession] = useState(null);
  const [allSessions, setAllSessions] = useState([]);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [newSessionName, setNewSessionName] = useState("");

  const fetchSessions = async () => {
    try {
      const response = await fetch('http://localhost:5000/get_sessions');
      const data = await response.json();
      setAllSessions(data.sessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };
  
  useEffect(() => {
    fetchSessions();
  }, []);

  const createNewSession = async () => {
    try {
      const response = await axios.post('http://localhost:5000/create_session');
      const data = response.data;
      setCurrentSession(data.session_id);
      setAllSessions(prevSessions => [{ id: data.session_id, name: data.session_name }, ...prevSessions]);
    } catch (error) {
      console.error('Error creating session:', error);
    }
  };

   // Handler for renaming a session
   const handleRenameSession = async (sessionId) => {
    if (!newSessionName.trim()) return;
    try {
      const response = await axios.post('http://localhost:5000/rename_session', {
        session_id: sessionId,
        new_name: newSessionName
      });
      const updatedSession = response.data;
      setAllSessions(allSessions.map(session => 
        session.id === sessionId ? { ...session, name: updatedSession.session_name } : session
      ));
      setEditingSessionId(null); // Stop editing
      setNewSessionName(""); // Reset input
    } catch (error) {
      console.error('Error renaming session:', error);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      console.log("Attempting to delete Session ID:", sessionId);
      await axios.delete(`http://localhost:5000/delete_session/${sessionId}`);
      fetchSessions(); // Refetch sessions after deletion
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  return (
    <div className="App">
      <div className="sidebar">
        <button className="newChatButton" onClick={createNewSession}>New Chat</button>
        {allSessions.map(session => (
          <div key={session.id} className="session-item">
            <div className="session-content">
              {editingSessionId === session.id ? (
                <input 
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                  onBlur={() => handleRenameSession(session.id)}
                  onKeyPress={event => {
                    if (event.key === "Enter") {
                      handleRenameSession(session.id);
                    }
                  }}
                  autoFocus
                />
              ) : (
                <>
                  <button className="sessionButton" onClick={() => setCurrentSession(session.id)}>
                  {session.name}
                  </button>
                </>
              )}
            </div>
            <div className="session-actions">
              <button className="editButton" onClick={() => {
                setEditingSessionId(session.id);
                setNewSessionName(session.name);
              }}>
                <img src="/assets/edit_icon.svg" alt="Edit" /> 
              </button>
              <button className="deleteButton" onClick={() => handleDeleteSession(session.id)}>
                <img src="/assets/delete_icon.svg" alt="Delete" /> 
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="chatArea">
        {currentSession && <ChatInterface sessionId={currentSession} />}
      </div>
    </div>
  );
}

export default App;