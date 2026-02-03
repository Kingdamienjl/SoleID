import Foundation
import UIKit

// MARK: - API Service
actor APIService {
    static let shared = APIService()

    private var baseURL: String {
        UserDefaults.standard.string(forKey: "api_base_url")
            ?? "http://192.168.1.221:8000/api/"
    }

    private let session: URLSession

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    // MARK: - Match Image
    func matchImage(_ image: UIImage) async throws -> MatchResponse {
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw APIError.imageEncodingFailed
        }

        let url = URL(string: "\(baseURL)match")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"sneaker.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        RemoteLogger.shared.log(tag: "API", level: .info, message: "Matching image", data: ["size": imageData.count])

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        if httpResponse.statusCode != 200 {
            RemoteLogger.shared.log(tag: "API", level: .error, message: "Match failed", data: ["status": httpResponse.statusCode])
            throw APIError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(MatchResponse.self, from: data)
    }

    // MARK: - Search Sneakers
    func searchSneakers(query: String, brand: String? = nil, limit: Int = 20) async throws -> SearchResponse {
        var urlComponents = URLComponents(string: "\(baseURL)search")!
        urlComponents.queryItems = [
            URLQueryItem(name: "q", value: query),
            URLQueryItem(name: "limit", value: String(limit))
        ]
        if let brand = brand {
            urlComponents.queryItems?.append(URLQueryItem(name: "brand", value: brand))
        }

        let (data, response) = try await session.data(from: urlComponents.url!)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(SearchResponse.self, from: data)
    }

    // MARK: - Get Brands
    func getBrands() async throws -> BrandsResponse {
        let url = URL(string: "\(baseURL)brands")!
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        let decoder = JSONDecoder()
        return try decoder.decode(BrandsResponse.self, from: data)
    }

    // MARK: - Get Trending
    func getTrending(limit: Int = 10) async throws -> TrendingResponse {
        var urlComponents = URLComponents(string: "\(baseURL)sneakers/trending")!
        urlComponents.queryItems = [URLQueryItem(name: "limit", value: String(limit))]

        let (data, response) = try await session.data(from: urlComponents.url!)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(TrendingResponse.self, from: data)
    }

    // MARK: - Get Price
    func getPrice(sku: String) async throws -> PriceSnapshot {
        let url = URL(string: "\(baseURL)prices/\(sku)")!
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(PriceSnapshot.self, from: data)
    }

    // MARK: - Validate Image
    func validateImage(_ image: UIImage) async throws -> ValidationResult {
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw APIError.imageEncodingFailed
        }

        let url = URL(string: "\(baseURL)validate")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"sneaker.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ValidationResult.self, from: data)
    }
}

// MARK: - API Errors
enum APIError: Error, LocalizedError {
    case imageEncodingFailed
    case invalidResponse
    case httpError(Int)
    case decodingFailed

    var errorDescription: String? {
        switch self {
        case .imageEncodingFailed:
            return "Failed to encode image"
        case .invalidResponse:
            return "Invalid server response"
        case .httpError(let code):
            return "Server error: \(code)"
        case .decodingFailed:
            return "Failed to decode response"
        }
    }
}
