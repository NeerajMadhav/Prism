/** PRISM FinOps — structured client logger (no secrets/PII in payloads). */

type LogFields = Record<string, string | number | boolean | null | undefined>;

const SERVICE = 'prism-frontend';

function emit(
  level: 'debug' | 'info' | 'warn' | 'error',
  event: string,
  fields: LogFields = {},
): void {
  if (typeof window === 'undefined') {
    return;
  }
  const payload = {
    ts: new Date().toISOString(),
    service: SERVICE,
    level,
    event,
    ...fields,
  };
  const line = JSON.stringify(payload);
  switch (level) {
    case 'error':
      console.error(line);
      break;
    case 'warn':
      console.warn(line);
      break;
    case 'debug':
      if (process.env.NODE_ENV !== 'production') {
        console.debug(line);
      }
      break;
    default:
      if (process.env.NODE_ENV !== 'production') {
        console.info(line);
      }
      break;
  }
}

/** Application client logger — keys only, never tokens or passwords. */
export const clientLogger = {
  debug: (event: string, fields?: LogFields) => emit('debug', event, fields),
  info: (event: string, fields?: LogFields) => emit('info', event, fields),
  warn: (event: string, fields?: LogFields) => emit('warn', event, fields),
  error: (event: string, fields?: LogFields) => emit('error', event, fields),
};

/** Creates a short request id for correlating browser → API logs. */
export function createClientRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `fe-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
