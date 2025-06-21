import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Example Domain',
  description: 'Example Domain',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="bg-background min-h-screen flex flex-col">
          <header className="bg-primary p-4 shadow-md">
            <div className="container mx-auto flex items-center justify-between">
              <a href="/" className="text-xl font-semibold text-text">
                Example Domain
              </a>
            </div>
          </header>
          <main className="flex-grow">
            {children}
          </main>
          <footer className="bg-secondary p-4 mt-8 text-center">
            <p className="text-xs text-text">© 2024 Example Domain</p>
          </footer>
        </div>
      </body>
    </html>
  )
}