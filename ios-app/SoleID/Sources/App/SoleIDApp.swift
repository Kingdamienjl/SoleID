import SwiftUI
import FirebaseCore
import FirebaseCrashlytics
import FirebasePerformance
import GoogleSignIn

@main
struct SoleIDApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var authService = AuthService.shared

    init() {
        // Configure Firebase
        FirebaseApp.configure()

        // Enable Crashlytics
        Crashlytics.crashlytics().setCrashlyticsCollectionEnabled(true)

        // Set custom keys for better crash context
        let crashlytics = Crashlytics.crashlytics()
        crashlytics.setCustomValue(Bundle.main.appVersion, forKey: "app_version")
        crashlytics.setCustomValue(Bundle.main.buildNumber, forKey: "build_number")
        crashlytics.setCustomValue(UIDevice.current.model, forKey: "device_model")
        crashlytics.setCustomValue(UIDevice.current.systemVersion, forKey: "ios_version")

        // Enable Performance Monitoring
        Performance.sharedInstance().isDataCollectionEnabled = true

        // Initialize remote logger
        RemoteLogger.shared.initialize()
        RemoteLogger.shared.log(tag: "App", level: .info, message: "SoleID iOS started")

        print("SoleID iOS initialized")
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .environmentObject(authService)
                .preferredColorScheme(.dark)
                .onAppear {
                    // Upload any pending logs on app launch
                    Task {
                        await RemoteLogger.shared.uploadPendingLogs()
                    }
                }
                .onOpenURL { url in
                    // Handle Google Sign-In callback URL
                    GIDSignIn.sharedInstance.handle(url)
                }
        }
    }
}

// MARK: - Root View (handles auth state)

struct RootView: View {
    @EnvironmentObject var authService: AuthService

    var body: some View {
        Group {
            switch authService.authState {
            case .unknown:
                // Loading state
                ZStack {
                    Color(hex: "0D0D0D").ignoresSafeArea()
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: Color(hex: "FF6B35")))
                        .scaleEffect(1.5)
                }
            case .unauthenticated:
                LoginView()
            case .authenticated:
                ContentView()
            }
        }
        .animation(.easeInOut, value: authService.authState.isAuthenticated)
    }
}

// Helper for animation
extension AuthState {
    var isAuthenticated: Bool {
        if case .authenticated = self { return true }
        return false
    }
}

// MARK: - App State
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var selectedTab: Tab = .camera
    @Published var apiBaseURL: String {
        didSet {
            UserDefaults.standard.set(apiBaseURL, forKey: "api_base_url")
        }
    }

    enum Tab {
        case camera
        case search
        case collection
        case settings
    }

    init() {
        // Load saved API URL or use default
        self.apiBaseURL = UserDefaults.standard.string(forKey: "api_base_url")
            ?? "http://192.168.1.221:8000/api/"
    }
}

// MARK: - Bundle Extensions
extension Bundle {
    var appVersion: String {
        infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }

    var buildNumber: String {
        infoDictionary?["CFBundleVersion"] as? String ?? "1"
    }
}
