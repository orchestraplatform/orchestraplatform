---
title: Introduction
description: Welcome to the Orchestra Platform - a comprehensive bioinformatics and data science learning environment
---

# Welcome to Orchestra Platform

Orchestra Platform is a cloud-native, Kubernetes-based learning environment designed specifically for bioinformatics and data science education. It provides instructors and students with on-demand, isolated workshop environments that can be quickly provisioned and automatically managed.

## What is Orchestra Platform?

Orchestra Platform enables educational institutions, research organizations, and training companies to deliver hands-on bioinformatics and data science workshops without the complexity of manual infrastructure management. Each workshop runs in its own isolated environment with dedicated resources, ensuring a consistent and reliable learning experience.

## Key Features

### 🚀 **Instant Workshop Creation**
- Create fully configured workshop environments in minutes
- Support for popular bioinformatics tools (RStudio, Jupyter, etc.)
- Automated resource provisioning and cleanup

### 🔒 **Secure & Isolated**
- Each workshop runs in its own Kubernetes namespace
- Network isolation between workshop instances
- Secure access via unique subdomains and HTTPS

### ⏰ **Time-Limited Sessions**
- Configurable workshop duration (hours to days)
- Automatic cleanup when sessions expire
- Resource management and cost control

### 🎯 **User-Friendly Interface**
- Simple web dashboard for workshop management
- Real-time status monitoring
- Easy sharing of workshop URLs

### 📚 **Flexible Content**
- Support for custom Docker images
- Persistent storage for workshop data
- Pre-configured environments for common workflows

## Use Cases

### Educational Institutions
- Bioinformatics courses and workshops
- Computational biology training
- Data science bootcamps
- Research method courses

### Research Organizations
- Training workshops for new tools
- Collaborative analysis sessions
- Reproducible research environments
- Method development and testing

### Industry Training
- Professional development workshops
- Customer training sessions
- Product demonstrations
- Certification programs

## Architecture Overview

Orchestra Platform consists of four main components:

1. **Orchestra Operator** - Kubernetes operator managing workshop lifecycle
2. **Orchestra API** - REST API for workshop operations
3. **Orchestra Frontend** - Web application for users
4. **Orchestra Docs** - Comprehensive documentation (this site)

Each workshop gets its own unique subdomain and runs in complete isolation from other workshops.

## Getting Started

Ready to start using Orchestra Platform? Check out our [Installation Guide](/getting-started/installation/) to set up your own instance, or jump to the [User Guide](/user-guide/creating-workshops/) to learn how to create your first workshop.

## Community and Support

Orchestra Platform is open source and welcomes contributions from the community. Visit our [GitHub repository](https://github.com/seandavi/orchestra-operator) to:

- Report issues or request features
- Contribute code improvements
- Join discussions about the platform
- Access the latest development updates

For questions and support, please check our documentation or open an issue on GitHub.
