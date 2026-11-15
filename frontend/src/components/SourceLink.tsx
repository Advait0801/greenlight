import type { Citation } from "../api/types";

// Every finding and deadline shows the rule text and a link to its source.
export function SourceLink({ citation }: { citation: Citation }) {
  return (
    <figure className="mt-2 border-l-2 border-gold py-1 pl-4 text-sm">
      <blockquote className="text-stone-800">“{citation.source_text}”</blockquote>
      <figcaption className="mt-1 text-stone-600">
        <a className="font-medium text-cardinal underline underline-offset-2" href={citation.source_url} target="_blank" rel="noreferrer">
          {citation.source}
        </a>
        {citation.source_section ? `, ${citation.source_section}` : ""} · version of {citation.effective_date}
        {citation.verified !== "read" ? " · not yet verified" : ""}
      </figcaption>
    </figure>
  );
}
