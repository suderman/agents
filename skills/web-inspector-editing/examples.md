# Examples

## Example: test a CSS override on a live marketing page

1. Open the target URL in chrome-devtools.
2. Reload with cache ignored.
3. Wait for a stable piece of page text such as the section heading.
4. Inspect the rendered DOM and measure the target region with
   `getBoundingClientRect()` and `getComputedStyle()`.
5. Inject one temporary `<style>` block with a unique id.
6. Measure again to confirm the intended layout change happened.
7. Take a screenshot.
8. If the result is not good enough, reload before trying a different CSS idea.

## Example: recent content might be missing because of caching

1. Load the page and verify whether the expected element exists in the live DOM.
2. If it is missing but expected to be recent, reload with cache ignored.
3. If it still looks stale, retry with a cache-busting query string such as
   `?v=2`.
4. If needed, open a fresh tab in a separate isolated context.
5. Confirm the new content is present before testing CSS or JS.

## Example: compare two CSS layout approaches safely

1. Reload the page.
2. Inject attempt A.
3. Measure and screenshot the result.
4. Record what worked and what did not.
5. Reload the page again.
6. Inject attempt B.
7. Measure and screenshot again.
8. Recommend only the attempt that worked from a clean reload.

## Example: test a JavaScript fix for a broken interaction

1. Reload the page and wait for the relevant UI.
2. Reproduce the issue once without any injected code.
3. Check console and network evidence.
4. Inject one small JavaScript experiment with `evaluate_script`.
5. Trigger the interaction again.
6. Verify behavior changed as expected.
7. Reload before trying a different JS approach.

## Example: validate five cards stay on one row

1. Reload the page.
2. Inject the candidate CSS override.
3. Query all visible cards and collect their `top` values.
4. Confirm success only if all target cards share the same `top` value.
5. Take a screenshot to confirm the visual result.
6. If spacing or sizing is poor, reload before adjusting widths or logo sizes.

## Example: previous test code polluted the page

1. Notice that computed styles or layout do not match the site's source CSS.
2. Inspect `<style>` tags in the document and look for previously injected test
   code.
3. Do not trust the current page state.
4. Reload the page or open a fresh isolated tab.
5. Reconfirm the page is clean.
6. Only then begin the next attempt.
