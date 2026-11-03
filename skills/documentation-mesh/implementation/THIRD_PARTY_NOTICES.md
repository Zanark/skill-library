# Third-party notices

The offline dashboard bundles the following pinned npm packages and their transitive browser dependencies:

- `force-graph` 1.51.4 — MIT
- `d3-force-3d` and related D3 modules resolved by the committed lockfile — ISC/BSD-style licenses as declared by their packages

Development browser tests use `playwright-core` 1.62.1 under the Apache-2.0 license. Playwright is not included in the end-user runtime.

The distributable package retains the package lock and this notice. Exact resolved versions and integrity hashes are recorded in `package-lock.json`.

The Windows x64 executable includes the self-contained Microsoft .NET 8 runtime, licensed under the MIT license. The application itself references no third-party NuGet packages.
