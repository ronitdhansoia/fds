import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Section({
  overline,
  title,
  children,
  className,
}: {
  overline?: string;
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "mx-auto grid max-w-[1280px] grid-cols-12 gap-6 px-6",
        className,
      )}
    >
      <header className="col-span-12 md:col-span-3 lg:col-span-3">
        {overline ? <div className="overline mb-3">{overline}</div> : null}
        {title ? (
          <h2 className="font-display text-subhead text-text balance leading-[1.15] md:sticky md:top-20">
            {title}
          </h2>
        ) : null}
      </header>
      <div className="col-span-12 md:col-span-9 lg:col-span-9">{children}</div>
    </section>
  );
}
