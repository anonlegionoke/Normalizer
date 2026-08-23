#!/usr/bin/env python3
import subprocess
import re
import sys
import colorsys
from collections import Counter

def get_colors_at_inset(icon_path, bw, bh, x, y, inset_pct):
    inset_x = max(1, int(bw * inset_pct))
    inset_y = max(1, int(bh * inset_pct))
    pts = [
        (x + bw//2, y + inset_y),
        (x + bw//2, y + bh - inset_y),
        (x + inset_x, y + bh//2),
        (x + bw - inset_x, y + bh//2)
    ]
    colors = []
    for px, py in pts:
        cmd = f'convert -density 384 -background none "{icon_path}" -depth 8 -crop "1x1+{px}+{py}" +repage -format "%[hex:u] %[fx:a]" info:'
        try:
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
            parts = out.split()
            if len(parts) >= 2 and float(parts[1]) > 0.9:
                colors.append(f"#{parts[0][:6].upper()}")
        except:
            pass
    return colors

def check_solid_shape(icon_path):
    cmd = f'convert -density 384 -background none "{icon_path}" -channel A -threshold 90% +channel -format "%@" info:'
    try:
        bounds = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
        bw, rest = bounds.split('x')
        bh, x, y = rest.replace('+', ' ').split()
        bw, bh, x, y = int(bw), int(bh), int(x), int(y)
    except:
        return None
        
    c10 = get_colors_at_inset(icon_path, bw, bh, x, y, 0.10)
    
    if not c10: return None
        
    counts = Counter(c10)
    most_common_color, most_common_count = counts.most_common(1)[0]
    
    if most_common_count == 4:
        c2 = get_colors_at_inset(icon_path, bw, bh, x, y, 0.02)
        if len(c2) == 4 and all(c == most_common_color for c in c2):
            return (True, most_common_color)
        else:
            return (False, "PALE")
    else:
        return (False, most_common_color)

def luminance(hex_col):
    def adjust(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def contrast(hex1, hex2):
    l1 = luminance(hex1)
    l2 = luminance(hex2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def hex_to_hsv(hex_col):
    r, g, b = int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)
    return colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)

def hue_diff(h1, h2):
    diff = abs(h1 - h2)
    return min(diff, 1.0 - diff) * 360

def is_contrasting(hex1, hex2):
    c = contrast(hex1, hex2)
    hsv1 = hex_to_hsv(hex1)
    hsv2 = hex_to_hsv(hex2)
    hd = hue_diff(hsv1[0], hsv2[0])
    
    if hd < 5.0: return c >= 2.5
    else: return c >= 1.35

def get_pale_fallback(colors):
    for count, hex_val in colors:
        r, g, b = int(hex_val[1:3], 16), int(hex_val[3:5], 16), int(hex_val[5:7], 16)
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        if s > 0.1:
            pale_s = min(s, 0.15)
            pale_v = max(v, 0.95)
            r_new, g_new, b_new = colorsys.hsv_to_rgb(h, pale_s, pale_v)
            return f"#{int(r_new*255):02X}{int(g_new*255):02X}{int(b_new*255):02X}"
    return "#FFFFFF"

def get_bg(icon_path, icon_name):
    cmd = f'convert -density 384 -background none "{icon_path}" -scale 50x50! -colors 4 -depth 8 -format "%c" histogram:info:'
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
    except:
        out = ""
        
    colors = []
    for line in out.split('\n'):
        m = re.search(r'^\s*(\d+):\s*\(([^)]+)\)\s*(#[0-9A-Fa-f]{6,8})', line)
        if m:
            count = int(m.group(1))
            rgba_str = m.group(2)
            hex_val = m.group(3)[:7].upper()
            vals = rgba_str.split(',')
            if len(vals) == 4 and int(vals[3]) < 128: continue
            colors.append((count, hex_val))
            
    colors.sort(key=lambda x: x[0], reverse=True)
    
    if colors:
        is_pure_black = all(luminance(h) < 0.10 for _, h in colors)
        if is_pure_black: return "#FFFFFF"
        is_pure_white = all(luminance(h) > 0.90 for _, h in colors)
        if is_pure_white: return "#222222"

    if any(n in icon_name.lower() for n in ['chrome', 'firefox', 'brave', 'libreoffice']):
        return get_pale_fallback(colors)

    solid_res = check_solid_shape(icon_path)
    if solid_res and solid_res[0]:
        return f"SOLID:{solid_res[1]}"

    bg_color = None
    if solid_res and not solid_res[0]:
        bg_color = solid_res[1]

    if not bg_color or bg_color == "PALE" or bg_color == "#FFFFFF":
        if not bg_color:
            if not colors:
                bg_color = "#FFFFFF"
            else:
                def get_fallback(hex_val):
                    r, g, b = int(hex_val[1:3], 16), int(hex_val[3:5], 16), int(hex_val[5:7], 16)
                    if (r*299 + g*587 + b*114) / 1000 > 200: return "#222222"
                    else: return "PALE"

                if len(colors) == 1:
                    bg_color = get_fallback(colors[0][1])
                else:
                    c1, h1 = colors[0]
                    c2, h2 = colors[1]
                    total = sum(c[0] for c in colors)
                    if total > 0 and c1 / total < 0.40:
                        bg_color = "PALE"
                    elif is_grayscale(h1) and not is_grayscale(h2):
                        h1 = h2
                    
                    if not bg_color:
                        if c2 > 0 and (c1 - c2) / c1 <= 0.05:
                            bg_color = "PALE"
                        else:
                            has_contrast = False
                            for count, h_other in colors:
                                if h_other == h1: continue
                                if is_contrasting(h1, h_other):
                                    has_contrast = True
                                    break
                            if not has_contrast:
                                bg_color = get_fallback(h1)
                            else:
                                bg_color = h1

    if bg_color and bg_color.startswith("#") and colors:
        total_pixels = sum(c[0] for c in colors)
        for count, hex_color in colors:
            if count / total_pixels < 0.05: continue
            if not is_contrasting(bg_color, hex_color):
                bg_color = "PALE"
                break

    if bg_color == "PALE":
        bg_color = get_pale_fallback(colors)

    return bg_color

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("#FFFFFF")
        sys.exit(1)
    print(get_bg(sys.argv[1], sys.argv[2]))
