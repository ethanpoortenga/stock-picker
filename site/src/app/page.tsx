import picksData from "../data/picks.json";

interface Pick {
  date: string;
  ticker: string;
  price_at_pick: number;
  score: number;
  rsi: number;
  five_day_return: number;
  target_price: number;
  result: "win" | "loss" | null;
  actual_return: number | null;
  next_day_close?: number;
  reasoning?: string;
}

export default function Home() {
  const picks = (picksData as Pick[]).slice().reverse();
  const todayPick = picks[0];

  const resolved = picks.filter((p) => p.result !== null);
  const wins = resolved.filter((p) => p.result === "win").length;

  return (
    <div className="mx-auto min-h-screen max-w-2xl px-6 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="pb-16 pt-20 text-center">
        <h1 className="text-sm font-medium uppercase tracking-[0.3em] text-[var(--color-muted)]">
          The Oracle
        </h1>
      </header>

      {/* Today's Pick */}
      {todayPick && (
        <section className="mb-20 text-center">
          <p className="mb-8 font-[family-name:var(--font-mono)] text-xs text-[var(--color-muted)]">
            {todayPick.date}
          </p>
          <h2 className="font-[family-name:var(--font-mono)] text-7xl font-bold tracking-tight sm:text-8xl">
            {todayPick.ticker}
          </h2>
          <p className="mt-4 font-[family-name:var(--font-mono)] text-xl text-[var(--color-muted)]">
            ${todayPick.price_at_pick.toFixed(2)}
          </p>
          {todayPick.reasoning && (
            <p className="mx-auto mt-6 max-w-md text-sm leading-relaxed text-[var(--color-muted)]">
              {todayPick.reasoning}
            </p>
          )}
          <div className="mt-8">
            {todayPick.result === "win" && (
              <span className="font-[family-name:var(--font-mono)] text-sm text-[var(--color-win)]">
                +{todayPick.actual_return?.toFixed(2)}%
              </span>
            )}
            {todayPick.result === "loss" && (
              <span className="font-[family-name:var(--font-mono)] text-sm text-[var(--color-loss)]">
                {todayPick.actual_return?.toFixed(2)}%
              </span>
            )}
            {todayPick.result === null && (
              <span className="font-[family-name:var(--font-mono)] text-xs tracking-widest text-[var(--color-muted)]">
                ...
              </span>
            )}
          </div>
        </section>
      )}

      {/* Record */}
      {resolved.length > 0 && (
        <p className="mb-8 text-center font-[family-name:var(--font-mono)] text-xs text-[var(--color-muted)]">
          {wins}–{resolved.length - wins}
        </p>
      )}

      {/* History */}
      <section className="pb-20">
        <div className="space-y-px">
          {picks.slice(1).map((pick) => (
            <div
              key={pick.date}
              className="flex items-center justify-between border-b border-[var(--color-border)] py-3"
            >
              <div className="flex items-center gap-4">
                <span className="w-20 font-[family-name:var(--font-mono)] text-xs text-[var(--color-muted)]">
                  {pick.date.slice(5)}
                </span>
                <span className="font-[family-name:var(--font-mono)] text-sm font-medium">
                  {pick.ticker}
                </span>
              </div>
              <div className="font-[family-name:var(--font-mono)] text-sm">
                {pick.result === "win" && (
                  <span className="text-[var(--color-win)]">+{pick.actual_return?.toFixed(2)}%</span>
                )}
                {pick.result === "loss" && (
                  <span className="text-[var(--color-loss)]">{pick.actual_return?.toFixed(2)}%</span>
                )}
                {pick.result === null && (
                  <span className="text-[var(--color-muted)]">—</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] py-8 text-center font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">
        not financial advice
      </footer>
    </div>
  );
}
