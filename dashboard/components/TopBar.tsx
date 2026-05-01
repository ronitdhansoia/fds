import Link from "next/link";

export function TopBar({ active }: { active?: "home" | "methodology" | "explorer" }) {
  return (
    <div className="sticky top-0 z-30 border-b border-border bg-bg">
      <div className="mx-auto flex h-12 max-w-[1280px] items-center justify-between px-6">
        <Link
          href="/"
          className="font-mono text-overline tracking-[0.2em] text-text-3 transition-colors hover:text-text"
        >
          MIGRANTMONEY
        </Link>
        <nav className="flex items-center gap-7 font-mono text-overline tracking-[0.18em] uppercase">
          <Link
            href="/"
            className={`transition-colors hover:text-text ${active === "home" ? "text-text" : "text-text-3"}`}
          >
            Index
          </Link>
          <Link
            href="/corridor/USA-MEX"
            className={`transition-colors hover:text-text ${active === "explorer" ? "text-text" : "text-text-3"}`}
          >
            Corridor
          </Link>
          <Link
            href="/methodology"
            className={`transition-colors hover:text-text ${active === "methodology" ? "text-text" : "text-text-3"}`}
          >
            Methodology
          </Link>
        </nav>
      </div>
    </div>
  );
}
