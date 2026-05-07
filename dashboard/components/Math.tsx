import katex from "katex";
import "katex/dist/katex.min.css";

interface MathProps {
  expr: string;
  display?: boolean;
}

export function Math({ expr, display = false }: MathProps) {
  const html = katex.renderToString(expr, {
    displayMode: display,
    throwOnError: true,
    strict: "ignore",
    output: "html",
  });
  return (
    <span
      className={display ? "block my-0" : "inline"}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function MathBlock({ expr, caption }: { expr: string; caption?: string }) {
  return (
    <figure className="my-7 rounded-[2px] border border-border bg-surface px-6 py-5">
      <Math expr={expr} display />
      {caption ? (
        <figcaption className="mt-3 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
