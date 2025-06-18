import React from 'react';
import { Menu } from 'lucide-react';

function Header() {
  return (
    <header>
      <h1>Vanilla Website</h1>
      <Menu />
      <p><code>{"header": "```json"}</code></p>
    </header>
  );
}

export default Header;