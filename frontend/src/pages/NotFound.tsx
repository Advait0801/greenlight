import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p>
        <Link className="text-cardinal underline underline-offset-2" to="/">
          Back to the start page
        </Link>
      </p>
    </div>
  );
}
