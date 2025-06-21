import React from 'react';
import { Inter } from 'next/font/google';
import { ShieldCheck, ArrowRightFromLine, Search } from 'lucide-react';
import MainContent from './components/MainContent';

const inter = Inter({ subsets: ['latin'] });

export default function Page() {
  return (
    <div className={`bg-[#ffffff] text-[#1e293b] min-h-screen font-sans ${inter.className}`}>
      <header className="bg-[#ffffff] shadow-md sticky top-0 z-50">
        <div className="container mx-auto px-4 py-6 flex items-center justify-between">
          <a href="/" className="text-2xl font-bold text-[#2563eb]">
            Logo
          </a>
          <nav className="hidden md:flex space-x-6">
            <a href="#" className="hover:text-[#2563eb]">
              Home
            </a>
            <a href="#" className="hover:text-[#2563eb]">
              About
            </a>
            <a href="#" className="hover:text-[#2563eb]">
              Services
            </a>
            <a href="#" className="hover:text-[#2563eb]">
              Contact
            </a>
          </nav>
          <div className="flex items-center space-x-4">
            <button className="hidden md:block bg-[#2563eb] text-white py-2 px-4 rounded-md hover:bg-[#0ea5e9]">
              Sign Up
            </button>
            <button className="md:hidden">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12">
        <section className="mb-16">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div className="order-2 md:order-1">
              <h1 className="text-4xl md:text-5xl font-bold mb-4">
                Your Modern Next.js App
              </h1>
              <p className="text-lg text-[#475569] mb-8">
                Built with Next.js 14, Tailwind CSS, and lucide-react icons.
              </p>
              <div className="flex items-center space-x-4">
                <button className="bg-[#2563eb] text-white py-3 px-6 rounded-md hover:bg-[#0ea5e9]">
                  Get Started
                </button>
                <a href="#" className="text-[#2563eb] hover:underline">
                  Learn More
                </a>
              </div>
            </div>
            <div className="order-1 md:order-2">
              <img
                src="/hero-image.svg"
                alt="Hero Image"
                className="rounded-lg shadow-lg"
              />
            </div>
          </div>
        </section>

        <section className="mb-16">
          <h2 className="text-3xl font-semibold mb-6">Key Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
              <ShieldCheck className="text-[#2563eb] w-8 h-8 mb-4" />
              <h3 className="text-xl font-semibold mb-2">Security</h3>
              <p className="text-[#475569]">Enhanced security features to protect your data.</p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
              <ArrowRightFromLine className="text-[#2563eb] w-8 h-8 mb-4" />
              <h3 className="text-xl font-semibold mb-2">Scalability</h3>
              <p className="text-[#475569]">Easily scale your application to meet growing demands.</p>
            </div>
            <div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
              <Search className="text-[#2563eb] w-8 h-8 mb-4" />
              <h3 className="text-xl font-semibold mb-2">SEO Optimized</h3>
              <p className="text-[#475569]">Improved search engine optimization for better visibility.</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-3xl font-semibold mb-6">Main Content Area</h2>
          <MainContent />
        </section>
      </main>

      <footer className="bg-[#e2e8f0] py-6 text-center text-[#475569]">
        <p>&copy; {new Date().getFullYear()} Your Company. All rights reserved.</p>
      </footer>
    </div>
  );
}