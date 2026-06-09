import type { StatCardItem } from '../types';

type StatCardsProps = {
  cards: StatCardItem[];
  isLoading: boolean;
};

export function StatCards({ cards, isLoading }: StatCardsProps) {
  return (
    <section className="admin-page__grid admin-page__grid--stats">
      {cards.map((card) => (
        <article key={card.label} className={`admin-page__stat admin-page__stat--${card.tone}`}>
          <div className="admin-page__stat-icon">
            <card.icon size={20} />
          </div>
          <span>{card.label}</span>
          <strong>{isLoading ? '-' : card.value}</strong>
          <p>{card.detail}</p>
        </article>
      ))}
    </section>
  );
}
