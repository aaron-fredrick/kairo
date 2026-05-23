# Contributing to Kairo

First off, thank you for considering contributing to Kairo! It's people like you that make Kairo such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please be respectful and considerate of others.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for Kairo. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

* Use the Bug Report issue template.
* Explain the problem and include additional details to help maintainers reproduce the problem.
* Include screenshots and animated GIFs in your pull request whenever possible.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for Kairo, including completely new features and minor improvements to existing functionality.

* Use the Feature Request issue template.
* Provide a clear and descriptive title for the issue.
* Provide a step-by-step description of the suggested enhancement.

### Pull Requests

* Fill in the required template.
* Do not include issue numbers in the PR title.
* Include screenshots and animated GIFs in your pull request whenever possible.
* Follow the Python and Javascript coding styles.
* Document new code based on the Documentation Styleguide.
* End files with a newline.

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature").
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...").
* Limit the first line to 72 characters or less.
* Reference issues and pull requests liberally after the first line.

### Coding Guidelines

#### Backend (Python / FastAPI)
- We follow PEP 8 standards.
- Use type hints (`typing` module).
- Ensure all models inherit from the common SQLAlchemy `Base`.
- Add docstrings to functions and classes.

#### Frontend (Svelte / JavaScript)
- Use functional programming patterns where possible.
- Organize components cleanly.
- Keep CSS modular (component-scoped).
