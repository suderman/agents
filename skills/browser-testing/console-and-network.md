# Console and Network Inspection

Browser-side signals often reveal the real cause faster than reading source
files.

## Console inspection

Check for:

- uncaught exceptions
- failed imports
- hydration mismatches
- warnings tied to the broken component
- permission or security errors
- asset load failures
- API parsing errors

Do not dismiss warnings too quickly. Some warnings explain why the UI never
updated.

## Network inspection

Check for:

- failed API requests
- unexpected status codes
- bad payload shapes
- slow responses
- repeated polling failures
- CORS issues
- authentication failures
- stale cached responses

## Use network evidence well

When a UI looks empty or broken, ask:

- did the request fire?
- did it fail?
- did it succeed with unexpected data?
- did it never happen?
- did the UI fail after receiving valid data?

## Correlate signals

Look for connections between:

- user action
- network request
- console output
- DOM update or lack of update

## Strong debugging pattern

1. perform the action
2. watch for console output
3. watch for network requests
4. inspect resulting DOM
5. compare expected vs actual behavior

## Rule

Do not treat the UI as the only source of truth. The browser runtime is telling
you what happened.
