# Security policy

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

Send the details to:

- Email: [bernardo.leandro@gmail.com](mailto:bernardo.leandro@gmail.com)
- Subject line: **`Markdown Hero: <short description>`**

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal Markdown sample is ideal).
- The version of `markdown_hero` and the Python version you tested on.
- Whether you believe the issue is exploitable in a pure-library context
  or only via the `markdown-hero` CLI.

You will receive an acknowledgement as soon as possible. Coordinated
disclosure timelines will be agreed on a case-by-case basis.

## Supported versions

The latest minor release is the only branch that receives security fixes.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Threat model

`markdown_hero` is a pure-Python library. It does not open network
connections, does not execute Markdown content, and does not unpickle
data. The only externally-supplied inputs are Markdown text and
optional regex patterns; risks are limited to:

- **ReDoS** when `markdown_break(is_regex=True, ...)` is given an
  attacker-controlled pattern. See `docs/reference.md` section 13.
- **YAML loading** in frontmatter is performed via `yaml.safe_load`,
  which prevents deserialization of arbitrary Python objects.

If you find a path that violates these assumptions, please report it
using the channel above.

## General contact

For non-security questions or feedback, please use:

- Email: [bernardo.leandro@gmail.com](mailto:bernardo.leandro@gmail.com)
- Subject line: **`Markdown Hero: <topic>`**

Using the `Markdown Hero:` subject prefix on every message keeps the
project correspondence searchable and routed correctly.
