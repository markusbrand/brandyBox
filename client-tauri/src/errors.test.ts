import { describe, it, expect } from 'vitest';
import { formatUserFacingError } from './errors';

describe('formatUserFacingError', () => {
  it('handles Error instances', () => {
    const err = new Error('Test error message');
    expect(formatUserFacingError(err)).toBe('Test error message');
  });

  it('handles string inputs', () => {
    expect(formatUserFacingError('Just a string error')).toBe('Just a string error');
  });

  it('handles empty inputs', () => {
    expect(formatUserFacingError('')).toBe('Something went wrong. Try again.');
    expect(formatUserFacingError('   ')).toBe('Something went wrong. Try again.');
    expect(formatUserFacingError(new Error(''))).toBe('Something went wrong. Try again.');
  });

  it('handles inputs with a colon separator and a long tail', () => {
    // Tail length >= 3
    expect(formatUserFacingError('invalid args `api_create_user`: Email already registered')).toBe('Email already registered');
    expect(formatUserFacingError('Some prefix: a long enough message')).toBe('a long enough message');
    expect(formatUserFacingError(new Error('api_error: User not found'))).toBe('User not found');
  });

  it('handles inputs with a colon separator but a short tail', () => {
    // Tail length < 3
    expect(formatUserFacingError('Some prefix: ok')).toBe('Some prefix: ok');
    expect(formatUserFacingError('Prefix: no')).toBe('Prefix: no');
  });

  it('handles inputs with a colon near the end', () => {
    // The implementation returns raw.trim() as a fallback
    expect(formatUserFacingError('Ends with colon: ')).toBe('Ends with colon:');
    expect(formatUserFacingError('Another colon :')).toBe('Another colon :');
  });

  it('handles inputs without a colon separator', () => {
    expect(formatUserFacingError('No colon in this message')).toBe('No colon in this message');
  });

  it('handles undefined or null inputs', () => {
    // String(undefined) is "undefined", String(null) is "null"
    expect(formatUserFacingError(undefined)).toBe('undefined');
    expect(formatUserFacingError(null)).toBe('null');
  });

  it('handles objects', () => {
    // String({ message: "error" }) is "[object Object]"
    expect(formatUserFacingError({ message: 'error' })).toBe('[object Object]');
  });
});
