# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - Consolidated deployment efforts and release

We created a Dockerfile and published a consolidated scistream deployment container. It uses the subprocess implementation and starts Stunnel and Haproxy services. This hasn't been tested extensively.

We also created a "abstract" parent class for all the subprocess plugins, current implementations are haproxy and stunnel.

Improved a few testings

## [1.1.6] - Various deployments improvements

In order to provide a better documented procedure for installation we introduced an ansible playbook for vagrant development. We also have a 
scistream.yml playbook that should represent the procedure for running Scistream.

In order to remove the docker dependency, we developed a subprocess plugin for running S2DS, this version runs Stunnel specifically, this should later be generalized to run the other types of proxies. 

We implemented a port reservation mechanism at S2CS for the Stunnel implementation. This needs to be revised because it breaks separation of concerns between S2CS and S2DS.

When using verbose a app.log file is now created for better logging and auditing 

We consolidated S2UC commands so that the appcontroller functionality is now integrated into the initial request.

### Breaking changes
 - This version deprecates the cons-req command

### [Added]
 - S2DS implementation for Stunnel using Subprocesses
 - inbound-request new S2UC command that  integrates appcontroller
 - S2DS pytests
 - Provisioning Ansible playbook for vagrant development environment
 - Consolidated Scistream container with all dependencies included.
 - get_available_ports function in S2CS for port reservation
 - port_range configuration parameter for S2CS

### [Modified]
 - set_verbosity functionality to log to file

### 

## [1.1.0] - Security Enhancements

This release focuses on improving security architecture. It introduces encrypted Control Channel communication, deprecates unencrypted calls, and adds low-overhead authentication for data-plane endpoints via Stunnel.

### Breaking Changes
 - This version is not backwards compatible due to security architecture modifications
 - Deprecated and removed support for unencrypted calls to Scistream Control Server (S2CS)
 - Removed support for unencrypted requests from Scistream User Client (S2UC) and appcontroller

### [Added]
- Security enhancements:
  - TLS support via Stunnel
  - PSK authentication via Stunnel
  - Added low-overhead Data-channel authentication
- Stunnel support:
  - Added Stunnel support to Scistream Data Server (S2DS)
  - Added PSK key volume mount config to docker S2DS plugin
  - Added Stunnel Jinja2 config template
- Other additions:
  - Added default None value for context variable
  - Added role and uid parameters to S2DS update_listeners
- Testing:
  - Added HAproxy, Stunnel, Nginx docker tests on pytest

### [Fixed]
 - Fixed directory creation issue on S2DS

## [1.0.0]

### [Added]
 - Haproxy implementation of Scistream Data Server now permits explicit definition of the path for its configuration file.
 - Haproxy default location for its configuration has been modified.
 - All CLI commands now support --version

## [0.2.0]

### [Added]
 - Scistream User Client(S2UC) now supports explicitly defining the scope of the control server
 - Scistream Data Server now uses Haproxy by default instead of the naive S2DS implementation

### [Fixed]
 - Imports in the unit tests
 - Revised Auth tutorial documentation.

### [Removed]
 - Error message on S2UC when no authentication token is present, now it just assumes no authentication is required.

## [0.1.6]

### [Added]
 - Nginx config template can now setup multiple connections
 - Created ProxyContainer parent class and made Nginx and Haproxy inherit from it. deleted old Nginx implementation
 - Modified s2uc so that it can send an array of ports

### [Fixed]
 - Improved logic for S2UC authorization

### [Bug]
 - Hardcoded app controller ports for pvapy tests[WIP]
 - Modified behavior of get_access_token(). This needs to be further tested [WIP]

### [Removed]
 - Commands developed specifically for previous demos have been removed
