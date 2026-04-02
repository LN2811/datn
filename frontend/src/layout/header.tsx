import { Link } from 'react-router-dom'

import './header.css'

export function HeaderComponent() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link to="/" className="site-header__brand">
          LOC Tracking
        </Link>
        <nav className="site-header__nav">
          <Link to="/" className="site-header__link">
            Home
          </Link>
          <Link to="/dashboard" className="site-header__link">
            Dashboard
          </Link>
          <Link to="/login" className="site-header__link">
            Login
          </Link>
        </nav>
      </div>
    </header>
  )
}
