export default function SettingsPage() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <section className="terminal-card space-y-3 p-4"><h2>Data Sources</h2><input placeholder="Alpha Vantage API key" className="w-full bg-[var(--bg-tertiary)] p-2" /><select className="w-full bg-[var(--bg-tertiary)] p-2"><option>60s refresh</option><option>30s refresh</option><option>5min refresh</option></select></section>
      <section className="terminal-card space-y-3 p-4"><h2>Alerts</h2><input placeholder="NOW crosses price" className="w-full bg-[var(--bg-tertiary)] p-2" /><input placeholder="RSI below 30 or above 70" className="w-full bg-[var(--bg-tertiary)] p-2" /></section>
      <section className="terminal-card space-y-3 p-4"><h2>Display</h2><select className="w-full bg-[var(--bg-tertiary)] p-2"><option>1Y default range</option><option>6M default range</option></select><label className="block"><input type="checkbox" defaultChecked /> Show SMA overlays</label><label className="block"><input type="checkbox" defaultChecked /> Show Bollinger Bands</label></section>
    </div>
  );
}
