import SwiftUI

struct MatchResultView: View {
    let result: MatchResponse
    let image: UIImage?

    @State private var selectedCandidate: Candidate?
    @State private var priceSnapshot: PriceSnapshot?
    @State private var isLoadingPrice = false

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Captured Image
                if let image = image {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 200)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .shadow(radius: 4)
                }

                // Validation Status
                if let validation = result.validation {
                    ValidationStatusCard(validation: validation)
                }

                // Results
                if result.candidates.isEmpty {
                    NoResultsView()
                } else {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Matches Found")
                            .font(.headline)
                            .padding(.horizontal)

                        ForEach(result.candidates) { candidate in
                            CandidateCard(
                                candidate: candidate,
                                isSelected: selectedCandidate?.id == candidate.id
                            )
                            .onTapGesture {
                                selectCandidate(candidate)
                            }
                        }
                    }
                }

                // Price Info (when candidate selected)
                if let candidate = selectedCandidate {
                    PriceInfoCard(
                        shoe: candidate.shoe,
                        priceSnapshot: priceSnapshot,
                        isLoading: isLoadingPrice
                    )
                }
            }
            .padding()
        }
        .navigationTitle("Match Results")
        .navigationBarTitleDisplayMode(.inline)
        .background(Color(.systemBackground))
        .onAppear {
            // Auto-select top candidate
            if let first = result.candidates.first {
                selectCandidate(first)
            }
        }
    }

    private func selectCandidate(_ candidate: Candidate) {
        selectedCandidate = candidate
        Task {
            await loadPrice(for: candidate.shoe.sku)
        }
    }

    private func loadPrice(for sku: String) async {
        isLoadingPrice = true
        do {
            priceSnapshot = try await APIService.shared.getPrice(sku: sku)
        } catch {
            RemoteLogger.shared.recordNonFatal(error, context: "Price fetch failed")
        }
        isLoadingPrice = false
    }
}

// MARK: - Validation Status Card
struct ValidationStatusCard: View {
    let validation: ValidationResult

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: validation.isValid ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundColor(validation.isValid ? .green : .orange)
                Text(validation.isValid ? "Shoe Detected" : "Validation Issues")
                    .font(.headline)
                Spacer()
                Text("\(Int(validation.shoeConfidence * 100))% confidence")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            if !validation.validationErrors.isEmpty {
                ForEach(validation.validationErrors, id: \.self) { error in
                    HStack {
                        Image(systemName: "exclamationmark.circle")
                            .foregroundColor(.orange)
                            .font(.caption)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            if !validation.suggestions.isEmpty {
                Divider()
                Text("Suggestions:")
                    .font(.caption)
                    .foregroundColor(.secondary)
                ForEach(validation.suggestions, id: \.self) { suggestion in
                    HStack(alignment: .top) {
                        Image(systemName: "lightbulb.fill")
                            .foregroundColor(.yellow)
                            .font(.caption)
                        Text(suggestion)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: - Candidate Card
struct CandidateCard: View {
    let candidate: Candidate
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            // Placeholder image
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.tertiarySystemBackground))
                    .frame(width: 80, height: 80)
                Image(systemName: "shoe.2.fill")
                    .font(.title)
                    .foregroundColor(.gray)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(candidate.shoe.brand)
                    .font(.caption)
                    .foregroundColor(.orange)
                Text(candidate.shoe.model)
                    .font(.headline)
                Text(candidate.shoe.colorway)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Text("SKU: \(candidate.shoe.sku)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            VStack {
                Text("\(candidate.scorePercentage)%")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.orange)
                Text("match")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.secondarySystemBackground))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .strokeBorder(isSelected ? Color.orange : Color.clear, lineWidth: 2)
                )
        )
    }
}

// MARK: - Price Info Card
struct PriceInfoCard: View {
    let shoe: Shoe
    let priceSnapshot: PriceSnapshot?
    let isLoading: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Price Information")
                .font(.headline)

            if isLoading {
                HStack {
                    Spacer()
                    ProgressView()
                    Spacer()
                }
                .padding()
            } else if let price = priceSnapshot {
                HStack(spacing: 20) {
                    PriceItem(label: "Last Sale", value: price.lastSale)
                    PriceItem(label: "Lowest Ask", value: price.lowestAsk)
                    PriceItem(label: "Average", value: price.averagePrice)
                }

                if !price.sourceBreakdown.isEmpty {
                    Divider()
                    Text("Sources")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    ForEach(price.sourceBreakdown, id: \.source) { source in
                        HStack {
                            Text(source.source.capitalized)
                                .font(.caption)
                            Spacer()
                            if let median = source.median {
                                Text("$\(Int(median))")
                                    .font(.caption)
                                    .fontWeight(.semibold)
                            }
                            if let count = source.count {
                                Text("(\(count) listings)")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }

                Text("Updated: \(price.asOf)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            } else {
                Text("Price data unavailable")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct PriceItem: View {
    let label: String
    let value: Double?

    var body: some View {
        VStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            if let value = value {
                Text("$\(Int(value))")
                    .font(.title3)
                    .fontWeight(.semibold)
            } else {
                Text("-")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }
        }
    }
}

// MARK: - No Results View
struct NoResultsView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 50))
                .foregroundColor(.gray)
            Text("No Matches Found")
                .font(.title2)
                .foregroundColor(.primary)
            Text("Try taking another photo with better lighting or angle")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }
}

#Preview {
    NavigationStack {
        MatchResultView(
            result: MatchResponse(
                candidates: [
                    Candidate(
                        shoe: Shoe(
                            id: "1",
                            brand: "Jordan",
                            model: "Air Jordan 1 Retro High OG",
                            colorway: "Chicago",
                            sku: "555088-101",
                            year: 2015,
                            aliases: ["AJ1", "Chicago 1s"],
                            images: [],
                            sources: [],
                            lastPriceSnapshotAt: nil
                        ),
                        score: 0.92
                    )
                ],
                validation: ValidationResult(
                    isValid: true,
                    shoeConfidence: 0.85,
                    validationErrors: [],
                    suggestions: [],
                    qualityScore: 0.9
                )
            ),
            image: nil
        )
    }
}
