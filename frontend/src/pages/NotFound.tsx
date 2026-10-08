import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="mx-auto max-w-xl text-center">
      <h1 className="text-xl">This page does not exist</h1>
      <p className="mt-2">
        <Link to="/" className="font-medium text-studentFit underline">
          Go to the start
        </Link>
      </p>
    </div>
  );
}
