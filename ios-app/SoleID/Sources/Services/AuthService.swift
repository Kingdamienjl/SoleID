import Foundation
import FirebaseAuth
import FirebaseCore
import GoogleSignIn
import GoogleSignInSwift

/// User model for authenticated users
struct AuthUser: Identifiable {
    let id: String
    let email: String?
    let displayName: String?
    let photoURL: URL?
    let isAnonymous: Bool

    init(firebaseUser: FirebaseAuth.User) {
        self.id = firebaseUser.uid
        self.email = firebaseUser.email
        self.displayName = firebaseUser.displayName
        self.photoURL = firebaseUser.photoURL
        self.isAnonymous = firebaseUser.isAnonymous
    }
}

/// Authentication state
enum AuthState {
    case unknown
    case authenticated(AuthUser)
    case unauthenticated
}

/// Authentication service handling Firebase Auth and Google Sign-In
@MainActor
class AuthService: ObservableObject {
    static let shared = AuthService()

    @Published var authState: AuthState = .unknown
    @Published var isLoading = false
    @Published var errorMessage: String?

    private var authStateListener: AuthStateDidChangeListenerHandle?

    var currentUser: AuthUser? {
        if case .authenticated(let user) = authState {
            return user
        }
        return nil
    }

    var isAuthenticated: Bool {
        if case .authenticated = authState {
            return true
        }
        return false
    }

    private init() {
        setupAuthStateListener()
    }

    deinit {
        if let listener = authStateListener {
            Auth.auth().removeStateDidChangeListener(listener)
        }
    }

    // MARK: - Auth State Listener

    private func setupAuthStateListener() {
        authStateListener = Auth.auth().addStateDidChangeListener { [weak self] _, user in
            Task { @MainActor in
                if let user = user {
                    self?.authState = .authenticated(AuthUser(firebaseUser: user))
                    RemoteLogger.shared.log(tag: "Auth", level: .info, message: "User authenticated: \(user.uid)")
                } else {
                    self?.authState = .unauthenticated
                    RemoteLogger.shared.log(tag: "Auth", level: .info, message: "User signed out")
                }
            }
        }
    }

    // MARK: - Google Sign-In

    func signInWithGoogle() async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        guard let clientID = FirebaseApp.app()?.options.clientID else {
            errorMessage = "Firebase not configured properly"
            throw AuthError.configurationError
        }

        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootViewController = windowScene.windows.first?.rootViewController else {
            errorMessage = "Unable to get root view controller"
            throw AuthError.presentationError
        }

        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config

        do {
            let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootViewController)

            guard let idToken = result.user.idToken?.tokenString else {
                errorMessage = "Failed to get ID token from Google"
                throw AuthError.tokenError
            }

            let accessToken = result.user.accessToken.tokenString
            let credential = GoogleAuthProvider.credential(
                withIDToken: idToken,
                accessToken: accessToken
            )

            let authResult = try await Auth.auth().signIn(with: credential)
            RemoteLogger.shared.log(
                tag: "Auth",
                level: .info,
                message: "Google Sign-In successful for: \(authResult.user.email ?? "unknown")"
            )

        } catch let error as GIDSignInError {
            switch error.code {
            case .canceled:
                errorMessage = "Sign-in was cancelled"
            case .EMM:
                errorMessage = "Enterprise mobility management error"
            case .hasNoAuthInKeychain:
                errorMessage = "No previous sign-in found"
            case .scopesAlreadyGranted:
                // Not really an error
                break
            default:
                errorMessage = error.localizedDescription
            }
            throw error
        } catch {
            errorMessage = error.localizedDescription
            RemoteLogger.shared.log(tag: "Auth", level: .error, message: "Google Sign-In failed: \(error)")
            throw error
        }
    }

    // MARK: - Email/Password Sign-In

    func signInWithEmail(email: String, password: String) async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        do {
            let result = try await Auth.auth().signIn(withEmail: email, password: password)
            RemoteLogger.shared.log(
                tag: "Auth",
                level: .info,
                message: "Email Sign-In successful for: \(result.user.email ?? "unknown")"
            )
        } catch {
            errorMessage = mapFirebaseError(error)
            RemoteLogger.shared.log(tag: "Auth", level: .error, message: "Email Sign-In failed: \(error)")
            throw error
        }
    }

    // MARK: - Email/Password Registration

    func registerWithEmail(email: String, password: String, displayName: String?) async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        do {
            let result = try await Auth.auth().createUser(withEmail: email, password: password)

            // Update display name if provided
            if let displayName = displayName, !displayName.isEmpty {
                let changeRequest = result.user.createProfileChangeRequest()
                changeRequest.displayName = displayName
                try await changeRequest.commitChanges()
            }

            RemoteLogger.shared.log(
                tag: "Auth",
                level: .info,
                message: "Registration successful for: \(result.user.email ?? "unknown")"
            )
        } catch {
            errorMessage = mapFirebaseError(error)
            RemoteLogger.shared.log(tag: "Auth", level: .error, message: "Registration failed: \(error)")
            throw error
        }
    }

    // MARK: - Password Reset

    func resetPassword(email: String) async throws {
        isLoading = true
        errorMessage = nil

        defer { isLoading = false }

        do {
            try await Auth.auth().sendPasswordReset(withEmail: email)
            RemoteLogger.shared.log(tag: "Auth", level: .info, message: "Password reset email sent to: \(email)")
        } catch {
            errorMessage = mapFirebaseError(error)
            throw error
        }
    }

    // MARK: - Sign Out

    func signOut() throws {
        do {
            try Auth.auth().signOut()
            GIDSignIn.sharedInstance.signOut()
            RemoteLogger.shared.log(tag: "Auth", level: .info, message: "User signed out")
        } catch {
            errorMessage = "Failed to sign out"
            throw error
        }
    }

    // MARK: - Helper Methods

    private func mapFirebaseError(_ error: Error) -> String {
        let nsError = error as NSError

        switch nsError.code {
        case AuthErrorCode.invalidEmail.rawValue:
            return "Invalid email address"
        case AuthErrorCode.wrongPassword.rawValue:
            return "Incorrect password"
        case AuthErrorCode.userNotFound.rawValue:
            return "No account found with this email"
        case AuthErrorCode.emailAlreadyInUse.rawValue:
            return "This email is already registered"
        case AuthErrorCode.weakPassword.rawValue:
            return "Password is too weak"
        case AuthErrorCode.networkError.rawValue:
            return "Network error. Please check your connection"
        case AuthErrorCode.tooManyRequests.rawValue:
            return "Too many attempts. Please try again later"
        default:
            return error.localizedDescription
        }
    }

    func clearError() {
        errorMessage = nil
    }
}

// MARK: - Auth Errors

enum AuthError: LocalizedError {
    case configurationError
    case presentationError
    case tokenError

    var errorDescription: String? {
        switch self {
        case .configurationError:
            return "Firebase is not configured properly"
        case .presentationError:
            return "Unable to present sign-in screen"
        case .tokenError:
            return "Failed to get authentication token"
        }
    }
}
