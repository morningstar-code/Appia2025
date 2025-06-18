import React from 'react';

export function Button({ variant = 'primary', children, onClick }) {
  return (
    <button className={`button ${variant}`} onClick={onClick}>
      {children}
    </button>
  );
}