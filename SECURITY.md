# Security Policy

## Supported versions

Security fixes are applied to the latest version on the default branch.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue.

Use the repository's **Security** tab and choose **Report a vulnerability** to submit a private report. If private vulnerability reporting is not enabled, contact the repository owner privately through their GitHub profile and include:

- The affected component and version or commit
- Reproduction steps or a minimal proof of concept
- Expected and observed impact
- Any suggested mitigation

Do not include real credentials, private user data, or destructive payloads. You should receive an acknowledgement after the maintainer reviews the report; disclosure timing will be coordinated after a fix is available.

## Security scope

Particular attention is given to API input validation, unsafe HTML rendering, CORS configuration, local Ollama transport, dependency vulnerabilities, and accidental credential exposure.
