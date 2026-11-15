import type { Citation } from "../api/types";

// A quote whose source lists items inline ("intro: * a * b") is shown as a list; the words are unchanged.
function Quote({ text }: { text: string }) {
  const parts = text.split(/\s+\*\s+/).map((t) => t.trim()).filter(Boolean);
  if (parts.length < 3) return <blockquote className="text-stone-800">“{text}”</blockquote>;
  const [intro, ...items] = parts;
  return (
    <blockquote className="text-stone-800">
      <p>“{intro}</p>
      <ul className="mt-1 list-disc columns-1 pl-5 sm:columns-2">
        {items.map((item, i) => <li key={i}>{item}{i === items.length - 1 ? "”" : ""}</li>)}
      </ul>
    </blockquote>
  );
}

// Every finding and deadline shows the rule text and a link to its source.
export function SourceLink({ citation }: { citation: Citation }) {
  return (
    <figure className="mt-2 border-l-2 border-gold py-1 pl-4 text-sm">
      <Quote text={citation.source_text} />
      <figcaption className="mt-1 text-stone-600">
        <a className="inline-flex items-center gap-1 rounded bg-white px-1.5 py-0.5 font-semibold text-cardinal underline decoration-gold decoration-2 underline-offset-2 ring-1 ring-cardinal/20 hover:bg-gold-soft" href={citation.source_url} target="_blank" rel="noreferrer">
          {citation.source}
          <span aria-hidden="true">↗</span>
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
        {citation.source_section ? `, ${citation.source_section}` : ""} · version of {citation.effective_date}
        {citation.verified !== "read" ? " · not yet verified" : ""}
      </figcaption>
    </figure>
  );
}
