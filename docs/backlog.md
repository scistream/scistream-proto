---
title: "Advanced SciStream Tutorial for Developers"

introduction:
  - Brief overview of SciStream and its architecture
  - Purpose and goals of the tutorial
  - Prerequisites and required knowledge

part1:
  title: "Setting up a SciStream Environment with VMs"
  steps:
    - Preparing the Development Environment:
        - System requirements
        - Setting up virtual machines (VMs)
        - Network configuration
    - Installing SciStream from PyPI:
        - Creating a virtual environment
        - Installing SciStream using pip
        - Verifying the installation
    - Configuring SciStream Components:
        - SciStream Control Server (S2CS)
        - SciStream Data Server (S2DS)
        - SciStream User Client (S2UC)
    - Establishing a Sample Stream Flow:
        - Defining the producer and consumer applications
        - Configuring the stream endpoints
        - Starting the SciStream components
        - Monitoring and verifying the stream flow

part2:
  title: "Running SciStream from Source Code"
  steps:
    - Setting up the Development Environment:
        - Cloning the SciStream repository
        - Installing dependencies
        - Building the source code
    - Understanding the SciStream Codebase:
        - Overview of the source code structure
        - Key modules and components
        - Debugging and logging
    - Modifying and Extending SciStream:
        - Customizing S2CS and S2DS behavior
        - Implementing custom authentication and authorization mechanisms
        - Extending SciStream with new features
    - Deploying a Modified SciStream Instance:
        - Building and packaging the modified version
        - Deploying the custom SciStream components
        - Testing and validating the modifications

advanced_topics:
  - Performance tuning and optimization
  - Scaling SciStream components
  - Security considerations and hardening
  - Monitoring and troubleshooting techniques
  - Integration with external systems and tools

conclusion:
  - Recap of the tutorial objectives
  - Further resources and documentation
  - Community and support channels
  - Encouragement to contribute to the SciStream project

appendices:
  - Glossary of terms
  - Troubleshooting common issues
  - Additional code samples and scripts
  - References and external links
