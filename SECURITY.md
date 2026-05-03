# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities to [athenabot@qq.com](mailto:athenabot@qq.com).
Do not open a public issue.

Expect an acknowledgment within 48 hours and a fix timeline within 7 days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |

## Security Practices

- All credentials must be stored in `.env` files (gitignored)
- Run `bandit` and `trufflehog` before committing
- Do not use `shell=True` in `subprocess` calls without `# nosec` justification
