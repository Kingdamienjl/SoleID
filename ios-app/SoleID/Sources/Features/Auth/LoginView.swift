import SwiftUI
import GoogleSignInSwift

struct LoginView: View {
    @StateObject private var authService = AuthService.shared
    @State private var email = ""
    @State private var password = ""
    @State private var showPassword = false
    @State private var isRegistering = false
    @State private var displayName = ""
    @State private var showForgotPassword = false

    // Theme colors matching Android
    private let darkBackground = Color(hex: "0D0D0D")
    private let darkSurface = Color(hex: "1A1A1A")
    private let accentOrange = Color(hex: "FF6B35")
    private let accentGold = Color(hex: "FFD700")
    private let textWhite = Color(hex: "FAFAFA")
    private let textGray = Color(hex: "B0B0B0")
    private let cardBackground = Color(hex: "242424")

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                colors: [darkBackground, darkSurface, Color(hex: "151515")],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            // Animated background orbs
            GeometryReader { geometry in
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [accentOrange.opacity(0.3), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 100
                        )
                    )
                    .frame(width: 200, height: 200)
                    .blur(radius: 60)
                    .offset(x: -50, y: 100)

                Circle()
                    .fill(
                        RadialGradient(
                            colors: [accentGold.opacity(0.2), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 75
                        )
                    )
                    .frame(width: 150, height: 150)
                    .blur(radius: 50)
                    .offset(x: geometry.size.width - 80, y: 200)
            }

            ScrollView {
                VStack(spacing: 24) {
                    Spacer().frame(height: 60)

                    // Logo
                    logoSection

                    Spacer().frame(height: 24)

                    // Login Card
                    loginCard

                    // Register link
                    registerLink

                    Spacer().frame(height: 24)
                }
                .padding(.horizontal, 24)
            }
        }
        .sheet(isPresented: $showForgotPassword) {
            ForgotPasswordSheet(email: email)
        }
    }

    // MARK: - Logo Section

    private var logoSection: some View {
        VStack(spacing: 8) {
            // Logo with glow
            ZStack {
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [accentOrange.opacity(0.5), .clear],
                            center: .center,
                            startRadius: 0,
                            endRadius: 70
                        )
                    )
                    .frame(width: 140, height: 140)
                    .blur(radius: 30)

                RoundedRectangle(cornerRadius: 30)
                    .fill(
                        LinearGradient(
                            colors: [cardBackground, darkSurface],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 120, height: 120)
                    .shadow(color: .black.opacity(0.5), radius: 20, x: 0, y: 10)
                    .overlay(
                        Image(systemName: "shoe.fill")
                            .font(.system(size: 50))
                            .foregroundColor(accentOrange)
                    )
            }

            Text("SOLE ID")
                .font(.system(size: 36, weight: .black))
                .tracking(6)
                .foregroundColor(textWhite)
                .shadow(color: accentOrange.opacity(0.5), radius: 10, x: 0, y: 4)

            Text("Authenticate Your Kicks")
                .font(.subheadline)
                .foregroundColor(textGray)
        }
    }

    // MARK: - Login Card

    private var loginCard: some View {
        VStack(spacing: 16) {
            Text(isRegistering ? "Create Account" : "Welcome Back")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(textWhite)

            Text(isRegistering ? "Sign up to get started" : "Sign in to continue")
                .font(.subheadline)
                .foregroundColor(textGray)
                .padding(.bottom, 8)

            // Display name field (registration only)
            if isRegistering {
                CustomTextField(
                    text: $displayName,
                    placeholder: "Display Name",
                    icon: "person.fill"
                )
            }

            // Email field
            CustomTextField(
                text: $email,
                placeholder: "Email",
                icon: "envelope.fill",
                keyboardType: .emailAddress,
                autocapitalization: .never
            )

            // Password field
            CustomSecureField(
                text: $password,
                placeholder: "Password",
                showPassword: $showPassword
            )

            // Forgot password (login only)
            if !isRegistering {
                HStack {
                    Spacer()
                    Button("Forgot Password?") {
                        showForgotPassword = true
                    }
                    .font(.footnote)
                    .foregroundColor(accentOrange)
                }
            }

            // Error message
            if let error = authService.errorMessage {
                Text(error)
                    .font(.footnote)
                    .foregroundColor(.red)
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(8)
            }

            // Sign In / Register Button
            Button(action: primaryAction) {
                if authService.isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: textWhite))
                } else {
                    Text(isRegistering ? "SIGN UP" : "SIGN IN")
                        .font(.headline)
                        .fontWeight(.bold)
                        .tracking(2)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(accentOrange)
            .foregroundColor(textWhite)
            .cornerRadius(16)
            .disabled(!isFormValid || authService.isLoading)
            .opacity(isFormValid ? 1 : 0.5)

            // Divider
            HStack {
                Rectangle()
                    .fill(textGray.opacity(0.3))
                    .frame(height: 1)
                Text("OR")
                    .font(.footnote)
                    .foregroundColor(textGray)
                Rectangle()
                    .fill(textGray.opacity(0.3))
                    .frame(height: 1)
            }
            .padding(.vertical, 8)

            // Google Sign-In Button
            Button(action: signInWithGoogle) {
                HStack {
                    Text("G")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(Color(hex: "DB4437"))
                    Text("Continue with Google")
                        .font(.headline)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(Color.clear)
            .foregroundColor(textWhite)
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(textGray.opacity(0.3), lineWidth: 1)
            )
            .cornerRadius(16)
            .disabled(authService.isLoading)
        }
        .padding(24)
        .background(cardBackground.opacity(0.9))
        .cornerRadius(24)
        .shadow(color: .black.opacity(0.3), radius: 16, x: 0, y: 8)
    }

    // MARK: - Register Link

    private var registerLink: some View {
        HStack {
            Text(isRegistering ? "Already have an account?" : "Don't have an account?")
                .foregroundColor(textGray)
            Button(isRegistering ? "Sign In" : "Sign Up") {
                withAnimation {
                    isRegistering.toggle()
                    authService.clearError()
                }
            }
            .fontWeight(.bold)
            .foregroundColor(accentOrange)
        }
        .font(.subheadline)
    }

    // MARK: - Actions

    private var isFormValid: Bool {
        let emailValid = email.contains("@") && email.contains(".")
        let passwordValid = password.count >= 6
        let nameValid = !isRegistering || !displayName.isEmpty
        return emailValid && passwordValid && nameValid
    }

    private func primaryAction() {
        authService.clearError()
        Task {
            do {
                if isRegistering {
                    try await authService.registerWithEmail(
                        email: email,
                        password: password,
                        displayName: displayName.isEmpty ? nil : displayName
                    )
                } else {
                    try await authService.signInWithEmail(email: email, password: password)
                }
            } catch {
                // Error is handled by authService
            }
        }
    }

    private func signInWithGoogle() {
        authService.clearError()
        Task {
            do {
                try await authService.signInWithGoogle()
            } catch {
                // Error is handled by authService
            }
        }
    }
}

