import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { approvePacket, buildHandover, type HandoverPacket } from "../api/handover";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { loadSaved, toRequest } from "./YearPlan";

const input = "mt-1 w-full rounded border border-stone-400 px-2 py-1";

export function Handover() {
  const navigate = useNavigate();
  const [sent, setSent] = useState([{ reference: "", club_token: "" }]);
  const [packet, setPacket] = useState<HandoverPacket | null>(null);
  const [texts, setTexts] = useState<string[]>([]);
  const [approved, setApproved] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function build() {
    setError("");
    const { body, problems } = toRequest(loadSaved());
    if (!body) return setError(`Fix the year plan first: ${problems.join(" ")}`);
    if (body.events.length === 0) return setError("The year plan saved in this browser has no events yet. Fill in the year plan first.");
    setBusy(true);
    const result = await buildHandover(body, sent.filter((s) => s.reference.trim() && s.club_token.trim()));
    setBusy(false);
    if (!result.ok) return setError(result.error);
    setPacket(result.data);
    setTexts(result.data.packets.map((p) => p.text));
    setApproved({});
  }

  async function approve(i: number) {
    if (!packet) return;
    const result = await approvePacket(packet.packets[i]?.role ?? "", texts[i] ?? "");
    if (!result.ok) return setError(result.error);
    setApproved({ ...approved, [i]: result.data.message });
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Handover packet</h2>
        <p>
          At election time, Greenlight writes a packet for each officer role from your club's saved history: the year plan saved in this
          browser and the applications your club sent to the USG (Undergraduate Student Government) screen. Edit each packet and approve it
          before you pass it on. Greenlight sends nothing.
        </p>
      </header>

      <section aria-labelledby="sent-heading" className="space-y-2 rounded-md border border-stone-300 bg-white p-4">
        <h3 id="sent-heading" className="text-lg font-semibold">Applications your club sent (optional)</h3>
        {sent.map((s, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-2">
            <label className="block">Reference<input className={input} value={s.reference} onChange={(e) => setSent(sent.map((x, j) => (j === i ? { ...x, reference: e.target.value } : x)))} /></label>
            <label className="block">Token<input className={input} autoComplete="off" value={s.club_token} onChange={(e) => setSent(sent.map((x, j) => (j === i ? { ...x, club_token: e.target.value } : x)))} /></label>
          </div>
        ))}
        <button type="button" onClick={() => setSent([...sent, { reference: "", club_token: "" }])} className="rounded border border-stone-400 px-3 py-2 text-sm">Add another</button>
      </section>

      <button type="button" onClick={build} disabled={busy} className="rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
        {busy ? "Writing…" : "Write the handover packets"}
      </button>
      {error ? <p role="alert" className="rounded border border-red-700 bg-red-50 px-3 py-2 text-red-900">{error}</p> : null}

      {packet ? (
        <section aria-labelledby="packets-heading" className="space-y-4">
          <h3 id="packets-heading" className="text-xl font-semibold">Packets for {packet.club_name || "your club"}</h3>
          <PrecheckNotice text={packet.notice} />
          {packet.notes.map((n) => <p key={n} className="text-sm text-amber-950">! {n}</p>)}
          {packet.packets.map((p, i) => (
            <div key={p.role} className="rounded-md border border-stone-300 bg-white p-4">
              <label className="block font-semibold">{p.role} (edit it before approving)
                <textarea rows={14} className={`${input} font-mono text-sm font-normal`} value={texts[i] ?? ""}
                  onChange={(e) => { setTexts(texts.map((t, j) => (j === i ? e.target.value : t))); setApproved({ ...approved, [i]: "" }); }} />
              </label>
              <button type="button" onClick={() => approve(i)} disabled={!(texts[i] ?? "").trim()} className="mt-2 rounded border border-cardinal px-4 py-2 font-medium text-cardinal disabled:opacity-50">
                I have read and approve this packet
              </button>
              {approved[i] ? <p role="status" className="mt-2 font-medium">{approved[i]}</p> : null}
            </div>
          ))}
          <button type="button" onClick={() => navigate("/", { state: { seedPlan: packet.next_year_plan } })} className="rounded border border-stone-400 px-4 py-2">
            Start next year's plan from this one
          </button>
          <p className="text-sm text-stone-600">This replaces the plan saved in this browser with next year's starting plan: the same events, one year later on the same weekday, with the money left blank.</p>
        </section>
      ) : null}
    </div>
  );
}
