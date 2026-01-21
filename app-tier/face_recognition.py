#!/usr/bin/env python3
"""
Face recognition stub for local testing.
Replace with actual implementation for production.
"""
import sys


def recognize_face(image_path: str) -> str:
    #stub - returns placeholder for smoke testing
    return f"UNKNOWN:{image_path.split('/')[-1]}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python face_recognition.py <image_path>")
        sys.exit(1)

    result = recognize_face(sys.argv[1])
    print(result)
