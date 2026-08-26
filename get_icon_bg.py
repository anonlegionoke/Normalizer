#!/usr/bin/env python3
import sys
import collections
import subprocess
import tempfile
import os
import colorsys
from PIL import Image

FORCE_WHITE = ["google-chrome", "firefox", "chromium", "brave", "vivaldi", "microsoft-edge"]

def get_bg_color(image_path, icon_name=""):
    if "webapp" not in icon_name.lower() and "webapp" not in image_path.lower():
        for fw in FORCE_WHITE:
            if fw in icon_name.lower() or fw in os.path.basename(image_path).lower():
                return "HIST:#FFFFFF"
                
    if "org.gnome.weather" in icon_name.lower() or "org.gnome.weather" in image_path.lower():
        return "HIST:#f6e88c"
            
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
    all_pixels = []
    perimeter_pixels = []
    
    margin_x = max(1, int((right - left) * 0.05))
    margin_y = max(1, int((lower - upper) * 0.05))
    
    gray_count_all = 0
    total_count_all = 0
    
    for y in range(upper, lower):
        for x in range(left, right):
            r, g, b, a = img.getpixel((x, y))
            if a > 128:
                total_count_all += 1
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                if s < 0.1 or v < 0.1:
                    gray_count_all += 1
                
                all_pixels.append((r, g, b))
                if (x < left + margin_x) or (x > right - margin_x - 1) or \
                   (y < upper + margin_y) or (y > lower - margin_y - 1):
                    perimeter_pixels.append((r, g, b))
                    
    if not perimeter_pixels or not all_pixels:
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        return "HIST:#FFFFFF"
        
    if gray_count_all / total_count_all > 0.95:
        avg_brightness = sum(c[0]*0.299 + c[1]*0.587 + c[2]*0.114 for c in all_pixels) / len(all_pixels)
        perim_brightness = sum(c[0]*0.299 + c[1]*0.587 + c[2]*0.114 for c in perimeter_pixels) / len(perimeter_pixels)
        if temp_png and os.path.exists(temp_png): os.remove(temp_png)
        
        # If the perimeter is pure white, it's a solid white block (like Claude or Devin).
        # We want these to seamlessly expand into a White background!
        if perim_brightness > 250:
            return "HIST:#FFFFFF"
        
        if avg_brightness > 128:
            return "HIST:#333333"
        else:
            return "HIST:#FFFFFF"
            
    hues = []
    for (r, g, b) in perimeter_pixels:
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if s < 0.1 or v < 0.1:
            hues.append("grayscale")
        else:
            hues.append(int(h * 12))
            
    hue_counter = collections.Counter(hues)
    max_count = 0
    best_hue_pair = None
    grayscale_count = hue_counter["grayscale"]
    
    for h in range(12):
        count = hue_counter[h] + hue_counter[(h+1)%12]
        if count > max_count:
            max_count = count
            best_hue_pair = (h, (h+1)%12)
            
    total_hues = len(hues)
    result = "HIST:#FFFFFF"
    
    if grayscale_count / total_hues > 0.55:
        all_inner_hues = []
        for (r, g, b) in all_pixels:
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            if s >= 0.1 and v >= 0.1:
                all_inner_hues.append(int(h * 12))
        
        if all_inner_hues:
            inner_counter = collections.Counter(all_inner_hues)
            max_inner_count = 0
            best_inner_pair = None
            for h in range(12):
                count = inner_counter[h] + inner_counter[(h+1)%12]
                if count > max_inner_count:
                    max_inner_count = count
                    best_inner_pair = (h, (h+1)%12)
                    
            if max_inner_count / len(all_pixels) > 0.30:
                target_pixels = []
                for (r, g, b) in all_pixels:
                    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                    if s >= 0.1 and v >= 0.1 and int(h * 12) in best_inner_pair:
                        target_pixels.append((r, g, b))
                if target_pixels:
                    avg_r = sum(c[0] for c in target_pixels) // len(target_pixels)
                    avg_g = sum(c[1] for c in target_pixels) // len(target_pixels)
                    avg_b = sum(c[2] for c in target_pixels) // len(target_pixels)
                    result = f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
                    if temp_png and os.path.exists(temp_png): os.remove(temp_png)
                    return result
        
        target_pixels = [c for c in perimeter_pixels if (colorsys.rgb_to_hsv(c[0]/255, c[1]/255, c[2]/255)[1] < 0.1 or colorsys.rgb_to_hsv(c[0]/255, c[1]/255, c[2]/255)[2] < 0.1)]
        if target_pixels:
            avg_r = sum(c[0] for c in target_pixels) // len(target_pixels)
            avg_g = sum(c[1] for c in target_pixels) // len(target_pixels)
            avg_b = sum(c[2] for c in target_pixels) // len(target_pixels)
            result = f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
            
    elif max_count / total_hues > 0.55:
        target_pixels = []
        for (r, g, b) in perimeter_pixels:
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            if s >= 0.1 and v >= 0.1:
                curr_hue = int(h * 12)
                if curr_hue in best_hue_pair:
                    target_pixels.append((r, g, b))
        if target_pixels:
            avg_r = sum(c[0] for c in target_pixels) // len(target_pixels)
            avg_g = sum(c[1] for c in target_pixels) // len(target_pixels)
            avg_b = sum(c[2] for c in target_pixels) // len(target_pixels)
            result = f"HIST:#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
            
    if temp_png and os.path.exists(temp_png):
        os.remove(temp_png)
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    icon_name = sys.argv[2] if len(sys.argv) > 2 else ""
    print(get_bg_color(sys.argv[1], icon_name))
