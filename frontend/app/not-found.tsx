import Link from "next/link";
import { EmptyState } from "@/components/empty-state";
export default function NotFound() {
  return (
    <>
      <EmptyState
        title="Workspace not found"
        description="This link does not match an available SOC workspace."
      />
      <div className="text-center">
        <Link className="button" href="/">
          Return to Overview
        </Link>
      </div>
    </>
  );
}
