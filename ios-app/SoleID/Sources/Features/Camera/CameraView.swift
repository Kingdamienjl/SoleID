import SwiftUI
import PhotosUI
import AVFoundation

struct CameraView: View {
    @StateObject private var viewModel = CameraViewModel()
    @State private var showingImagePicker = false
    @State private var showingCamera = false
    @State private var navigateToMatch = false

    var body: some View {
        NavigationStack {
            ZStack {
                // Background
                Color.black.ignoresSafeArea()

                VStack(spacing: 0) {
                    // Camera Preview or Placeholder
                    ZStack {
                        if viewModel.isCameraAvailable {
                            CameraPreviewView(session: viewModel.session)
                                .ignoresSafeArea()
                        } else {
                            VStack {
                                Image(systemName: "camera.fill")
                                    .font(.system(size: 60))
                                    .foregroundColor(.gray)
                                Text("Camera not available")
                                    .foregroundColor(.gray)
                            }
                        }

                        // Loading Overlay
                        if viewModel.isProcessing {
                            Color.black.opacity(0.6)
                            VStack {
                                ProgressView()
                                    .scaleEffect(1.5)
                                    .tint(.white)
                                Text("Analyzing sneaker...")
                                    .foregroundColor(.white)
                                    .padding(.top, 16)
                            }
                        }
                    }

                    // Control Bar
                    HStack(spacing: 40) {
                        // Gallery Button
                        Button {
                            showingImagePicker = true
                        } label: {
                            Image(systemName: "photo.on.rectangle")
                                .font(.title)
                                .foregroundColor(.white)
                                .frame(width: 60, height: 60)
                                .background(Color.gray.opacity(0.3))
                                .clipShape(Circle())
                        }

                        // Capture Button
                        Button {
                            Task {
                                await viewModel.capturePhoto()
                            }
                        } label: {
                            ZStack {
                                Circle()
                                    .strokeBorder(.white, lineWidth: 4)
                                    .frame(width: 80, height: 80)
                                Circle()
                                    .fill(.white)
                                    .frame(width: 65, height: 65)
                            }
                        }
                        .disabled(!viewModel.isCameraAvailable || viewModel.isProcessing)

                        // Placeholder for symmetry
                        Color.clear
                            .frame(width: 60, height: 60)
                    }
                    .padding(.vertical, 30)
                    .background(Color.black.opacity(0.8))
                }
            }
            .navigationTitle("Scan Sneaker")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarBackground(Color.black.opacity(0.8), for: .navigationBar)
            .sheet(isPresented: $showingImagePicker) {
                ImagePicker(image: $viewModel.selectedImage)
            }
            .onChange(of: viewModel.selectedImage) { _, newImage in
                if newImage != nil {
                    Task {
                        await viewModel.processSelectedImage()
                    }
                }
            }
            .navigationDestination(isPresented: $viewModel.showMatchResult) {
                if let result = viewModel.matchResult {
                    MatchResultView(result: result, image: viewModel.capturedImage)
                }
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text(viewModel.errorMessage)
            }
            .onAppear {
                viewModel.checkPermissions()
            }
        }
    }
}

// MARK: - Camera Preview
struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)

        DispatchQueue.main.async {
            previewLayer.frame = view.bounds
        }

        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        if let layer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            layer.frame = uiView.bounds
        }
    }
}

// MARK: - Image Picker
struct ImagePicker: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    @Environment(\.dismiss) var dismiss

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.filter = .images
        config.selectionLimit = 1

        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let parent: ImagePicker

        init(_ parent: ImagePicker) {
            self.parent = parent
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            parent.dismiss()

            guard let result = results.first else { return }

            result.itemProvider.loadObject(ofClass: UIImage.self) { [weak self] object, error in
                if let image = object as? UIImage {
                    DispatchQueue.main.async {
                        self?.parent.image = image
                    }
                }
            }
        }
    }
}

// MARK: - Camera ViewModel
@MainActor
class CameraViewModel: ObservableObject {
    @Published var isCameraAvailable = false
    @Published var isProcessing = false
    @Published var selectedImage: UIImage?
    @Published var capturedImage: UIImage?
    @Published var matchResult: MatchResponse?
    @Published var showMatchResult = false
    @Published var showError = false
    @Published var errorMessage = ""

    let session = AVCaptureSession()
    private var photoOutput: AVCapturePhotoOutput?

    func checkPermissions() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            setupCamera()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                if granted {
                    DispatchQueue.main.async {
                        self?.setupCamera()
                    }
                }
            }
        default:
            isCameraAvailable = false
        }
    }

    private func setupCamera() {
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            isCameraAvailable = false
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            if session.canAddInput(input) {
                session.addInput(input)
            }

            let output = AVCapturePhotoOutput()
            if session.canAddOutput(output) {
                session.addOutput(output)
                photoOutput = output
            }

            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                self?.session.startRunning()
            }

            isCameraAvailable = true
            RemoteLogger.shared.log(tag: "Camera", level: .info, message: "Camera setup complete")
        } catch {
            isCameraAvailable = false
            RemoteLogger.shared.recordNonFatal(error, context: "Camera setup failed")
        }
    }

    func capturePhoto() async {
        guard let photoOutput = photoOutput else { return }

        isProcessing = true
        RemoteLogger.shared.log(tag: "Camera", level: .info, message: "Capturing photo")

        let settings = AVCapturePhotoSettings()
        let delegate = PhotoCaptureDelegate { [weak self] image in
            Task { @MainActor in
                self?.capturedImage = image
                await self?.processImage(image)
            }
        }

        photoOutput.capturePhoto(with: settings, delegate: delegate)
    }

    func processSelectedImage() async {
        guard let image = selectedImage else { return }
        capturedImage = image
        await processImage(image)
    }

    private func processImage(_ image: UIImage?) async {
        guard let image = image else {
            isProcessing = false
            return
        }

        do {
            RemoteLogger.shared.log(tag: "Match", level: .info, message: "Sending image for matching")
            let result = try await APIService.shared.matchImage(image)
            matchResult = result
            showMatchResult = true
            RemoteLogger.shared.log(tag: "Match", level: .info, message: "Match complete", data: ["candidates": result.candidates.count])
        } catch {
            errorMessage = error.localizedDescription
            showError = true
            RemoteLogger.shared.recordNonFatal(error, context: "Image matching failed")
        }

        isProcessing = false
        selectedImage = nil
    }
}

// MARK: - Photo Capture Delegate
class PhotoCaptureDelegate: NSObject, AVCapturePhotoCaptureDelegate {
    private let completion: (UIImage?) -> Void

    init(completion: @escaping (UIImage?) -> Void) {
        self.completion = completion
    }

    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        if let error = error {
            RemoteLogger.shared.recordNonFatal(error, context: "Photo capture failed")
            completion(nil)
            return
        }

        guard let data = photo.fileDataRepresentation(),
              let image = UIImage(data: data) else {
            completion(nil)
            return
        }

        completion(image)
    }
}

#Preview {
    CameraView()
}