// MARK: - Custom TextField

struct CustomTextField: View {
    @Binding var text: String
    let placeholder: String
    let icon: String
    var keyboardType: UIKeyboardType = .default
    var autocapitalization: TextInputAutocapitalization = .sentences

    private let accentOrange = Color(hex: "FF6B35")
    private let textGray = Color(hex: "B0B0B0")
    private let textWhite = Color(hex: "FAFAFA")

    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(accentOrange)
                .frame(width: 24)
            TextField(placeholder, text: $text)
                .keyboardType(keyboardType)
                .textInputAutocapitalization(autocapitalization)
                .foregroundColor(textWhite)
        }
        .padding()
        .background(Color(hex: "1A1A1A"))
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(textGray.opacity(0.3), lineWidth: 1)
        )
    }
}

// MARK: - Custom Secure Field

struct CustomSecureField: View {
    @Binding var text: String
    let placeholder: String
    @Binding var showPassword: Bool

    private let accentOrange = Color(hex: "FF6B35")
    private let textGray = Color(hex: "B0B0B0")
    private let textWhite = Color(hex: "FAFAFA")

    var body: some View {
        HStack {
            Image(systemName: "lock.fill")
                .foregroundColor(accentOrange)
                .frame(width: 24)

            if showPassword {
                TextField(placeholder, text: $text)
                    .foregroundColor(textWhite)
            } else {
                SecureField(placeholder, text: $text)
                    .foregroundColor(textWhite)
            }

            Button(action: { showPassword.toggle() }) {
                Image(systemName: showPassword ? "eye.fill" : "eye.slash.fill")
                    .foregroundColor(textGray)
            }
        }
        .padding()
        .background(Color(hex: "1A1A1A"))
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(textGray.opacity(0.3), lineWidth: 1)
        )
    }
}

// MARK: - Forgot Password Sheet

struct ForgotPasswordSheet: View {
    @Environment(\.dismiss) var dismiss
    @StateObject private var authService = AuthService.shared
    @State var email: String
    @State private var sent = false

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                Text("Reset Password")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Enter your email and we'll send you a link to reset your password.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

                TextField("Email", text: $email)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .textFieldStyle(.roundedBorder)

                if sent {
                    Text("Password reset email sent!")
                        .foregroundColor(.green)
                }

                if let error = authService.errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.footnote)
                }

                Button(action: resetPassword) {
                    if authService.isLoading {
                        ProgressView()
                    } else {
                        Text("Send Reset Link")
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color(hex: "FF6B35"))
                .foregroundColor(.white)
                .cornerRadius(12)
                .disabled(email.isEmpty || authService.isLoading)

                Spacer()
            }
            .padding()
            .navigationBarItems(trailing: Button("Done") { dismiss() })
        }
    }

    private func resetPassword() {
        Task {
            do {
                try await authService.resetPassword(email: email)
                sent = true
            } catch {
                // Error handled by authService
            }
        }
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    LoginView()
}
