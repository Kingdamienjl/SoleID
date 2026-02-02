import Foundation
import UIKit
import FirebaseCrashlytics

// MARK: - Log Level
enum LogLevel: String, Codable {
    case debug = "DEBUG"
    case info = "INFO"
    case warning = "WARN"
    case error = "ERROR"
}

// MARK: - Log Entry
struct LogEntry: Codable {
    let timestamp: Int64
    let tag: String
    let level: String
    let message: String
    let data: [String: AnyCodable]
}

// MARK: - Remote Logger
/// Handles local logging and remote upload to backend
/// Mirrors the Android RemoteLogUploader functionality
class RemoteLogger {
    static let shared = RemoteLogger()

    private let fileManager = FileManager.default
    private let logsDirectory: URL
    private let uploadedMarkersDirectory: URL
    private let dateFormatter: DateFormatter
    private let queue = DispatchQueue(label: "com.soleid.logger", qos: .utility)

    private var deviceId: String {
        UIDevice.current.identifierForVendor?.uuidString ?? "unknown"
    }

    private var baseURL: String {
        UserDefaults.standard.string(forKey: "api_base_url")
            ?? "http://192.168.1.221:8000/api/"
    }

    private init() {
        let documentsPath = fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
        logsDirectory = documentsPath.appendingPathComponent("logs", isDirectory: true)
        uploadedMarkersDirectory = documentsPath.appendingPathComponent("logs_uploaded", isDirectory: true)

        dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        dateFormatter.locale = Locale(identifier: "en_US_POSIX")

        // Create directories if needed
        try? fileManager.createDirectory(at: logsDirectory, withIntermediateDirectories: true)
        try? fileManager.createDirectory(at: uploadedMarkersDirectory, withIntermediateDirectories: true)
    }

    func initialize() {
        setupCrashlyticsContext()
        log(tag: "Logger", level: .info, message: "RemoteLogger initialized")
    }

    // MARK: - Crashlytics Context
    private func setupCrashlyticsContext() {
        let crashlytics = Crashlytics.crashlytics()
        crashlytics.setCustomValue(deviceId, forKey: "device_id")
        crashlytics.setCustomValue(Bundle.main.appVersion, forKey: "app_version")
        crashlytics.setCustomValue(Bundle.main.buildNumber, forKey: "build_number")
        crashlytics.setCustomValue(UIDevice.current.model, forKey: "device_model")
        crashlytics.setCustomValue(UIDevice.current.systemVersion, forKey: "ios_version")
        crashlytics.setCustomValue(baseURL, forKey: "api_base_url")
    }

    // MARK: - Logging
    func log(tag: String, level: LogLevel, message: String, data: [String: Any] = [:]) {
        let entry = LogEntry(
            timestamp: Int64(Date().timeIntervalSince1970 * 1000),
            tag: tag,
            level: level.rawValue,
            message: message,
            data: data.mapValues { AnyCodable($0) }
        )

        // Log to Crashlytics
        Crashlytics.crashlytics().log("[\(level.rawValue)] \(tag): \(message)")

        // Add custom keys for important data
        for (key, value) in data {
            Crashlytics.crashlytics().setCustomValue("\(value)", forKey: "\(tag).\(key)")
        }

        // Write to file
        queue.async { [weak self] in
            self?.writeToFile(entry)
        }

        // Also print for debug
        #if DEBUG
        print("[\(level.rawValue)] \(tag): \(message) \(data)")
        #endif
    }

    // MARK: - Non-Fatal Error Recording
    func recordNonFatal(_ error: Error, context: String? = nil) {
        if let context = context {
            Crashlytics.crashlytics().log("Context: \(context)")
        }
        Crashlytics.crashlytics().record(error: error)

        log(tag: "Error", level: .error, message: error.localizedDescription, data: [
            "context": context ?? "none",
            "type": String(describing: type(of: error))
        ])
    }

    // MARK: - File Writing
    private func writeToFile(_ entry: LogEntry) {
        let dateString = dateFormatter.string(from: Date())
        let fileURL = logsDirectory.appendingPathComponent("\(dateString).ndjson")

        guard let jsonData = try? JSONEncoder().encode(entry),
              var jsonString = String(data: jsonData, encoding: .utf8) else {
            return
        }
        jsonString += "\n"

        if fileManager.fileExists(atPath: fileURL.path) {
            if let handle = try? FileHandle(forWritingTo: fileURL) {
                handle.seekToEndOfFile()
                handle.write(jsonString.data(using: .utf8)!)
                handle.closeFile()
            }
        } else {
            try? jsonString.write(to: fileURL, atomically: true, encoding: .utf8)
        }
    }

