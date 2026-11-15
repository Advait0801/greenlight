export function PrecheckNotice({ text }: { text?: string }) {
  return (
    <p className="flex items-start gap-2 text-sm text-stone-600" role="note">
      <span aria-hidden="true" className="mt-0.5 grid h-4 w-4 flex-none place-items-center rounded-full border border-stone-500 text-[0.625rem] font-semibold">i</span>
      <span>{text ?? "Greenlight is a pre-check, not a decision. The office that owns each rule makes the decision."}</span>
    </p>
  );
}
