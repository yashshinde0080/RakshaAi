/**
 * Central strings module (PRD §8: localization-ready).
 *
 * `t(key, params)` renders catalog strings with `{param}` interpolation, and
 * the params are **type-checked per key**: `ParamsOf` derives the required
 * placeholder names straight from the string template, so calling `t('x')`
 * without a required param — or passing a param the template doesn't declare —
 * fails `tsc --noEmit`. Translation files that rename or drop a placeholder
 * break every call site that uses it.
 *
 * Keys are dotted paths into the catalog (e.g. `'reason.spo2Critical'`), and
 * `StringKey` is derived recursively from `en` — a typo in any `t()` call or
 * translation file fails typecheck.
 *
 * Adding a locale later:
 *   1. Create `src/i18n/fr.ts` typed as `StringCatalog` (compile-time key
 *      parity — a missing or extra key fails typecheck). Placeholders must
 *      keep the same names as `en`.
 *   2. Make `t` resolve the active catalog (e.g. from a locale module).
 *   3. No component changes needed — they only call `t()`.
 *
 * Notes:
 *   - Rendered strings (e.g. `triggeredReasons`) are computed in the active
 *     locale at call time; history records store the rendered strings. If
 *     locale switching is added, migrate the record schema to store reason
 *     keys instead so old history can re-render in the new locale.
 */

import { en } from './en';
import type { StringCatalog } from './en';

export { en };
export type { StringCatalog };

/** Recursively builds dotted paths to every leaf string in the catalog. */
type FlattenKeys<T> = T extends string
  ? ''
  : {
      [K in keyof T]-?: K extends string
        ? `${K}${FlattenKeys<T[K]> extends '' ? '' : `.${FlattenKeys<T[K]>}`}`
        : never;
    }[keyof T];

export type StringKey = FlattenKeys<StringCatalog>;

/** The string value at a dotted path into the catalog. */
type PathValue<T, P extends string> = P extends `${infer Head}.${infer Tail}`
  ? PathValue<T[Head & keyof T], Tail>
  : T[P & keyof T];

/** Placeholder names required by a template, e.g. 'x {a} y {b}' → { a, b }. */
type ParamsOf<S extends string> = S extends `${string}{${infer Param}}${infer Rest}`
  ? { [K in Param | keyof ParamsOf<Rest>]: string | number }
  : {};

export type StringParams = Record<string, string | number>;

/** The param-less signature case: a template with no placeholders. */
type NoParams = Record<string, never>;

/** Resolve a dotted key to the leaf string, mirroring FlattenKeys' shape. */
function resolve(catalog: unknown, path: string): string {
  let current = catalog as Record<string, unknown>;
  for (const part of path.split('.')) {
    current = current[part] as Record<string, unknown>;
  }
  return current as unknown as string;
}

export function t<K extends StringKey>(
  key: K,
  ...args: ParamsOf<PathValue<StringCatalog, K>> extends NoParams
    ? []
    : [params: ParamsOf<PathValue<StringCatalog, K>>]
): string {
  const params = args[0];
  let out = resolve(en, key);
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      out = out.split(`{${name}}`).join(String(value));
    }
  }
  return out;
}
