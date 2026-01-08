# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future changes will be documented here

## [1.0.0] - 2026-01-08

### Added
- Initial release
- Asynchronous document parsing service based on Celery
- Decoupled API/Worker architecture
- Support for multiple document formats (PDF, Office, images)
- MinerU and MarkItDown parsing backends
- Local and S3-compatible storage support
- Task priority queue
- Real-time task status tracking
- Queue statistics and monitoring
- Docker Compose deployment
- CPU and GPU worker support
- Automatic cleanup service
- Health check endpoints
- Comprehensive API documentation (FastAPI/Swagger)
- Comprehensive documentation (README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY)
- CI/CD pipeline with GitHub Actions

### Features
- **API Service**: Lightweight FastAPI service for task submission and querying
- **Worker Service**: Celery-based worker for document parsing
- **Storage Abstraction**: Unified interface for local filesystem and S3 storage
- **Task Management**: Submit, query, cancel, and monitor parsing tasks
- **Multi-format Support**: PDF, images (PNG, JPG, etc.), Office documents (Word, Excel, PowerPoint)
- **Language Support**: Chinese, English, and other languages
- **Image Processing**: Base64 encoding and MinIO upload support
- **Cleanup Service**: Automatic cleanup of expired output files

### Technical Details
- Python 3.10+ support
- FastAPI for API layer
- Celery 5.3+ for task queue
- Redis for message broker and result backend
- Docker containerization
- S3-compatible storage (MinIO, AWS S3)

### Documentation
- Comprehensive README (English and Chinese)
- API documentation
- Deployment guides
- Storage configuration guides
- Troubleshooting guides

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

---

## Version History

- **1.0.0**: Initial release with decoupled architecture and comprehensive features

---

For detailed commit history, see [GitHub Commits](https://github.com/wzdavid/mineru-api/commits/main).
