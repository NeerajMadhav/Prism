/** PRISM FinOps — password rules matching FastAPI `_validate_password`. */

import { z } from 'zod';

/** Zod schema aligned with backend password strength requirements. */
export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain an uppercase letter')
  .regex(/\d/, 'Password must contain a number')
  .regex(/[^A-Za-z0-9]/, 'Password must contain a special character');
