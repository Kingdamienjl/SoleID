# SoleID iOS App

iOS port of the SoleID sneaker identification app.

## Requirements

- Xcode 15.0+
- iOS 16.0+
- Swift 5.9+
- macOS (for development)

## Setup

### 1. Open in Xcode

```bash
cd ios-app
open Package.swift
```

Or create a new Xcode project and add the package.

### 2. Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Add an iOS app to your existing SoleID project (or create new)
3. Download `GoogleService-Info.plist`
4. Add it to `SoleID/Resources/`

### 3. Build & Run

1. Select your target device/simulator
2. Build and run (⌘R)

## Project Structure

```
ios-app/
├── Package.swift              # Swift Package Manager config
├── SoleID/
│   ├── Sources/
│   │   ├── App/               # App entry point & navigation
│   │   ├── Features/
│   │   │   ├── Camera/        # Camera & photo picker
│   │   │   ├── Match/         # Match results display
│   │   │   ├── Search/        # Search & browse sneakers
│   │   │   └── Settings/      # App settings
│   │   ├── Services/          # API & network layer
│   │   ├── Models/            # Data models
│   │   ├── Debug/             # Logging & crash reporting
│   │   └── Common/            # Shared utilities
│   └── Resources/
│       ├── Info.plist
│       └── GoogleService-Info.plist (add this)
└── README.md
```

## Features

- **Camera Scanning**: Capture sneaker photos for identification
- **Photo Library**: Select images from gallery
- **Search**: Browse and search sneaker database
- **Price Tracking**: View market prices from eBay
- **Remote Debugging**: Logs uploaded to backend for debugging
- **Crashlytics**: Crash reports via Firebase

## API Configuration

The app connects to the SoleID backend. Configure the API URL in Settings or edit the default in `AppState.swift`:

```swift
self.apiBaseURL = "http://YOUR_SERVER_IP:8000/api/"
```

## Remote Debugging

Same as Android, logs are automatically:
1. Written to local files (NDJSON format)
2. Uploaded to backend periodically
3. Sent to Firebase Crashlytics

View logs at:
- Backend: `http://YOUR_SERVER/api/debug/devices`
- Firebase Console: Crashlytics dashboard

## Dependencies

- **Firebase SDK** - Analytics, Crashlytics, Auth, Storage
- **SwiftUI** - Modern declarative UI
- **AVFoundation** - Camera access
- **PhotosUI** - Photo picker

## Matching Android Features

| Feature | Android | iOS |
|---------|---------|-----|
| Camera | CameraX | AVFoundation |
| Photo Picker | ActivityResultContracts | PHPickerViewController |
| UI Framework | Jetpack Compose | SwiftUI |
| Networking | Retrofit/OkHttp | URLSession |
| Local Storage | Room | FileManager/UserDefaults |
| DI | Hilt | Manual/Swift native |
| Crash Reporting | Firebase Crashlytics | Firebase Crashlytics |
| Remote Logging | Custom + WorkManager | Custom + BGTaskScheduler |

## Building for Release

1. Configure signing in Xcode
2. Archive (Product → Archive)
3. Distribute via App Store Connect or TestFlight
