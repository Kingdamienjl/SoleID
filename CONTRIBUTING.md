# Contributing to SoleID 🤝

Thank you for your interest in contributing to SoleID! This document provides guidelines and information for contributors.

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Use the [GitHub Issues](https://github.com/yourusername/SoleID/issues) page
- Search existing issues before creating new ones
- Provide detailed reproduction steps
- Include system information and error logs

### 💡 Feature Requests
- Discuss new features in [GitHub Discussions](https://github.com/yourusername/SoleID/discussions)
- Explain the use case and expected behavior
- Consider implementation complexity and project scope

### 🛠️ Code Contributions
- Fork the repository and create a feature branch
- Follow the coding standards outlined below
- Write tests for new functionality
- Update documentation as needed

## 🏗️ Development Setup

### Backend Development
```bash
cd sneaker-scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configure your .env file
python build_database.py
```

### Android Development
```bash
cd android-app
# Open in Android Studio or use command line
./gradlew build
```

## 📋 Coding Standards

### Python (Backend)
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

### Kotlin (Android)
- Follow Kotlin coding conventions
- Use meaningful class and function names
- Implement proper error handling
- Follow Android architecture guidelines
- Use dependency injection with Hilt

### General Guidelines
- Write clear, self-documenting code
- Add comments for complex logic
- Keep commits atomic and well-described
- Update tests when modifying functionality

## 🧪 Testing

### Backend Testing
```bash
cd sneaker-scraper
python -m pytest tests/
```

### Android Testing
```bash
cd android-app
./gradlew test
./gradlew connectedAndroidTest
```

## 📝 Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch from `main`
3. **Make** your changes with clear commits
4. **Test** your changes thoroughly
5. **Update** documentation if needed
6. **Submit** a pull request with:
   - Clear title and description
   - Reference to related issues
   - Screenshots for UI changes
   - Test results

## 🎯 Priority Areas

### High Priority
- RapidAPI integration implementation
- Android app UI completion
- ML model optimization
- Performance improvements

### Medium Priority
- Additional scraping sources
- Enhanced error handling
- Comprehensive testing
- Documentation improvements

### Low Priority
- Code refactoring
- Minor UI enhancements
- Additional utility features

## 🏷️ Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `priority-high` - High priority items
- `backend` - Backend/API related
- `android` - Android app related
- `ml` - Machine learning related

## 📞 Getting Help

- **Questions**: Use [GitHub Discussions](https://github.com/yourusername/SoleID/discussions)
- **Chat**: Join our community chat (link coming soon)
- **Email**: For private inquiries

## 📄 License

By contributing to SoleID, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make SoleID better! 🚀👟