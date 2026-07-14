import type { Sentiment } from "../types";

const LABELS: Record<Sentiment, { symbol: string; text: string }> = {
  positive: { symbol: "▲", text: "Positive" },
  neutral: { symbol: "■", text: "Neutral" },
  negative: { symbol: "▼", text: "Negative" },
};

interface Props {
  sentiment: Sentiment;
  score?: number;
}

export function SentimentBadge({ sentiment, score }: Props) {
  const { symbol, text } = LABELS[sentiment];
  return (
    <span className={`badge badge--${sentiment}`}>
      <span aria-hidden>{symbol}</span> {text}
      {typeof score === "number" && <span className="badge__score">{score.toFixed(2)}</span>}
    </span>
  );
}
