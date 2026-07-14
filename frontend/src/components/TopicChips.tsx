import type { Category } from "../types";

interface Props {
  categories: Category[];
  active: string | null;
  onSelect: (key: string) => void;
}

export function TopicChips({ categories, active, onSelect }: Props) {
  return (
    <div className="chips" role="tablist" aria-label="Topics">
      {categories.map((category) => (
        <button
          key={category.key}
          className={`chip ${active === category.key ? "chip--active" : ""}`}
          role="tab"
          aria-selected={active === category.key}
          onClick={() => onSelect(category.key)}
        >
          {category.label}
        </button>
      ))}
    </div>
  );
}
