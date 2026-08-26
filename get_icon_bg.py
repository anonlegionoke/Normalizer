#!/usr/bin/env python3
import sys
import collections
import subprocess
import tempfile
import os
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
    # If the entire non-transparent part of the logo is just ONE color (like ChatGPT's black logo),
    # using that color as a background will make it invisible.
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
    def quantize_coarse(color): return (color[0] // 128 * 128, color[1] // 128 * 128, color[2] // 128 * 128)
    
    q_all = [quantize(c) for c in all_pixels]
    all_counter = collections.Counter(q_all)
    all_ratio = all_counter.most_common(1)[0][1] / len(q_all)
    
    # If the logo is essentially a single solid color shape (e.g. > 98%), fall back to white/contrast
    if all_ratio > 0.98:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    # 2. Edge dominance check (Use coarse quantization for gradients like LibreOffice!)
    q_perim = [quantize_coarse(c) for c in perimeter_pixels]
    perim_counter = collections.Counter(q_perim)
    
    most_common_color, most_common_count = perim_counter.most_common(1)[0]
    perim_ratio = most_common_count / len(q_perim)
    
    # If a color dominates the edge (>50%), use it!
    if perim_ratio > 0.50:
        target_q = most_common_color
        exact_pixels = [c for c in perimeter_pixels if quantize_coarse(c) == target_q]
        avg_r = sum(c[0] for c in exact_pixels) // len(exact_pixels)
        avg_g = sum(c[1] for c in exact_pixels) // len(exact_pixels)
        avg_b = sum(c[2] for c in exact_pixels) // len(exact_pixels)
        result = f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
    else:
        result = "HIST:#FFFFFF"
        
    if temp_png and os.path.exists(temp_png):
        os.remove(temp_png)
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    print(get_bg_color(sys.argv[1]))
