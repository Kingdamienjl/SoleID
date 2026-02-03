#!/usr/bin/env python3
"""
TFLite Sneaker Recognition Model Training

Creates a TensorFlow Lite model for sneaker brand/model recognition
using transfer learning from MobileNetV2.

Usage:
    python scripts/train_tflite_model.py --data-dir ../sneaker-scraper/data/scraped_images

Output:
    - sneaker_model.tflite (quantized model for mobile)
    - sneaker_labels.txt (class labels)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Check for TensorFlow
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
except ImportError:
    print("TensorFlow not found. Install with: pip install tensorflow")
    sys.exit(1)

import numpy as np

# Constants
IMG_SIZE = 224  # MobileNetV2 input size
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001


def prepare_dataset(data_dir: Path) -> Tuple[tf.data.Dataset, tf.data.Dataset, List[str]]:
    """
    Prepare training and validation datasets from image directory.

    Expected structure:
        data_dir/
            Brand_Model_Colorway/
                image1.jpg
                image2.jpg
            ...
    """
    print(f"Loading images from: {data_dir}")

    # Count total images first
    total_images = sum(1 for _ in data_dir.rglob("*.jpg"))
    print(f"Total images found: {total_images}")

    # Use smaller validation split for small datasets
    val_split = 0.1 if total_images < 500 else 0.2

    # Use ImageDataGenerator for augmentation
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest',
        validation_split=val_split
    )

    # Training data
    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training',
        shuffle=True
    )

    # Validation data
    val_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation',
        shuffle=False
    )

    # Get class names
    class_names = list(train_generator.class_indices.keys())
    print(f"Found {len(class_names)} classes")
    print(f"Training samples: {train_generator.samples}")
    print(f"Validation samples: {val_generator.samples}")

    # If still no validation samples, use training data for validation
    if val_generator.samples == 0:
        print("Warning: No validation samples. Using training data for validation.")
        val_generator = train_generator

    return train_generator, val_generator, class_names


def create_model(num_classes: int) -> keras.Model:
    """
    Create a transfer learning model based on MobileNetV2.
    """
    print(f"Creating model for {num_classes} classes...")

    # Load MobileNetV2 without top layers
    base_model = MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights='imagenet'
    )

    # Freeze base model layers
    base_model.trainable = False

    # Build model
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dropout(0.3),
        layers.Dense(256, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    model.summary()
    return model


def train_model(model: keras.Model, train_gen, val_gen, epochs: int = EPOCHS) -> keras.Model:
    """
    Train the model with early stopping.
    """
    print(f"\nTraining for {epochs} epochs...")

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=3,
            restore_best_weights=True
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=2,
            min_lr=1e-6
        )
    ]

    history = model.fit(
        train_gen,
        epochs=epochs,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )

    # Print final metrics
    final_acc = history.history['accuracy'][-1]
    final_val_acc = history.history['val_accuracy'][-1]
    print(f"\nFinal training accuracy: {final_acc:.4f}")
    print(f"Final validation accuracy: {final_val_acc:.4f}")

    return model


def convert_to_tflite(model: keras.Model, output_path: Path, quantize: bool = True) -> None:
    """
    Convert Keras model to TFLite format with optional quantization.
    """
    print(f"\nConverting to TFLite...")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if quantize:
        # Dynamic range quantization (smaller model, faster inference)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]

    tflite_model = converter.convert()

    # Save model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    size_mb = len(tflite_model) / (1024 * 1024)
    print(f"Model saved: {output_path} ({size_mb:.2f} MB)")


def save_labels(class_names: List[str], output_path: Path) -> None:
    """
    Save class labels to text file.
    """
    with open(output_path, 'w') as f:
        for name in class_names:
            f.write(f"{name}\n")
    print(f"Labels saved: {output_path}")


def verify_model(model_path: Path, labels_path: Path) -> bool:
    """
    Verify the TFLite model can be loaded and run inference.
    """
    print("\nVerifying model...")

    try:
        # Load model
        interpreter = tf.lite.Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()

        # Get input/output details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        print(f"Input shape: {input_details[0]['shape']}")
        print(f"Output shape: {output_details[0]['shape']}")

        # Test inference with random input
        input_shape = input_details[0]['shape']
        test_input = np.random.rand(*input_shape).astype(np.float32)

        interpreter.set_tensor(input_details[0]['index'], test_input)
        interpreter.invoke()

        output = interpreter.get_tensor(output_details[0]['index'])
        print(f"Test inference successful, output shape: {output.shape}")

        # Load and verify labels
        with open(labels_path, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        print(f"Loaded {len(labels)} labels")

        return True

    except Exception as e:
        print(f"Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Train TFLite sneaker recognition model")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "sneaker-scraper" / "data" / "scraped_images",
        help="Directory containing training images"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "android-app" / "app" / "src" / "main" / "assets",
        help="Output directory for model files"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=EPOCHS,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Disable model quantization"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("TFLite Sneaker Recognition Model Training")
    print("=" * 60)

    # Check data directory
    if not args.data_dir.exists():
        print(f"Error: Data directory not found: {args.data_dir}")
        sys.exit(1)

    # Count available classes
    subdirs = [d for d in args.data_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
    if len(subdirs) < 2:
        print(f"Error: Need at least 2 classes, found {len(subdirs)}")
        print("Each subdirectory = one class (brand/model)")
        sys.exit(1)

    print(f"\nFound {len(subdirs)} sneaker classes")

    # Prepare dataset
    train_gen, val_gen, class_names = prepare_dataset(args.data_dir)

    # Create and train model
    model = create_model(num_classes=len(class_names))
    model = train_model(model, train_gen, val_gen, epochs=args.epochs)

    # Convert to TFLite
    model_path = args.output_dir / "sneaker_model.tflite"
    labels_path = args.output_dir / "sneaker_labels.txt"

    convert_to_tflite(model, model_path, quantize=not args.no_quantize)
    save_labels(class_names, labels_path)

    # Verify
    if verify_model(model_path, labels_path):
        print("\n" + "=" * 60)
        print("SUCCESS! Model ready for deployment")
        print("=" * 60)
        print(f"\nFiles created:")
        print(f"  - {model_path}")
        print(f"  - {labels_path}")
        print(f"\nCopy these to your Android app's assets folder.")
    else:
        print("\nWARNING: Model verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
