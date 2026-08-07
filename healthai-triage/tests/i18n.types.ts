/**
 * Type-level contract for `t()` — verified by `npm run typecheck`, never
 * executed at runtime (not matched by the `tests/*.test.ts` glob).
 *
 * Each `@ts-expect-error` line must fail to compile; if the types regress and
 * a line stops erroring, tsc fails with "Unused '@ts-expect-error' directive".
 */

import { t } from '../src/i18n';

// Missing required params must fail.
// @ts-expect-error spo2Critical requires the {value} param
void t('reason.spo2Critical');
// @ts-expect-error spo2Critical requires the 'value' key inside params
void t('reason.spo2Critical', {});

// Params a template does not declare must fail.
// @ts-expect-error 'common.history' takes no params at all
void t('common.history', { foo: 1 });
// @ts-expect-error levelName needs {level}, not {value}
void t('severity.levelName', { value: 1 });
// @ts-expect-error excess property on a param-ful string is rejected
void t('reason.spo2Critical', { value: 89, foo: 1 });

// These must compile — typecheck fails if the types regress.
void t('common.history');
void t('reason.spo2Critical', { value: 89 });
void t('severity.levelName', { level: 1 });
void t('disclaimer.body', { emergencyNumber: 911 });
void t('history.painValue', { pain: 4 });
void t('history.durationValue', { hours: 6 });
