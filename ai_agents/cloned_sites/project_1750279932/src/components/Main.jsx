import React from 'react';

function Main() {
  return (
    <main>
      <h2>Welcome!</h2>
      <p><code>{"primary_font": "sans-serif",}</code></p>
      <button className="primary-button">Primary Button</button>
      <button className="secondary-button">Secondary Button</button>
      <input type="text" className="text-input" placeholder="Enter text" />
    </main>
  );
}

export default Main;