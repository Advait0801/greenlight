// A small set of line icons (24px grid, 1.75 stroke), drawn inline so no icon package is needed. Decorative only.

const PATHS: Record<string, string> = {
  home: "M3 10.5 12 3l9 7.5M5 9v11h5v-6h4v6h5V9",
  document: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  calendar: "M4 6h16v15H4zM4 10h16M8 3v4M16 3v4",
  handover: "M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3M18 3v4h-4M6 21v-4h4",
  event: "M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z",
  money: "M12 3v18M16.5 7.5C16 6 14.3 5 12 5c-2.6 0-4.5 1.3-4.5 3.2 0 4.3 9 2.3 9 6.8 0 1.9-2 3.3-4.5 3.3-2.4 0-4.2-1.1-4.7-2.8",
  gap: "M4 8h13l-3-3M20 16H7l3 3",
  flag: "M5 21V4M5 4h11l-2 4 2 4H5",
  accuracy: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01",
  status: "M3 12h4l3-7 4 14 3-7h4",
  menu: "M4 6h16M4 12h16M4 18h16",
};

export function Icon({ name, className = "h-5 w-5" }: { name: string; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d={PATHS[name] ?? ""} />
    </svg>
  );
}
