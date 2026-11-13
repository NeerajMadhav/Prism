import { describe, expect, it } from 'vitest';
import axios from 'axios';

import { extractErrorMessage } from '@/lib/utils/errors';

describe('extractErrorMessage', () => {
  it('reads live AppError `{ error, code }` shape', () => {
    const err = new axios.AxiosError('Request failed');
    err.response = {
      status: 403,
      data: { error: 'Check your email to verify your account.', code: 'forbidden' },
      statusText: 'Forbidden',
      headers: {},
      config: {} as never,
    };
    expect(extractErrorMessage(err)).toBe('Check your email to verify your account.');
  });

  it('reads FastAPI `{ detail: string }` shape', () => {
    const err = new axios.AxiosError('Request failed');
    err.response = {
      status: 400,
      data: { detail: 'Invalid input' },
      statusText: 'Bad Request',
      headers: {},
      config: {} as never,
    };
    expect(extractErrorMessage(err)).toBe('Invalid input');
  });
});
