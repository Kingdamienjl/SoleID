import SwiftUI

struct SearchView: View {
    @StateObject private var viewModel = SearchViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search Bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    TextField("Search sneakers...", text: $viewModel.searchQuery)
                        .textFieldStyle(.plain)
                        .autocorrectionDisabled()
                        .submitLabel(.search)
                        .onSubmit {
                            Task { await viewModel.search() }
                        }
                    if !viewModel.searchQuery.isEmpty {
                        Button {
                            viewModel.searchQuery = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.gray)
                        }
                    }
                }
                .padding()
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .padding()

                // Brand Filter
                if !viewModel.brands.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            BrandChip(name: "All", isSelected: viewModel.selectedBrand == nil) {
                                viewModel.selectedBrand = nil
                                Task { await viewModel.search() }
                            }
                            ForEach(viewModel.brands, id: \.self) { brand in
                                BrandChip(name: brand, isSelected: viewModel.selectedBrand == brand) {
                                    viewModel.selectedBrand = brand
                                    Task { await viewModel.search() }
                                }
                            }
                        }
                        .padding(.horizontal)
                    }
                    .padding(.bottom, 8)
                }

                // Results
                if viewModel.isLoading {
                    Spacer()
                    ProgressView()
                    Spacer()
                } else if viewModel.searchResults.isEmpty {
                    if viewModel.searchQuery.isEmpty {
                        TrendingSection(trending: viewModel.trending)
                    } else {
                        Spacer()
                        VStack {
                            Image(systemName: "magnifyingglass")
                                .font(.system(size: 40))
                                .foregroundColor(.gray)
                            Text("No results found")
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }
                } else {
                    List(viewModel.searchResults) { result in
                        NavigationLink(destination: ShoeDetailView(shoe: result.shoe)) {
                            SearchResultRow(result: result)
                        }
                        .listRowBackground(Color(.secondarySystemBackground))
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Search")
            .task {
                await viewModel.loadInitialData()
            }
        }
    }
}

// MARK: - Brand Chip
struct BrandChip: View {
    let name: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(name)
                .font(.subheadline)
                .fontWeight(isSelected ? .semibold : .regular)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(isSelected ? Color.orange : Color(.tertiarySystemBackground))
                .foregroundColor(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
    }
}

// MARK: - Search Result Row
struct SearchResultRow: View {
    let result: SearchResult

    var body: some View {
        HStack(spacing: 12) {
            // Placeholder image
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.tertiarySystemBackground))
                    .frame(width: 60, height: 60)
                Image(systemName: "shoe.2.fill")
                    .foregroundColor(.gray)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(result.shoe.brand)
                    .font(.caption)
                    .foregroundColor(.orange)
                Text(result.shoe.model)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(result.shoe.colorway)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            if result.shoe.year != nil {
                Text("\(result.shoe.year!)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Trending Section
struct TrendingSection: View {
    let trending: [Shoe]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Trending")
                    .font(.title2)
                    .fontWeight(.bold)
                    .padding(.horizontal)

                if trending.isEmpty {
                    VStack {
                        ProgressView()
                        Text("Loading trending...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                } else {
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                        ForEach(trending) { shoe in
                            NavigationLink(destination: ShoeDetailView(shoe: shoe)) {
                                TrendingCard(shoe: shoe)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }
            .padding(.top)
        }
    }
}

struct TrendingCard: View {
    let shoe: Shoe

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color(.tertiarySystemBackground))
                    .frame(height: 120)
                Image(systemName: "shoe.2.fill")
                    .font(.system(size: 40))
                    .foregroundColor(.gray)
            }

            Text(shoe.brand)
                .font(.caption)
                .foregroundColor(.orange)
            Text(shoe.model)
                .font(.caption)
                .fontWeight(.medium)
                .lineLimit(2)
            Text(shoe.colorway)
                .font(.caption2)
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
    }
}

// MARK: - Shoe Detail View
struct ShoeDetailView: View {
    let shoe: Shoe
    @State private var priceSnapshot: PriceSnapshot?
    @State private var isLoadingPrice = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Image placeholder
                ZStack {
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color(.tertiarySystemBackground))
                        .frame(height: 250)
                    Image(systemName: "shoe.2.fill")
                        .font(.system(size: 80))
                        .foregroundColor(.gray)
                }
                .padding(.horizontal)

                // Info
                VStack(alignment: .leading, spacing: 8) {
                    Text(shoe.brand)
                        .font(.subheadline)
                        .foregroundColor(.orange)
                    Text(shoe.model)
                        .font(.title)
                        .fontWeight(.bold)
                    Text(shoe.colorway)
                        .font(.title3)
                        .foregroundColor(.secondary)

                    HStack {
                        Label(shoe.sku, systemImage: "barcode")
                        Spacer()
                        if let year = shoe.year {
                            Label("\(year)", systemImage: "calendar")
                        }
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.top, 4)
                }
                .padding(.horizontal)

                // Price Card
                PriceInfoCard(shoe: shoe, priceSnapshot: priceSnapshot, isLoading: isLoadingPrice)
                    .padding(.horizontal)

                // Aliases
                if !shoe.aliases.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Also Known As")
                            .font(.headline)
                        FlowLayout(spacing: 8) {
                            ForEach(shoe.aliases, id: \.self) { alias in
                                Text(alias)
                                    .font(.caption)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color(.tertiarySystemBackground))
                                    .clipShape(Capsule())
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }
            .padding(.vertical)
        }
        .navigationTitle("Details")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            isLoadingPrice = true
            do {
                priceSnapshot = try await APIService.shared.getPrice(sku: shoe.sku)
            } catch {
                RemoteLogger.shared.recordNonFatal(error, context: "Price fetch failed")
            }
            isLoadingPrice = false
        }
    }
}

// MARK: - Flow Layout Helper
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.width ?? 0, subviews: subviews, spacing: spacing)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x,
                                       y: bounds.minY + result.positions[index].y),
                         proposal: .unspecified)
        }
    }

    struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []

        init(in width: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var x: CGFloat = 0
            var y: CGFloat = 0
            var rowHeight: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)
                if x + size.width > width, x > 0 {
                    x = 0
                    y += rowHeight + spacing
                    rowHeight = 0
                }
                positions.append(CGPoint(x: x, y: y))
                rowHeight = max(rowHeight, size.height)
                x += size.width + spacing
            }

            size = CGSize(width: width, height: y + rowHeight)
        }
    }
}

// MARK: - Search ViewModel
@MainActor
class SearchViewModel: ObservableObject {
    @Published var searchQuery = ""
    @Published var selectedBrand: String?
    @Published var searchResults: [SearchResult] = []
    @Published var brands: [String] = []
    @Published var trending: [Shoe] = []
    @Published var isLoading = false

    func loadInitialData() async {
        do {
            async let brandsTask = APIService.shared.getBrands()
            async let trendingTask = APIService.shared.getTrending(limit: 10)

            let (brandsResponse, trendingResponse) = try await (brandsTask, trendingTask)
            brands = brandsResponse.brands
            trending = trendingResponse.shoes
        } catch {
            RemoteLogger.shared.recordNonFatal(error, context: "Initial data load failed")
        }
    }

    func search() async {
        guard !searchQuery.isEmpty else {
            searchResults = []
            return
        }

        isLoading = true
        do {
            let response = try await APIService.shared.searchSneakers(
                query: searchQuery,
                brand: selectedBrand
            )
            searchResults = response.results
        } catch {
            RemoteLogger.shared.recordNonFatal(error, context: "Search failed")
        }
        isLoading = false
    }
}

#Preview {
    SearchView()
}
