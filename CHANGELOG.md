# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The library (`dqt`) and the server (`dqt-server`) version independently. Library entries are tagged `dqt`; server entries are tagged `server`.

## [Unreleased]

### Added
- Initial scaffolding: monorepo layout with `packages/dqt`, `apps/server`, `apps/worker`, `apps/web`.
- `.cursor/rules/` set covering library/server boundary, algorithms, adapters, checks, lineage, semantic, causality, agent, governance, HITL, incidents/on-call, frontend, design tokens, deployment, i18n, and the glossary.
- Initial CLAUDE.md describing architecture, statistical scales, engine catalog, and module structure.
