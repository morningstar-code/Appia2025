"use client"
import { useState } from 'react'
import { Menu, X } from 'lucide-react'

export default function Navigation() {
  const [isOpen, setIsOpen] = useState(false)

  const toggleMenu = () => {
    setIsOpen(!isOpen)
  }

  return (
    <nav>
      <div className="hidden md:flex items-center space-x-6">
        <a href="#" className="hover:text-primary">About</a>
        <a href="#" className="hover:text-primary">Companies</a>
        <a href="#" className="hover:text-primary">Startup Jobs</a>
        <a href="#" className="hover:text-primary">Find a Co-Founder</a>
        <a href="#" className="hover:text-primary">Library</a>
        <a href="#" className="hover:text-primary">SAFE</a>
        <a href="#" className="hover:text-primary">Resources</a>
        <button className="bg-primary text-secondary rounded-full px-4 py-2 hover:bg-opacity-80 transition-colors">Apply for F2025 batch</button>
        <button className="ml-2">Apply</button>
      </div>

      {/* Mobile Menu Button */}
      <div className="md:hidden">
        <button onClick={toggleMenu} className="text-text hover:text-primary">
          {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Menu (Conditional Rendering) */}
      {isOpen && (
        <div className="md:hidden absolute top-16 right-0 bg-secondary shadow-md rounded-md py-2 px-4 w-64">
          <a href="#" className="block py-2 hover:text-primary">About</a>
          <a href="#" className="block py-2 hover:text-primary">Companies</a>
          <a href="#" className="block py-2 hover:text-primary">Startup Jobs</a>
          <a href="#" className="block py-2 hover:text-primary">Find a Co-Founder</a>
          <a href="#" className="block py-2 hover:text-primary">Library</a>
          <a href="#" className="block py-2 hover:text-primary">SAFE</a>
          <a href="#" className="block py-2 hover:text-primary">Resources</a>
          <button className="block bg-primary text-secondary rounded-full px-4 py-2 hover:bg-opacity-80 transition-colors w-full text-center mt-2">Apply for F2025 batch</button>
          <button className="block mt-2 text-center">Apply</button>
        </div>
      )}
    </nav>
  )
}