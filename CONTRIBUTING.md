# Contributing to Buienalarm

We love contributions to the Buienalarm project! Whether it's fixing bugs, adding features, improving documentation, or providing feedback, your help is appreciated.

## How to Contribute

### 1. Fork the Repository
To contribute to the Buienalarm project, first, fork the repository to your GitHub account. This allows you to make changes in your own copy of the repository.

### 2. Create a New Branch
Once you’ve forked the repository and cloned it to your local machine, create a new branch for your changes:

```bash
git checkout -b my-feature-branch
```

### 3. Make Your Changes
Make your changes in the appropriate files. If you're adding a new feature, please ensure that it is thoroughly tested. If you're fixing a bug, please include a test to verify the fix.

- **Code style**: We follow the [PEP 8](https://peps.python.org/pep-0008/) coding standards for Python code.
- **Formatting**: We use [black](https://black.readthedocs.io/) for Python code formatting. Please run `black .` before committing your changes.
- **Testing**: Ensure that your changes pass the existing tests, and write new tests where applicable.

### 4. Test Your Changes
Make sure all tests are passing by running:

```bash
pytest
```

We use `pytest` to run tests. If your changes introduce new functionality, consider adding tests to cover that functionality.

### 5. Commit Your Changes
Once you’re happy with your changes, commit them with a clear and concise message:

```bash
git commit -m "Add feature or fix bug"
```

### 6. Push Your Changes
Push your changes to your fork:

```bash
git push origin my-feature-branch
```

### 7. Create a Pull Request
After pushing your changes, navigate to the original repository and create a pull request (PR). Be sure to describe the changes you've made, why they're needed, and any relevant context. This helps the maintainers review and merge your changes more efficiently.

### 8. Respond to Feedback
The maintainers may provide feedback on your PR. Please respond to comments and make the necessary updates to your PR. We appreciate your help in improving the project!

## Code of Conduct
We expect all contributors to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat others with kindness and respect.

## Reporting Issues
If you encounter a bug or have a suggestion for the project, feel free to open an issue on the GitHub repository. Be sure to provide as much detail as possible to help us understand the problem.

## Documentation
If you contribute to the documentation, please follow the existing structure and format. It's important to ensure that the documentation is clear, accurate, and up-to-date.

---

This template gives clear instructions for contributing to the project, including how to fork the repository, create a branch, make changes, and submit a pull request. You can further customize it based on specific contribution guidelines you want to set for your repository.
