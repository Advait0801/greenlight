export function PrecheckNotice({ text }: { text?: string }) {
  return (
    <p className="rounded-md border border-stone-300 bg-white px-4 py-3 text-sm text-stone-700" role="note">
      {text ?? "Greenlight is a pre-check, not a decision. The office that owns each rule makes the decision."}
    </p>
  );
}
