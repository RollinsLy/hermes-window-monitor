# Security and privacy

The monitor reads local process names, parent relationships, command-line
arguments, CPU activity, and classic console window titles to associate Hermes
sessions with windows. Tooltips display profile names, window titles, handles,
and process IDs. It does not read chat history or terminal contents and contains
no network client, telemetry, account login, or API key requirement.

Command lines and titles can still contain sensitive information. Redact them
before sharing screenshots or bug reports. Run as your normal Windows user;
administrator access should not be needed for sessions owned by that user.

The `--demo` option uses simulated sessions, does not scan processes, and disables
click-to-focus. It is useful for recording a privacy-safe preview.

For a suspected vulnerability, use GitHub's private vulnerability reporting flow
if it is enabled for this repository. Otherwise open an issue with a minimal,
non-sensitive description and ask the maintainer to arrange a private channel.
Do not publish credentials or exploitable private details in a public issue.

This is a small volunteer project without a guaranteed response-time commitment.
