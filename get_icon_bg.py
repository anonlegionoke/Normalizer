#!/usr/bin/env python3
import sys
import collections
from PIL import Image

def get_bg_color(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        return "HIST:#FFFFFF"
        
    width, height = img.size
    
    # 1. Get the bounding box of non-transparent pixels
    bbox = img.getbbox()
    if not bbox:
        return "HIST:#FFFFFF" # Empty image
        
    left, upper, right, lower = bbox
    
    # 2. Sample the perimeter of the non-transparent bounding box
    perimeter_pixels = []
    
    # Sample a 5% margin inside the bounding box
    margin_x = max(1, int((right - left) * 0.05))
    margin_y = max(1, int((lower - upper) * 0.05))
    
    for y in range(upper, lower):
        for x in range(left, right):
            r, g, b, a = img.getpixel((x, y))
            if a > 128:
                # Is it near the edge of the bounding box?
                if (x < left + margin_x) or (x > right - margin_x - 1) or \
                   (y < upper + margin_y) or (y > lower - margin_y - 1):
                    perimeter_pixels.append((r, g, b))
                    
    if not perimeter_pixels:
        return "HIST:#FFFFFF"
        
    # Quantize colors to group similar ones (e.g. 64 bins per channel for broad grouping)
    def quantize(color):
        return (color[0] // 64 * 64, color[1] // 64 * 64, color[2] // 64 * 64)
        
    quantized_pixels = [quantize(c) for c in perimeter_pixels]
    counter = collections.Counter(quantized_pixels)
    
    total_samples = len(quantized_pixels)
    most_common_color, most_common_count = counter.most_common(1)[0]
    
    ratio = most_common_count / total_samples
    
    # If the most common edge color dominates (>45%), use it as the solid background
    if ratio > 0.45:
        target_q = most_common_color
        exact_pixels = [c for c in perimeter_pixels if quantize(c) == target_q]
        avg_r = sum(c[0] for c in exact_pixels) // len(exact_pixels)
        avg_g = sum(c[1] for c in exact_pixels) // len(exact_pixels)
        avg_b = sum(c[2] for c in exact_pixels) // len(exact_pixels)
        return f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
    else:
        # Multiple distinct colors (e.g. Chrome, Firefox) -> fallback to White
        return "HIST:#FFFFFF"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    
    image_path = sys.argv[1]
    bg_color = get_bg_color(image_path)
    print(bg_color)