    // MARK: - Upload Pending Logs
    func uploadPendingLogs() async {
        guard let files = try? fileManager.contentsOfDirectory(at: logsDirectory, includingPropertiesForKeys: nil) else {
            return
        }

        let logFiles = files.filter { $0.pathExtension == "ndjson" && !isAlreadyUploaded($0) }

        for file in logFiles {
            do {
                try await uploadLogFile(file)
                markAsUploaded(file)
            } catch {
                print("Failed to upload \(file.lastPathComponent): \(error)")
            }
        }

        // Cleanup old logs
        cleanupOldLogs()
    }

    private func uploadLogFile(_ file: URL) async throws {
        guard let content = try? String(contentsOf: file, encoding: .utf8) else {
            return
        }

        let lines = content.components(separatedBy: .newlines).filter { !$0.isEmpty }
        if lines.isEmpty { return }

        // Parse entries
        let entries = lines.compactMap { line -> [String: Any]? in
            guard let data = line.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return nil
            }
            return json
        }

        // Build payload
        let payload: [String: Any] = [
            "device_id": deviceId,
            "device_model": UIDevice.current.model,
            "device_manufacturer": "Apple",
            "android_version": UIDevice.current.systemVersion, // iOS version for compatibility
            "sdk_int": 0, // Not applicable for iOS
            "app_version": Bundle.main.appVersion,
            "app_version_code": Int(Bundle.main.buildNumber) ?? 1,
            "log_file": file.lastPathComponent,
            "entries": entries,
            "uploaded_at": Int64(Date().timeIntervalSince1970 * 1000)
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: payload) else {
            throw LogUploadError.serializationFailed
        }

        var request = URLRequest(url: URL(string: "\(baseURL)debug/logs")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceId, forHTTPHeaderField: "X-Device-ID")
        request.setValue(Bundle.main.appVersion, forHTTPHeaderField: "X-App-Version")
        request.setValue("iOS", forHTTPHeaderField: "X-Platform")
        request.httpBody = jsonData

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw LogUploadError.uploadFailed
        }

        print("Uploaded \(file.lastPathComponent) successfully")
    }

    private func isAlreadyUploaded(_ file: URL) -> Bool {
        let markerFile = uploadedMarkersDirectory.appendingPathComponent("\(file.lastPathComponent).uploaded")
        return fileManager.fileExists(atPath: markerFile.path)
    }

    private func markAsUploaded(_ file: URL) {
        let markerFile = uploadedMarkersDirectory.appendingPathComponent("\(file.lastPathComponent).uploaded")
        fileManager.createFile(atPath: markerFile.path, contents: nil)
    }

    private func cleanupOldLogs() {
        let sevenDaysAgo = Date().addingTimeInterval(-7 * 24 * 60 * 60)

        for directory in [logsDirectory, uploadedMarkersDirectory] {
            guard let files = try? fileManager.contentsOfDirectory(at: directory, includingPropertiesForKeys: [.contentModificationDateKey]) else {
                continue
            }

            for file in files {
                guard let attrs = try? fileManager.attributesOfItem(atPath: file.path),
                      let modDate = attrs[.modificationDate] as? Date,
                      modDate < sevenDaysAgo else {
                    continue
                }
                try? fileManager.removeItem(at: file)
            }
        }
    }

    // MARK: - Device Info
    func getDeviceInfo() -> [String: String] {
        [
            "device_id": deviceId,
            "model": UIDevice.current.model,
            "manufacturer": "Apple",
            "ios_version": UIDevice.current.systemVersion,
            "app_version": Bundle.main.appVersion,
            "build_number": Bundle.main.buildNumber
        ]
    }
}

// MARK: - Errors
enum LogUploadError: Error {
    case serializationFailed
    case uploadFailed
}

// MARK: - AnyCodable Helper
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else {
            value = ""
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        } else {
            try container.encode("\(value)")
        }
    }
}
