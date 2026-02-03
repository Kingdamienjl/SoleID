import Foundation

// MARK: - Shoe Model
struct Shoe: Codable, Identifiable, Hashable {
    let id: String
    let brand: String
    let model: String
    let colorway: String
    let sku: String
    let year: Int?
    let aliases: [String]
    let images: [String]
    let sources: [SourceRef]
    let lastPriceSnapshotAt: String?

    var displayName: String {
        "\(brand) \(model)"
    }

    var fullName: String {
        "\(brand) \(model) \(colorway)"
    }
}

struct SourceRef: Codable, Hashable {
    let name: String
    let url: String
}

// MARK: - Match Response
struct MatchResponse: Codable {
    let candidates: [Candidate]
    let validation: ValidationResult?
}

struct Candidate: Codable, Identifiable {
    var id: String { shoe.id }
    let shoe: Shoe
    let score: Double

    var scorePercentage: Int {
        Int(score * 100)
    }
}

// MARK: - Validation Result
struct ValidationResult: Codable {
    let isValid: Bool
    let shoeConfidence: Double
    let validationErrors: [String]
    let suggestions: [String]
    let qualityScore: Double?
}

// MARK: - Search Response
struct SearchResponse: Codable {
    let results: [SearchResult]
    let total: Int
    let query: String
    let filters: [String: String]
}

struct SearchResult: Codable, Identifiable {
    var id: String { shoe.id }
    let shoe: Shoe
    let score: Double
}

// MARK: - Brands Response
struct BrandsResponse: Codable {
    let brands: [String]
    let total: Int
}

// MARK: - Trending Response
struct TrendingResponse: Codable {
    let shoes: [Shoe]
    let total: Int
}

// MARK: - Price Snapshot
struct PriceSnapshot: Codable {
    let sku: String
    let asOf: String
    let retail: Double?
    let lowestAsk: Double?
    let highestBid: Double?
    let lastSale: Double?
    let averagePrice: Double?
    let sourceBreakdown: [SourceBreakdown]
}

struct SourceBreakdown: Codable {
    let source: String
    let median: Double?
    let count: Int?
    let lowest: Double?
    let highest: Double?
}
