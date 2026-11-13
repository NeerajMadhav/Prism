/** PRISM FinOps — WebSocket auth token encoding (no query-string JWT). */

/** Encodes an access JWT for the Sec-WebSocket-Protocol header. */
export function encodeWsAuthProtocol(accessToken: string): string {
  const b64 = btoa(accessToken)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `prism.jwt.${b64}`;
}
