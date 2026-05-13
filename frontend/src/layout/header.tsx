import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'

import './header.css'

export function HeaderComponent() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      navigate('/', { replace: true })
    } finally {
      setIsLoggingOut(false)
    }
  }

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
          {user ? (
            <>
              <Link
                to={user.is_superuser ? '/admin' : '/dashboard'}
                className="site-header__link site-header__link--account"
              >
                {user.email}
              </Link>
              <button
                type="button"
                className="site-header__link site-header__logout"
                disabled={isLoggingOut}
                onClick={() => void handleLogout()}
              >
                {isLoggingOut ? 'Logging out...' : 'Logout'}
              </button>
            </>
          ) : (
            <Link to="/login" className="site-header__link">
              Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
