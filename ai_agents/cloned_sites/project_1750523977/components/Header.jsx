import { Menu, X } from 'lucide-react'
import Navigation from './Navigation'

export default function Header() {
  return (
    <header className="bg-secondary text-text py-4 shadow-md">
      <div className="container flex items-center justify-between">
        <a href="/" className="text-xl font-semibold flex items-center">
          <Menu className="h-6 w-6 mr-2 text-primary" />
          Y Combinator
        </a>
        <Navigation />
      </div>
    </header>
  )
}