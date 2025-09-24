# RubinTV

Learn more at https://rubintv.lsst.io (to follow)

rubintv is developed with [FastAPI](https://fastapi.tiangolo.com) and [Safir](https://safir.lsst.io).

## Overview

RubinTV is a small project scaffold intended to collect and display current and historic plots, images and movies from the S3 buckets at the various processing locations (Summit, USDF, BTS and TTS).
It also hosts services and web UI components related to Rubin Observatory tooling such as DDV (Direct Data Visualization)

The codebase aims to be modular and easy to extend: a backend built with FastAPI and Safir, and a frontend that uses modern TypeScript and React patterns.

This repository contains the core services and documentation to get started quickly and to follow project conventions.

## Project layout (typical)

- `python/lsst/ts/rubintv` - FastAPI application and service code
- `tests/` - Unit and integration tests for the backend
- `src/` - React + TypeScript frontend
- `src/js/components/tests` - Tests for React components

## Quick start (frontend)

1. Change into the `src/` directory.
2. Install dependencies: `npm install` or `yarn`.
3. Run the webpack compiler: `npm run build`

The project is currently loaded and run via the FastAPI backend

## Typescript Rules

- Do not use an `interface` for React component props if there is only one prop and it is not reused across multiple components. Prefer a `type` alias or an inline prop type in that case.
  - Rationale: using a `type` or inline type keeps the component local and avoids accidental declaration merging and unnecessary exports for a one-off props shape.

Other style notes:

- Favor explicit, narrow types and prefer immutability where reasonable.
- Opt for readability rather than reusability - if inline types are not causing function signatures to spill over a single line then use fully qualified types for clarity.
  e.g. `const handleConfirmSubmit = (e: React.FormEvent<HTMLFormElement>) => {}` allows the type of the target element to be seen without obfuscation.

## Contributing

Please follow the contribution guidelines in `CONTRIBUTING.md` (if present). Keep changes small and focused, add tests for behavior, and update docs when adding or changing public APIs.

## License

This project is provided under the terms of the LICENSE file in the repository.
