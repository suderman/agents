# Examples

## Example: button click does nothing

1. Open the page and locate the button
2. Take a screenshot and inspect visible state
3. Click the button
4. Check:
   - did the UI change?
   - did a request fire?
   - did the console report an error?
   - did a modal fail to open?
5. Inspect the clicked element and surrounding DOM
6. Form a concrete hypothesis before editing code

## Example: empty list that should contain data

1. Open the page and wait for loading to finish
2. Check if the request for the list fired
3. Inspect the response payload
4. Inspect console output for rendering or parsing errors
5. Inspect the DOM region where list items should appear
6. Determine whether the issue is:
   - request never fired
   - request failed
   - data shape mismatch
   - render logic bug
   - hidden/filtered UI state

## Example: form submission appears broken

1. Fill the form with valid test data
2. Submit it
3. Watch for:
   - disabled/loading state
   - validation messages
   - network request
   - redirect or success message
   - console errors
4. Verify whether the failure is:
   - client-side validation
   - submit handler not firing
   - API failure
   - success response with bad UI update

## Example: style/layout issue

1. Open the page at the affected screen state
2. Capture screenshot
3. Inspect the affected region in rendered DOM
4. Check computed visibility, size, overflow, and positioning clues
5. Confirm whether the issue is:
   - incorrect classes or styles
   - conditional rendering
   - missing content
   - layout collision from surrounding elements

## Example: route transition problem

1. Start from the page before the transition
2. Trigger the navigation
3. Watch:
   - URL change
   - loading state
   - console errors
   - failed route data requests
4. Confirm whether the app:
   - never navigated
   - navigated but failed to render
   - rendered stale content
   - hit an auth or data-loading problem
