import { tabItems } from '../constants';
import type { AdminSection } from '../types';

type AdminTabsProps = {
  activeSection: AdminSection;
  onChange: (section: AdminSection) => void;
};

export function AdminTabs({ activeSection, onChange }: AdminTabsProps) {
  return (
    <nav className="admin-page__tabs" aria-label="Chuc nang quan tri">
      {tabItems.map(({ section, icon: Icon, label }) => (
        <button
          key={section}
          className={activeSection === section ? 'admin-page__tab admin-page__tab--active' : 'admin-page__tab'}
          type="button"
          onClick={() => onChange(section)}
        >
          <Icon size={18} />
          {label}
        </button>
      ))}
    </nav>
  );
}
