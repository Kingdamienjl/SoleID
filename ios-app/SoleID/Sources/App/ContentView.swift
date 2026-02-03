import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            // Camera Tab
            CameraView()
                .tabItem {
                    Label("Scan", systemImage: "camera.fill")
                }
                .tag(0)

            // Search Tab
            SearchView()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .tag(1)

            // Collection Tab
            CollectionView()
                .tabItem {
                    Label("Collection", systemImage: "square.grid.2x2.fill")
                }
                .tag(2)

            // Settings Tab
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
                .tag(3)
        }
        .tint(.orange)
    }
}

// MARK: - Placeholder Views (to be implemented)

struct CollectionView: View {
    var body: some View {
        NavigationStack {
            VStack {
                Image(systemName: "shoe.2.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.gray)
                Text("Your Collection")
                    .font(.title2)
                    .foregroundColor(.gray)
                Text("Saved sneakers will appear here")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Collection")
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
