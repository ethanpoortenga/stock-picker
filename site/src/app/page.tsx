import picksData from "../data/picks.json";
import backtestData from "../data/backtest.json";

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
}

interface BacktestStats {
  start_date: string;
  end_date: string;
  total_picks: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_daily_return: number;
  total_return: number;
  sharpe_ratio: number;
  best_pick: Record<string, unknown> | null;
  worst_pick: Record<string, unknown> | null;
}

export default function Home() {
  const picks = (picksData as Pick[]).slice().reverse();
  const stats = backtestData as unknown as BacktestStats;
  const todayPick = picks[0];

  const livePicks = picks.filter((p) => p.result !== null);
  const liveWins = livePicks.filter((p) => p.result === "win").length;
  const liveWinRate = livePicks.length > 0 ? ((liveWins / livePicks.length) * 100).toFixed(1) : "—";

  return (
    <div className="min-h-screen font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="border-b border-[var(--color-card-border)] px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--color-accent)] font-[family-name:var(--font-mono)] text-sm font-bold text-black">
              SP
            </div>
            <span className="text-lg font-semibold">Daily Stock Pick</span>
          </div>
          <span className="text-sm text-zinc-500">Momentum + Mean Reversion Strategy</span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        {/* Today's Pick - Hero */}
        {todayPick && (
          <section className="mb-12">
            <p className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-500">
              Latest Pick — {todayPick.date}
            </p>
            <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-card)] p-8">
              <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h1 className="font-[family-name:var(--font-mono)] text-6xl font-bold text-[var(--color-accent)]">
                    {todayPick.ticker}
                  </h1>
                  <p className="mt-2 text-2xl text-zinc-300">${todayPick.price_at_pick.toFixed(2)}</p>
                </div>
                <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                  <Stat label="Target" value={`$${todayPick.target_price.toFixed(2)}`} />
                  <Stat label="Score" value={todayPick.score.toString()} />
                  <Stat label="RSI" value={todayPick.rsi.toString()} />
                  <Stat label="5d Return" value={`${todayPick.five_day_return.toFixed(1)}%`} />
                </div>
              </div>
              {todayPick.result && (
                <div
                  className={`mt-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ${
                    todayPick.result === "win"
                      ? "bg-green-500/15 text-green-400"
                      : "bg-red-500/15 text-red-400"
                  }`}
                >
                  {todayPick.result === "win" ? "+" : ""}
                  {todayPick.actual_return?.toFixed(2)}% — {todayPick.result === "win" ? "Target Hit" : "Missed"}
                </div>
              )}
              {!todayPick.result && (
                <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-yellow-500/15 px-4 py-2 text-sm font-semibold text-yellow-400">
                  Awaiting result...
                </div>
              )}
            </div>
          </section>
        )}

        {/* Stats Row */}
        <section className="mb-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Backtest Win Rate" value={`${stats.win_rate}%`} detail={`${stats.wins}/${stats.total_picks} picks`} />
          <StatCard label="Avg Daily Return" value={`${stats.avg_daily_return}%`} detail={`Sharpe: ${stats.sharpe_ratio}`} />
          <StatCard label="Live Win Rate" value={`${liveWinRate}%`} detail={`${liveWins}/${livePicks.length} picks`} />
          <StatCard label="Backtest Period" value={`${stats.total_picks}d`} detail={`${stats.start_date} to ${stats.end_date}`} />
        </section>

        {/* How It Works */}
        <section className="mb-12">
          <h2 className="mb-4 text-xl font-semibold">How It Works</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <InfoCard
              step="1"
              title="Score"
              text="Every S&P 500 stock is scored daily using RSI, momentum, volume, and trend signals."
            />
            <InfoCard
              step="2"
              title="Pick"
              text="The highest-scoring stock is selected as the daily pick, targeting a 1% next-day gain."
            />
            <InfoCard
              step="3"
              title="Track"
              text="Results are updated automatically. We track every pick against the 1% target."
            />
          </div>
        </section>

        {/* Pick History */}
        <section>
          <h2 className="mb-4 text-xl font-semibold">Pick History</h2>
          <div className="overflow-hidden rounded-xl border border-[var(--color-card-border)]">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--color-card-border)] bg-[var(--color-card)] text-xs uppercase tracking-wider text-zinc-500">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Ticker</th>
                  <th className="px-4 py-3 text-right">Entry</th>
                  <th className="px-4 py-3 text-right">Target</th>
                  <th className="px-4 py-3 text-right">Result</th>
                  <th className="px-4 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {picks.map((pick) => (
                  <tr key={pick.date} className="border-b border-[var(--color-card-border)] last:border-0">
                    <td className="px-4 py-3 font-[family-name:var(--font-mono)] text-zinc-400">{pick.date}</td>
                    <td className="px-4 py-3 font-semibold">{pick.ticker}</td>
                    <td className="px-4 py-3 text-right font-[family-name:var(--font-mono)]">
                      ${pick.price_at_pick.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-[family-name:var(--font-mono)]">
                      ${pick.target_price.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-[family-name:var(--font-mono)]">
                      {pick.actual_return !== null ? (
                        <span className={pick.actual_return >= 1 ? "text-green-400" : "text-red-400"}>
                          {pick.actual_return >= 0 ? "+" : ""}
                          {pick.actual_return.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-zinc-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {pick.result === "win" && (
                        <span className="inline-block rounded-full bg-green-500/15 px-2.5 py-0.5 text-xs font-medium text-green-400">
                          Win
                        </span>
                      )}
                      {pick.result === "loss" && (
                        <span className="inline-block rounded-full bg-red-500/15 px-2.5 py-0.5 text-xs font-medium text-red-400">
                          Miss
                        </span>
                      )}
                      {pick.result === null && (
                        <span className="inline-block rounded-full bg-zinc-500/15 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
                          Pending
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Disclaimer */}
        <footer className="mt-16 border-t border-[var(--color-card-border)] pt-8 text-center text-xs text-zinc-600">
          <p>
            This is an experimental stock picking project for educational purposes only.
            Not financial advice. Past performance does not guarantee future results.
          </p>
        </footer>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-1 font-[family-name:var(--font-mono)] text-lg font-semibold">{value}</p>
    </div>
  );
}

function StatCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-card-border)] bg-[var(--color-card)] p-5">
      <p className="text-xs uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-2 font-[family-name:var(--font-mono)] text-2xl font-bold">{value}</p>
      <p className="mt-1 text-xs text-zinc-500">{detail}</p>
    </div>
  );
}

function InfoCard({ step, title, text }: { step: string; title: string; text: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-card-border)] bg-[var(--color-card)] p-5">
      <div className="mb-3 flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-accent)] text-xs font-bold text-black">
        {step}
      </div>
      <h3 className="mb-1 font-semibold">{title}</h3>
      <p className="text-sm text-zinc-400">{text}</p>
    </div>
  );
}
