interface Props {
  icon: string;
  text: string;
}

export function EmptyState({ icon, text }: Props) {
  return (
    <div className="empty">
      <span className="empty__icon" aria-hidden>
        {icon}
      </span>
      <p>{text}</p>
    </div>
  );
}
