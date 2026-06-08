import { AxiosError } from 'axios';
import { parseApiError } from './api';

describe('parseApiError', () => {
  it('parses the backend error envelope', () => {
    const error = {
      response: {
        status: 400,
        data: { error: { code: 'validation_error', message: 'Invalid file', details: {}, request_id: 'req-1' } },
        headers: {},
      },
    } as AxiosError;
    expect(parseApiError(error)).toMatchObject({ status: 400, code: 'validation_error', message: 'Invalid file', requestId: 'req-1' });
  });
});
