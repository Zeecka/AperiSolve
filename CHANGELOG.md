# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.1] - 2026-03-30

### Security

- Fixed shell command injection vulnerability in the `jpseek` analyzer
  ([#133](https://github.com/Zeecka/AperiSolve/issues/133)).
  The password supplied by the user was previously interpolated directly into
  a shell command string passed to `bash -c`, allowing arbitrary command
  execution. The fix passes the password via an environment variable
  (`JPSEEK_PASS`) and invokes `expect` directly (without a shell wrapper),
  eliminating the injection vector. File paths in the Tcl script are now
  safely quoted using Tcl braces.
