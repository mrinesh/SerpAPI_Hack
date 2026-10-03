import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="text-center">
      <h1 className="text-xl font-semibold">Page not found</h1>
      <Link to="/" className="mt-4 inline-block text-sm text-slate-600 underline">
        Start a new search
      </Link>
    </div>
  );
}
