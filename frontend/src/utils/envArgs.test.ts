import { describe, expect, it } from 'vitest';
import { parseArgs, parseEnv, serializeArgs, serializeEnv } from './envArgs';

describe('parseEnv', () => {
  it('parses KEY=value lines', () => {
    const { value, error } = parseEnv('FOO=bar\nBAZ=qux');
    expect(error).toBeNull();
    expect(value).toEqual({ FOO: 'bar', BAZ: 'qux' });
  });

  it('ignores blank lines and comments', () => {
    const { value, error } = parseEnv('# a comment\n\nFOO=bar\n   \n# another');
    expect(error).toBeNull();
    expect(value).toEqual({ FOO: 'bar' });
  });

  it('keeps = inside the value', () => {
    expect(parseEnv('TOKEN=a=b=c').value).toEqual({ TOKEN: 'a=b=c' });
  });

  it('trims surrounding whitespace on key and value', () => {
    expect(parseEnv('  FOO = bar  ').value).toEqual({ FOO: 'bar' });
  });

  it('allows an empty value', () => {
    expect(parseEnv('DISABLE_AUTH=').value).toEqual({ DISABLE_AUTH: '' });
  });

  it('errors on a line with no =', () => {
    expect(parseEnv('FOO=bar\nNOPE').error).toBe('Line 2: expected KEY=value');
  });

  it('errors on an invalid variable name', () => {
    expect(parseEnv('1BAD=x').error).toBe('Line 1: invalid variable name "1BAD"');
  });

  it('errors on a duplicate key', () => {
    expect(parseEnv('FOO=a\nFOO=b').error).toBe('Line 2: duplicate variable "FOO"');
  });
});

describe('serializeEnv', () => {
  it('round-trips with parseEnv', () => {
    const text = 'FOO=bar\nBAZ=qux';
    expect(serializeEnv(parseEnv(text).value)).toBe(text);
  });

  it('handles null/undefined', () => {
    expect(serializeEnv(null)).toBe('');
    expect(serializeEnv(undefined)).toBe('');
  });
});

describe('parseArgs', () => {
  it('splits one argument per line, dropping blanks', () => {
    const { value, error } = parseArgs('start-notebook.py\n\n--ServerApp.token=\n  ');
    expect(error).toBeNull();
    expect(value).toEqual(['start-notebook.py', '--ServerApp.token=']);
  });
});

describe('serializeArgs', () => {
  it('round-trips with parseArgs', () => {
    expect(serializeArgs(parseArgs('a\nb\nc').value)).toBe('a\nb\nc');
  });

  it('handles null/undefined', () => {
    expect(serializeArgs(null)).toBe('');
    expect(serializeArgs(undefined)).toBe('');
  });
});
