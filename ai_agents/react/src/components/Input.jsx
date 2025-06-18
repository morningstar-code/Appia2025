import React from 'react';

export function Input({ value, onChange, placeholder }) {
  return (
    <input
      type="text"
      className="input"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
    />
  );
}