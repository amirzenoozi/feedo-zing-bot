# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Releases Quick Access
* [Unreleased](#unreleased)


## [Unreleased]

## [1.2.1] - 2026-04-07
### Added
- Add `/add_official` for Admin user to add offical RSS feeds for all users
- Add `/stats` for Admin user to see the stats of the bot

### Changed
- Update Translations
- Update `README.md`

### Fixed
- Solve `/add_official` Registration Error

## [1.1.2] - 2026-04-06
### Added
- Support Custom RSS Feeds for Users

### Fixed
- Solve Generating the Custom RSS button for Each User
- Remove `mode` from Toggling Button Handler


## [1.0.3] - 2026-04-06
### Added
- Add `get_now` Command for premium users

### Changed
- Update Translations

### Fixed
- Fix `get_now` Inline Button Command
- Fix `buy_sub` Inline Button Command


## [1.0.2] - 2026-04-06
### Added
- Let users choose their own Feeds

### Fixed
- Solve Syntax Error on SQL Query
- Correct BASE_DIR calculation in `bot.py`


## [0.2.0] - 2026-04-05
### Added
- Support Multilingual Messages
- Dockerized the whole application
- Add `README.md` to have a better overview of the project