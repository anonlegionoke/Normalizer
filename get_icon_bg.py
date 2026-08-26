#!/usr/bin/env python3
import sys
import collections
import subprocess
import tempfile
import os
import colorsys
from PIL import Image

def get_bg_color(image_path):
    temp_png = None
    try:
        if image_path.lower().endswith(".svg"):
            temp_png = tempfile.mktemp(suffix=".png")
            subprocess.run(["convert", "-background", "none", "-size", "256x256", image_path, temp_png], check=True, stderr=subprocess.DEVNULL)
            img = Image.open(temp_png).convert("RGBA")
        else:
            img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    width, height = img.size
    
    bbox = img.getbbox()
    if not bbox:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    left, upper, right, lower = bbox
    
    # 1. Mono-color check
    all_pixels = []
    perimeter_pixels = []
    
    margin_x = max(1, int((right - left) * 0.05))
    margin_y = max(1, int((lower - upper) * 0.05))
    
    for y in range(upper, lower):
        for x in range(left, right):
            r, g, b, a = img.getpixel((x, y))
            if a > 128:
                all_pixels.append((r, g, b))
                if (x < left + margin_x) or (x > right - margin_x - 1) or \
                   (y < upper + margin_y) or (y > lower - margin_y - 1):
                    perimeter_pixels.append((r, g, b))
                    
    if not perimeter_pixels or not all_pixels:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    def quantize(color): return (color[0] // 64 * 64, color[1] // 64 * 64, color[2] // 64 * 64)
    
    q_all = [quantize(c) for c in all_pixels]
    all_counter = collections.Counter(q_all)
    all_ratio = all_counter.most_common(1)[0][1] / len(q_all)
    
    if all_ratio > 0.98:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    # 2. Edge dominance check using HSV for gradients
    hues = []
    for (r, g, b) in perimeter_pixels:
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if s < 0.1 or v < 0.1:
            hues.append("grayscale")
        else:
            hues.append(int(h * 12)) # 12 bins = 30 degrees each
            
    hue_counter = collections.Counter(hues)
    most_common_hue, most_common_count = hue_counter.most_common(1)[0]
    hue_ratio = most_common_count / len(hues)
    
    # If a hue (or grayscale) dominates the edge (>70%), we use it!
    # A single-color gradient will easily score 90-100% here.
    # A multi-color icon (Firefox, Chrome) will score ~30-40%.
    if hue_ratio > 0.70:
        # Extract the exact average of ONLY the pixels that fell into the dominant hue bucket
        # so we get an accurate, pleasant color (ignoring the tiny bit of antialiasing noise)
        target_pixels = []
        for (r, g, b) in perimeter_pixels:
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            curr_hue = "grayscale" if (s < 0.1 or v < 0.1) else int(h * 12)
            if curr_hue == most_common_hue:
                target_pixels.append((r, g, b))
                
        avg_r = sum(c[0] for c in target_pixels) // len(target_pixels)
        avg_g = sum(c[1] for c in target_pixels) // len(target_pixels)
        avg_b = sum(c[2] for c in target_pixels) // len(target_pixels)
        result = f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
    else:
        result = "HIST:#FFFFFF"
        
    if temp_png and os.path.exists(temp_png):
        os.remove(temp_png)
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    print(get_bg_color(sys.argv[1]))
