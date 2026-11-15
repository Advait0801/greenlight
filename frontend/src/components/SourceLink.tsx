import type { Citation } from "../api/types";

// Every finding and deadline shows the rule text and a link to its source.
export function SourceLink({ citation }: { citation: Citation }) {
  return (
    <figure className="mt-2 border-l-2 border-gold py-1 pl-4 text-sm">
      <blockquote className="text-stone-800">“{citation.source_text}”</blockquote>
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
