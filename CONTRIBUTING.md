# Contributing to AI-EDR Threat Detection System

## Purpose

This project is an open-source research platform for AI-powered endpoint detection and response. Contributions are welcome from security researchers, ML engineers, and developers interested in cybersecurity automation.

## Guidelines

### Security
- All code changes must consider security implications
- Never commit hardcoded credentials or API keys
- Use environment variables for sensitive data

### Code quality
- Follow PEP 8 for Python code
- Add type hints where applicable
- Include docstrings for new functions

### Testing
- Test malware analysis functions with safe, known samples
- Describe the test environment when changing Azure VM lifecycle management
- Include the dataset and method when reporting detection-accuracy results

- Update `README.md` for new features
- Document API endpoints
- Add MITRE ATT&CK technique mappings when applicable

## Getting started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contribution areas

- Improved threat detection algorithms
- New sandbox integration (VMware, VirtualBox)
- Additional AI model support (OpenAI, Claude)
- Visualization enhancements
- Bug fixes and performance optimization

---

## Legal notice

By contributing to this project, you agree to use it only for **authorized security research and defensive purposes**.