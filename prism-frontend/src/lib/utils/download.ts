/** PRISM FinOps — browser download helpers. */

/** Triggers a CSV or blob file download in the browser. */
export function triggerCsvDownload(data: string | Blob, filename: string): void {
  const blob = typeof data === 'string' ? new Blob([data], { type: 'text/csv' }) : data;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
