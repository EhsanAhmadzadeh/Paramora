# Security Policy

Paramora is a FastAPI-native query compilation library. Security matters because Paramora processes user-controlled HTTP query parameters and emits backend query objects.

Please report potential vulnerabilities privately before opening a public issue.

## Supported Versions

Paramora is currently alpha software. Security fixes are provided for the latest released version only.

| Version | Supported |
| --- | --- |
| latest alpha release | Yes |
| older alpha releases | No |

After Paramora reaches `1.0`, this policy may change to support multiple maintained release lines.

## Reporting a Vulnerability

Please report security issues by email:

**amirehsansolout@gmail.com**

Use the subject line:

```text
[SECURITY] Paramora vulnerability report
````

Please include as much detail as possible:

* Paramora version
* Python version
* FastAPI version, if relevant
* Backend/emitter used, for example MongoDB
* A minimal query contract, if relevant
* The malicious or unexpected query string
* Expected behavior
* Actual behavior
* Impact assessment, if known
* Minimal reproduction code, if safe to share

Example report structure:

```text
Paramora version:
Python version:
FastAPI version:
Backend:

Query contract:

Query string:

Actual behavior:

Expected behavior:

Impact:

Reproduction:
```

## What Counts as a Security Issue

Please report privately if you find behavior that may allow:

* raw backend operator injection, for example raw MongoDB operators exposed through query parameters
* bypassing strict-mode field validation
* bypassing strict-mode operator validation
* incorrect type coercion that changes security-relevant filter behavior
* malformed query parameters producing unsafe backend query output
* denial-of-service behavior caused by pathological query strings
* unsafe behavior in backend emitters
* inconsistent validation between direct `Query.parse(...)` use and FastAPI dependency use
* error payloads that leak sensitive server-side implementation details

## What Usually Does Not Count as a Security Issue

These can usually be opened as normal GitHub issues:

* documentation typos
* non-security parser bugs
* unsupported query syntax
* expected validation errors
* feature requests for new operators
* performance improvements without denial-of-service impact
* type checker warnings without runtime security impact

When unsure, report privately.

## Response Expectations

I will try to acknowledge security reports within **7 days**.

A typical process is:

1. Acknowledge the report.
2. Reproduce and assess the issue.
3. Decide whether it is a security vulnerability.
4. Prepare a fix privately when appropriate.
5. Publish a patched release.
6. Credit the reporter if they want credit.

For critical issues, I will try to prioritize a patch as soon as reasonably possible.

## Disclosure Policy

Please do not publicly disclose a suspected vulnerability until a fix is available or until we have discussed a disclosure timeline.

I prefer coordinated disclosure:

* private report first
* maintainer confirmation
* patch release
* public advisory or issue after users can upgrade

## Security Design Notes

Paramora should never expose raw backend query operators through HTTP query parameters by default.

For example, Paramora should reject raw MongoDB-style input such as:

```http
/items?price[$gte]=10
/items?price__$gte=10
/items?$where=...
```

Instead, developers declare safe query contracts:

```python
from typing import Annotated

from paramora import QueryContract, query_field


class ItemQuery(QueryContract):
    price: Annotated[float, query_field("gte", "lte")]
```

Then users send backend-neutral query parameters:

```http
/items?price__gte=10&price__lte=20
```

Paramora validates and compiles those parameters into backend-specific query objects.

## Strict Mode and Loose Mode

Paramora has two operating modes:

* `Query()` uses loose mode.
* `Query(MyContract)` uses strict mode.

Strict mode is recommended for public APIs.

Loose mode is useful for prototypes, trusted internal tools, and admin utilities, but it should still not allow raw backend operator injection by default.

## Dependency Security

Paramora aims to keep runtime dependencies minimal.

When adding dependencies, contributors should consider:

* whether the dependency is required at runtime
* whether it increases the trusted computing base
* whether it is actively maintained
* whether it affects query parsing, validation, or backend emission security

## Maintainer Contact

Maintainer: **Ehsan Ahmadzadeh**

Email: **[amirehsansolout@gmail.com](mailto:amirehsansolout@gmail.com)**
