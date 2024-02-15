# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### [Added]
- Nginx config template can now setup multiple connections
- Created ProxyContainer parent class and made Nginx and Haproxy inherit from it. deleted old Nginx implementation
- Modified s2uc so that it can send an array of ports

### [Bug]
- Hardcoded app controller ports for pvapy tests[WIP]
- Modified behavior of get_access_token(). This needs to be further tested [WIP]
