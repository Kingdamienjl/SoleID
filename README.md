# SoleID - Complete Sneaker Recognition System

SoleID is a comprehensive sneaker identification and tracking system consisting of a web scraper backend and an Android mobile application. The system uses machine learning to identify sneakers from photos and provides real-time price tracking across multiple platforms.

## 🏗️ Project Structure

```
SoleID/
├── sneaker-scraper/          # Python backend web scraper
│   ├── api.py               # FastAPI REST API
│   ├── scrapers.py          # Web scrapers for StockX, GOAT, eBay
│   ├── models.py            # Database models
│   ├── scraper_manager.py   # Orchestration and scheduling
│   ├── image_processor.py   # Image processing utilities
│   ├── google_drive.py      # Google Drive integration
│   ├── database.py          # Database initialization
│   ├── utils.py             # Utility functions
│   ├── config.py            # Configuration management
│   ├── main.py              # Application entry point
│   ├── setup.py             # Project setup script
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment variables template
│   └── README.md            # Backend documentation
│
└── android-app/             # Android mobile application
    ├── app/
    │   ├── src/main/java/com/soleid/app/
    │   │   ├── data/            # Data layer (API, database, models)
    │   │   ├── di/              # Dependency injection
    │   │   ├── ml/              # Machine learning models
    │   │   └── presentation/    # UI layer (screens, components, themes)
    │   ├── src/main/res/        # Android resources
    │   └── build.gradle         # App-level build configuration
    ├── build.gradle             # Project-level build configuration
    ├── settings.gradle          # Gradle settings
    └── README.md                # Android app documentation
```

## 🚀 Quick Start

### Backend Setup (Python Scraper)

1. **Navigate to the scraper directory:**
   ```bash
   cd sneaker-scraper
   ```

2. **Run the setup script:**
   ```bash
   python setup.py
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Update database URLs, API keys, and Google Drive credentials

4. **Start the scraper:**
   ```bash
   python main.py
   ```

### Android App Setup

1. **Open the project in Android Studio:**
   - Open `android-app` folder in Android Studio

2. **Configure API endpoint:**
   - Update `API_BASE_URL` in `build.gradle` to point to your backend

3. **Add ML model:**
   - Place your TensorFlow Lite model in `assets/` folder
   - Update model filename in `SneakerRecognitionModel.kt`

4. **Build and run:**
   - Sync project with Gradle files
   - Run on device or emulator

## 🔧 System Requirements

### Backend
- Python 3.8+
- PostgreSQL database
- Redis (for caching and task queues)
- Google Drive API credentials
- Chrome/Firefox browser (for Selenium)

### Android App
- Android Studio Arctic Fox or newer
- Android SDK 24+ (Android 7.0)
- Device with camera support

## 📱 Features

### Backend Features
- **Multi-platform scraping:** StockX, GOAT, eBay integration
- **Real-time price tracking:** Automated price monitoring
- **Image processing:** Advanced image analysis and feature extraction
- **Google Drive integration:** Automatic backup and storage
- **RESTful API:** Complete API for mobile app integration
- **Scheduled scraping:** Automated data collection

### Android App Features
- **Real-time camera recognition:** Instant sneaker identification
- **Comprehensive database:** Extensive sneaker information
- **Price tracking:** Current and historical pricing data
- **Favorites system:** Save and organize favorite sneakers
- **Offline support:** Local database caching
- **Modern UI:** Material 3 design with Jetpack Compose

## 🔌 API Integration

The Android app communicates with the backend through REST API endpoints:

- `GET /sneakers` - Retrieve all sneakers
- `GET /sneakers/{id}` - Get specific sneaker details
- `POST /sneakers/search` - Search sneakers with filters
- `GET /sneakers/similar/{id}` - Find similar sneakers
- `POST /scrape/trigger` - Trigger manual scraping
- `GET /stats` - Get database statistics

## 🤖 Machine Learning

The system uses TensorFlow Lite for on-device sneaker recognition:

- **Model format:** TensorFlow Lite (.tflite)
- **Input:** Camera images (224x224 RGB)
- **Output:** Sneaker predictions with confidence scores
- **Features:** Real-time inference, offline processing

## 🔒 Security & Privacy

- **API keys:** Stored securely in environment variables
- **Local storage:** Encrypted database on device
- **Image processing:** On-device ML inference
- **Data backup:** Secure Google Drive integration

## 📊 Data Sources

- **StockX:** Primary marketplace data
- **GOAT:** Secondary marketplace verification
- **eBay:** Additional pricing and availability
- **Google Drive:** Image and data backup storage

## 🛠️ Development

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/

# Database migrations
alembic upgrade head
```

### Android Development
```bash
# Build debug APK
./gradlew assembleDebug

# Run tests
./gradlew test

# Generate release APK
./gradlew assembleRelease
```

## 📈 Monitoring & Logging

- **Backend logs:** Stored in `logs/` directory
- **API monitoring:** Built-in FastAPI metrics
- **Error tracking:** Comprehensive error logging
- **Performance metrics:** Database and scraping statistics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the individual README files in each directory
- Review the API documentation
- Check the logs for error messages
- Ensure all environment variables are properly configured

## 🔮 Future Enhancements

- **Additional platforms:** Expand to more sneaker marketplaces
- **Advanced ML:** Improved recognition accuracy
- **Social features:** User reviews and ratings
- **Price alerts:** Push notifications for price changes
- **Barcode scanning:** UPC/EAN code recognition
- **AR features:** Augmented reality try-on