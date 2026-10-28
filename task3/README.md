# iLearning Task 3 — Python LCM service

Dependency-free Python HTTP GET endpoint. The path is derived from the
`REGISTRATION_EMAIL` environment variable by replacing every character other
than ASCII letters and digits with `_`.

Examples at the configured path:

- `?x=12&y=18` returns the plain text `36`.
- `?x=0&y=18` returns `0`.
- Missing, repeated, negative or non-integer arguments return `NaN`.

The implementation uses `math.gcd` and arbitrary-precision integers.
No HTML or JSON is added to the response.

## Run

Set `REGISTRATION_EMAIL`, optionally `HOST` and `PORT`, then run `python app.py`.
For public hosting set `HOST=0.0.0.0`. The Dockerfile uses Python 3.12 and
runs as a non-root user. Render supplies HTTPS in front of the HTTP service.

## Test

```text
python -B -m unittest -v test_app.py
```

The 36 tests cover real local HTTP requests, valid and invalid inputs,
zero, large integers, response formatting and configuration.

## Submission format

```text
!task3 REGISTRATION_EMAIL https://ACTUAL-HOST/SANITIZED_EMAIL?x={}&y={}
```

Keep the braces literally. Verify the actual public endpoint before submission.
On Render Free, open the endpoint and wait for a successful response before
submitting, because idle services can take time to start.
