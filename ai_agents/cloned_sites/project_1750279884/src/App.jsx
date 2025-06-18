import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Main } from './components/Main';
import { Footer } from './components/Footer';

function App() {
  const [fade, setFade] = useState(false);

  useEffect(() => {
    setFade(true);
  }, []);

  return (
    <div className={`app-container ${fade ? 'fade-in' : ''}`}>
      <Header />
      <Main />
      <Footer />
    </div>
  );
}

export default App;