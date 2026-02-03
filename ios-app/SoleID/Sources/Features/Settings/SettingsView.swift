import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var authService: AuthService
    @State private var apiURL: String = ""
    @State private var showDeviceInfo = false
    @State private var showSignOutAlert = false

    var body: some View {
        NavigationStack {
            List {
                // Account Section
                Section("Account") {
                    if let user = authService.currentUser {
                        HStack {
                            // User avatar
                            if let photoURL = user.photoURL {
                                AsyncImage(url: photoURL) { image in
                                    image
                                        .resizable()
                                        .scaledToFill()
                                } placeholder: {
                                    Image(systemName: "person.circle.fill")
                                        .resizable()
                                        .foregroundColor(.secondary)
                                }
                                .frame(width: 50, height: 50)
                                .clipShape(Circle())
                            } else {
                                Image(systemName: "person.circle.fill")
                                    .resizable()
                                    .foregroundColor(Color(hex: "FF6B35"))
                                    .frame(width: 50, height: 50)
                            }

                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.displayName ?? "User")
                                    .font(.headline)
                                if let email = user.email {
                                    Text(email)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .padding(.vertical, 4)

                        Button(role: .destructive) {
                            showSignOutAlert = true
                        } label: {
                            HStack {
                                Image(systemName: "rectangle.portrait.and.arrow.right")
                                Text("Sign Out")
                            }
                        }
                    }
                }

                // Server Settings
                Section {
                    HStack {
                        Text("API Server")
                        Spacer()
                        TextField("URL", text: $apiURL)
                            .textFieldStyle(.roundedBorder)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                            .frame(width: 200)
                    }

                    Button("Save & Test Connection") {
                        appState.apiBaseURL = apiURL
                        testConnection()
                    }
                } header: {
                    Text("Server")
                } footer: {
                    Text("Enter the base URL of your SoleID backend server")
                }

                // Debug Section
                Section("Debug") {
                    Button("Upload Logs Now") {
                        Task {
                            await RemoteLogger.shared.uploadPendingLogs()
                        }
                    }

                    Button("View Device Info") {
                        showDeviceInfo = true
                    }

                    Button("Test Crash Reporting") {
                        // Record a non-fatal for testing
                        RemoteLogger.shared.recordNonFatal(
                            NSError(domain: "TestError", code: 1, userInfo: [NSLocalizedDescriptionKey: "Test error for crash reporting"]),
                            context: "Manual test from settings"
                        )
                    }
                }

                // App Info
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("\(Bundle.main.appVersion) (\(Bundle.main.buildNumber))")
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Text("Platform")
                        Spacer()
                        Text("iOS \(UIDevice.current.systemVersion)")
                            .foregroundColor(.secondary)
                    }

                    Link(destination: URL(string: "https://github.com/soleid/app")!) {
                        HStack {
                            Text("Source Code")
                            Spacer()
                            Image(systemName: "arrow.up.right.square")
                                .foregroundColor(.secondary)
                        }
                    }
                }

                // Legal
                Section("Legal") {
                    NavigationLink("Privacy Policy") {
                        Text("Privacy Policy content here")
                            .navigationTitle("Privacy Policy")
                    }
                    NavigationLink("Terms of Service") {
                        Text("Terms of Service content here")
                            .navigationTitle("Terms of Service")
                    }
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                apiURL = appState.apiBaseURL
            }
            .sheet(isPresented: $showDeviceInfo) {
                DeviceInfoSheet()
            }
            .alert("Sign Out", isPresented: $showSignOutAlert) {
                Button("Cancel", role: .cancel) { }
                Button("Sign Out", role: .destructive) {
                    do {
                        try authService.signOut()
                    } catch {
                        RemoteLogger.shared.log(tag: "Settings", level: .error, message: "Sign out failed: \(error)")
                    }
                }
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
    }

    private func testConnection() {
        Task {
            do {
                _ = try await APIService.shared.getBrands()
                // Show success somehow
                RemoteLogger.shared.log(tag: "Settings", level: .info, message: "Connection test successful")
            } catch {
                RemoteLogger.shared.recordNonFatal(error, context: "Connection test failed")
            }
        }
    }
}

// MARK: - Device Info Sheet
struct DeviceInfoSheet: View {
    @Environment(\.dismiss) var dismiss
    private let deviceInfo = RemoteLogger.shared.getDeviceInfo()

    var body: some View {
        NavigationStack {
            List {
                ForEach(Array(deviceInfo.keys.sorted()), id: \.self) { key in
                    HStack {
                        Text(key.replacingOccurrences(of: "_", with: " ").capitalized)
                        Spacer()
                        Text(deviceInfo[key] ?? "-")
                            .foregroundColor(.secondary)
                            .font(.system(.body, design: .monospaced))
                    }
                }
            }
            .navigationTitle("Device Info")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
        .environmentObject(AuthService.shared)
}
