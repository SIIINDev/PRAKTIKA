import { Fragment, type ReactNode } from "react";

interface HighlightProps {
  /** Server-provided string that may contain ONLY <em>...</em> tags. */
  html: string;
}

/**
 * Safely renders an ES highlight fragment.
 *
 * The server sends text wrapped in <em>...</em>. We must NOT trust it as raw
 * HTML. Strategy: tokenize the string, treating only the literal substrings
 * "<em>" and "</em>" as markup; everything else is rendered as plain React
 * text nodes (so React escapes it). Matched segments become <mark> with a
 * yellow background. No dangerouslySetInnerHTML, so injected tags/scripts in
 * the payload are rendered as inert text.
 */
export function Highlight({ html }: HighlightProps) {
  const nodes: ReactNode[] = [];
  let buffer = "";
  let inMark = false;
  let i = 0;
  let key = 0;

  const flush = () => {
    if (buffer.length === 0) return;
    if (inMark) {
      nodes.push(<mark key={key++}>{buffer}</mark>);
    } else {
      nodes.push(<Fragment key={key++}>{buffer}</Fragment>);
    }
    buffer = "";
  };

  while (i < html.length) {
    if (html.startsWith("<em>", i)) {
      flush();
      inMark = true;
      i += 4;
    } else if (html.startsWith("</em>", i)) {
      flush();
      inMark = false;
      i += 5;
    } else {
      buffer += html[i];
      i += 1;
    }
  }
  flush();

  return <>{nodes}</>;
}
