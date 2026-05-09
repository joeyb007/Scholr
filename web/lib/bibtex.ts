import type { Paper } from "@/types/scholr";

function sanitize(str: string): string {
  return str.replace(/[{}"\\]/g, "").trim();
}

export function generateBibtex(papers: Paper[]): string {
  return papers
    .map(p => {
      const key = p.id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 20);
      const url = p.id.startsWith("arXiv:")
        ? `https://arxiv.org/abs/${p.id.slice(6)}`
        : `https://openalex.org/works/${p.id}`;
      return [
        `@article{${key},`,
        `  title = {${sanitize(p.title)}},`,
        `  author = {${sanitize(p.authors)}},`,
        p.year ? `  year = {${p.year}},` : null,
        p.venue ? `  journal = {${sanitize(p.venue)}},` : null,
        `  url = {${url}}`,
        `}`,
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n");
}

export function downloadBibtex(papers: Paper[], filename = "scholr-references.bib") {
  const content = generateBibtex(papers);
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
