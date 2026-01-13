import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

function App() {
  const [apiStatus, setApiStatus] = useState('Checking...');

  useEffect(() => {
    axios.get(`${API_URL}/`)
      .then(response => {
        setApiStatus(`Connected: ${response.data.message}`);
      })
      .catch(error => {
        setApiStatus(`Error: ${error.message}`);
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Minimal Cell Model</h1>
        <p>API Status: {apiStatus}</p>
      </header>
    </div>
  );
}

export default App;
