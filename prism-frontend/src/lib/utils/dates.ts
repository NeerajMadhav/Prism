/** PRISM FinOps — timezone-aware date formatting. */

import { formatDistanceToNow } from 'date-fns';
import { formatInTimeZone, fromZonedTime, toZonedTime } from 'date-fns-tz';

/** Formats an ISO timestamp in the organization's timezone. */
export function formatDate(
  isoString: string,
  tz: string,
  fmt = 'MMM d, yyyy',
): string {
  return formatInTimeZone(isoString, tz, fmt);
}

/** Returns a human-readable relative time string. */
export function formatRelative(isoString: string): string {
  return formatDistanceToNow(new Date(isoString), { addSuffix: true });
}

/** Converts a date into the organization's timezone. */
export function toOrgTz(date: Date, tz: string): Date {
  return toZonedTime(date, tz);
}

/** Returns the current time in the organization's timezone. */
export function getOrgNow(tz: string): Date {
  return toZonedTime(new Date(), tz);
}

/** Formats a date as an API date parameter (YYYY-MM-DD). */
export function formatDateForApi(date: Date): string {
  return formatInTimeZone(date, 'UTC', 'yyyy-MM-dd');
}

/** Formats a datetime as an ISO string for API datetime fields. */
export function formatDateTimeForApi(date: Date): string {
  return fromZonedTime(date, 'UTC').toISOString();
}
