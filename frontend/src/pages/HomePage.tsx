import { useEffect, useState } from 'react'
import {
  ArrowRight,
  Award,
  BookOpen,
  Briefcase,
  CheckCircle,
  Clock,
  Code,
  Crown,
  FileText,
  Heart,
  Rocket,
  Shield,
  Target,
  Trophy,
  User,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { HeaderComponent } from '@/layout/header'

import './HomePage.css'

const systemStats = [
  {
    icon: Users,
    label: 'Students',
    value: '1,250',
    tone: 'blue',
  },
  {
    icon: Code,
    label: 'Total LOC',
    value: '125,000',
    tone: 'green',
  },
  {
    icon: FileText,
    label: 'Assignments',
    value: '127',
    tone: 'violet',
  },
  {
    icon: Trophy,
    label: 'Pass rate',
    value: '78.5%',
    tone: 'amber',
  },
]

const features = [
  {
    icon: Code,
    title: 'Assignment workspace',
    description:
      'Track coding tasks, submissions, and progress in one place.',
    tone: 'blue',
    roles: ['guest', 'member'],
  },
  {
    icon: FileText,
    title: 'Automatic LOC tracking',
    description:
      'Submissions can be measured consistently to support course evaluation.',
    tone: 'green',
    roles: ['guest', 'member'],
  },
  {
    icon: Trophy,
    title: 'Progress visibility',
    description: 'Teachers and learners can review output and completion status.',
    tone: 'amber',
    roles: ['guest', 'member'],
  },
  {
    icon: Users,
    title: 'Class management',
    description: 'Operational views help manage users, classes, and access.',
    tone: 'violet',
    roles: ['admin'],
  },
  {
    icon: CheckCircle,
    title: 'Review and oversight',
    description: 'Administrative users can oversee flow quality and platform use.',
    tone: 'orange',
    roles: ['admin'],
  },
  {
    icon: Award,
    title: 'System-wide control',
    description: 'Admins can manage high-level settings and platform governance.',
    tone: 'rose',
    roles: ['admin'],
  },
]

const howItWorks = [
  {
    step: 1,
    title: 'Receive assignment',
    description:
      'Teachers create programming assignments and distribute them to students.',
    icon: BookOpen,
  },
  {
    step: 2,
    title: 'Write code',
    description: 'Students implement the assignment according to the criteria.',
    icon: Code,
  },
  {
    step: 3,
    title: 'Submit result',
    description:
      'The system stores submissions and calculates Lines of Code automatically.',
    icon: FileText,
  },
  {
    step: 4,
    title: 'Reach the target',
    description: 'LOC is accumulated until the subject passing target is met.',
    icon: Target,
  },
]

type RoleInfo = {
  title: string
  icon: typeof User
  tone: string
  description: string
}

const getRoleInfo = (audience: 'guest' | 'member' | 'admin'): RoleInfo => {
  switch (audience) {
    case 'admin':
      return {
        title: 'Admin',
        icon: Crown,
        tone: 'slate',
        description: 'Manage all users and platform settings.',
      }
    case 'member':
      return {
        title: 'Signed-in user',
        icon: User,
        tone: 'blue',
        description: 'Open your workspace after login and continue with assigned tasks.',
      }
    default:
      return {
        title: 'Guest',
        icon: Briefcase,
        tone: 'slate',
        description: 'Sign in to see your dashboard and access protected features.',
      }
  }
}

export default function HomePage() {
  const { user, isCheckingAuth } = useAuth()
  const [currentTime, setCurrentTime] = useState(new Date())
  const audience: 'guest' | 'member' | 'admin' = isCheckingAuth
    ? 'guest'
    : user?.is_superuser
      ? 'admin'
      : user
        ? 'member'
        : 'guest'
  const roleInfo = getRoleInfo(audience)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)

    return () => window.clearInterval(timer)
  }, [])

  const relevantFeatures = features.filter((feature) =>
    feature.roles.includes(audience)
  )

  const identityItems = user
    ? [
        {
          label: 'Account email',
          value: user.email,
        },
        {
          label: 'Account status',
          value: user.is_active ? 'Active' : 'Inactive',
        },
        {
          label: 'Access level',
          value: user.is_superuser ? 'Administrator' : 'Authenticated user',
        },
      ]
    : [
        {
          label: 'Session',
          value: isCheckingAuth ? 'Checking sign-in state...' : 'Not signed in',
        },
        {
          label: 'Access',
          value: 'Public homepage only',
        },
        {
          label: 'Next step',
          value: 'Login to continue',
        },
      ]

  return (
    <main className="home-page">
      <div className="home-page__orb home-page__orb--left" aria-hidden="true" />
      <div
        className="home-page__orb home-page__orb--right"
        aria-hidden="true"
      />
      <div className='head'>
        <HeaderComponent />
      </div>

      <div className="home-page__container">
        <section className="home-page__hero">
          <div className="home-page__hero-copy">
            <span className="home-page__eyebrow">FPT University platform</span>
            <h1 className="home-page__title">
              LOC Tracking System for programming courses
            </h1>
            <p className="home-page__subtitle">
              A single workspace for assignments, submissions, LOC tracking,
              progress review, and subject completion monitoring.
            </p>

            <div className="home-page__actions">
              {user ? (
                <Link className="home-page__button home-page__button--primary" to={user.is_superuser ? '/admin' : '/dashboard'}>
                  <Rocket size={18} />
                  Open workspace
                </Link>
              ) : (
                <Link className="home-page__button home-page__button--primary" to="/login">
                  <Rocket size={18} />
                  Login
                </Link>
              )}
              <Link className="home-page__button home-page__button--secondary" to={user ? (user.is_superuser ? '/admin' : '/dashboard') : '/login'}>
                <ArrowRight size={18} />
                {user ? 'Continue' : 'Open sign-in page'}
              </Link>
            </div>
          </div>

          <aside className="home-page__hero-panel">
            <div className="home-page__panel-head">
              <div className={`home-page__role-mark home-page__role-mark--${roleInfo.tone}`}>
                <roleInfo.icon size={22} />
              </div>
              <div>
                <p className="home-page__panel-label">Current role</p>
                <h2 className="home-page__panel-title">{roleInfo.title}</h2>
              </div>
            </div>

            <p className="home-page__panel-text">{roleInfo.description}</p>

            <div className="home-page__meta-list">
              {identityItems.map((item) => (
                <div key={item.label} className="home-page__meta-item">
                  <span className="home-page__meta-key">{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </aside>
        </section>

        <section className="home-page__overview">
          <div className="home-page__section-copy">
            <span className="home-page__section-kicker">System goal</span>
            <h2>Track coding output, not just assignment status.</h2>
            <p>
              The platform helps students complete programming assignments,
              captures LOC automatically, and gives teachers a clearer view of
              learning progress.
            </p>
            <div className="home-page__badges">
              <span className={`home-page__badge home-page__badge--${roleInfo.tone}`}>
                <roleInfo.icon size={16} />
                {roleInfo.title}
              </span>
              {user ? (
                <span className="home-page__badge home-page__badge--neutral">
                  {user.email}
                </span>
              ) : (
                <span className="home-page__badge home-page__badge--neutral">
                  Public homepage
                </span>
              )}
            </div>
          </div>

          <div className="home-page__stats">
            {systemStats.map((stat) => (
              <article
                key={stat.label}
                className={`home-page__stat-card home-page__stat-card--${stat.tone}`}
              >
                <stat.icon className="home-page__stat-icon" size={22} />
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="home-page__section">
          <div className="home-page__section-copy home-page__section-copy--center">
            <span className="home-page__section-kicker">Workflow</span>
            <h2>From assignment delivery to subject completion</h2>
            <p>The core flow is compact, measurable, and visible to every role.</p>
          </div>

          <div className="home-page__timeline">
            {howItWorks.map((step) => (
              <article key={step.step} className="home-page__timeline-card">
                <div className="home-page__timeline-head">
                  <div className="home-page__timeline-icon">
                    <step.icon size={24} />
                  </div>
                  <span className="home-page__timeline-step">0{step.step}</span>
                </div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-page__section">
          <div className="home-page__section-copy home-page__section-copy--center">
            <span className="home-page__section-kicker">Role features</span>
            <h2>
              {user
                ? `Tools available for ${roleInfo.title}`
                : 'Core platform capabilities before sign-in'}
            </h2>
            <p>
              {user
                ? 'The homepage now highlights features based on the authenticated session.'
                : 'Guest users only see neutral product information until they log in.'}
            </p>
          </div>

          <div className="home-page__features">
            {relevantFeatures.map((feature) => (
              <article key={feature.title} className="home-page__feature-card">
                <div className={`home-page__feature-icon home-page__feature-icon--${feature.tone}`}>
                  <feature.icon size={22} />
                </div>
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="home-page__cta">
          <div className="home-page__cta-copy">
            <span className="home-page__section-kicker home-page__section-kicker--light">
              Next step
            </span>
            <h2>Ready to start working inside the platform?</h2>
            <p>
              {user
                ? 'Open your workspace and continue with the authenticated flow.'
                : 'Login first to continue with the authenticated flow and role-based access.'}
            </p>
          </div>

          <div className="home-page__cta-actions">
            <Link
              className="home-page__button home-page__button--light"
              to={user ? (user.is_superuser ? '/admin' : '/dashboard') : '/login'}
            >
              <ArrowRight size={18} />
              {user ? 'Open workspace' : 'Login now'}
            </Link>
            <Link
              className="home-page__button home-page__button--ghost"
              to={user ? '/' : '/login'}
            >
              <FileText size={18} />
              {user ? 'Stay on homepage' : 'Open sign-in page'}
            </Link>
          </div>
        </section>

        <footer className="home-page__footer">
          <div className="home-page__footer-item">
            <Clock size={16} />
            <span>Updated: {currentTime.toLocaleString('vi-VN')}</span>
          </div>
          <div className="home-page__footer-item">
            <Shield size={16} />
            <span>Stable system operation</span>
          </div>
          <div className="home-page__footer-item">
            <Heart size={16} />
            <span>Developed for FPT University</span>
          </div>
        </footer>
      </div>
    </main>
  )
}
