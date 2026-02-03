// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "SoleID",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        .library(
            name: "SoleID",
            targets: ["SoleID"]
        ),
    ],
    dependencies: [
        // Firebase
        .package(url: "https://github.com/firebase/firebase-ios-sdk.git", from: "10.0.0"),
        // Google Sign-In
        .package(url: "https://github.com/google/GoogleSignIn-iOS.git", from: "7.0.0"),
    ],
    targets: [
        .target(
            name: "SoleID",
            dependencies: [
                .product(name: "FirebaseAnalytics", package: "firebase-ios-sdk"),
                .product(name: "FirebaseCrashlytics", package: "firebase-ios-sdk"),
                .product(name: "FirebaseAuth", package: "firebase-ios-sdk"),
                .product(name: "FirebaseFirestore", package: "firebase-ios-sdk"),
                .product(name: "FirebaseStorage", package: "firebase-ios-sdk"),
                .product(name: "FirebasePerformance", package: "firebase-ios-sdk"),
                .product(name: "GoogleSignIn", package: "GoogleSignIn-iOS"),
                .product(name: "GoogleSignInSwift", package: "GoogleSignIn-iOS"),
            ],
            path: "SoleID/Sources"
        ),
        .testTarget(
            name: "SoleIDTests",
            dependencies: ["SoleID"],
            path: "SoleIDTests"
        ),
    ]
)
