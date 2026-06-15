/**
 * Helpers for editing a workshop template's `env` and `args` as plain text.
 *
 * `env` is edited as dotenv-style `KEY=value` lines (one per line); `args` as
 * one argument per line. Both are far easier to author and validate in a single
 * textbox than a row-per-entry UI, and need no YAML parser.
 */

export interface ParseResult<T> {
  value: T;
  /** First validation error (1-based line number), or null if the text is valid. */
  error: string | null;
}

// POSIX-ish environment variable name: letter/underscore, then alphanumerics/underscore.
const ENV_KEY_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

/**
 * Parse dotenv-style `KEY=value` lines into a record. Blank lines and lines
 * starting with `#` are ignored. The value is everything after the first `=`
 * (so values may themselves contain `=`).
 */
export function parseEnv(text: string): ParseResult<Record<string, string>> {
  const env: Record<string, string> = {};
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line === '' || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) {
      return { value: {}, error: `Line ${i + 1}: expected KEY=value` };
    }
    const key = line.slice(0, eq).trim();
    const val = line.slice(eq + 1).trim();
    if (!ENV_KEY_RE.test(key)) {
      return { value: {}, error: `Line ${i + 1}: invalid variable name "${key}"` };
    }
    if (key in env) {
      return { value: {}, error: `Line ${i + 1}: duplicate variable "${key}"` };
    }
    env[key] = val;
  }
  return { value: env, error: null };
}

/** Serialize a record into dotenv-style lines (insertion order). */
export function serializeEnv(env: Record<string, string> | null | undefined): string {
  if (!env) return '';
  return Object.entries(env)
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
}

/** Parse one-argument-per-line text into a string array. Blank lines are dropped. */
export function parseArgs(text: string): ParseResult<string[]> {
  const args = text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l !== '');
  return { value: args, error: null };
}

/** Serialize an args array into one-per-line text. */
export function serializeArgs(args: string[] | null | undefined): string {
  if (!args) return '';
  return args.join('\n');
}
