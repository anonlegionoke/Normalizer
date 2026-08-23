#!/bin/bash

# Advanced GNOME Icon Normalization Engine

# Configuration
OUTPUT_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
BACKUP_DIR="$HOME/.local/share/icons_squircle_backup"
TEST_DIR="$HOME/Pictures/SquircleTest"
MASK_FILE="/tmp/squircle_mask.png"

# Argument parsing
MODE="normal"
FORCE=0
DARK_MODE=0
AUTO_MODE=0
COLOR_MODE=0

for arg in "$@"; do
  case $arg in
    --restore) MODE="restore" ;;
    --test) MODE="test" ;;
    --force) FORCE=1 ;;
    --dark) DARK_MODE=1 ;;
    --auto) AUTO_MODE=1 ;;
    --color) COLOR_MODE=1 ;;
  esac
done

# Check dependencies
if ! command -v convert &> /dev/null || ! command -v identify &> /dev/null; then
    echo "Error: ImageMagick is not installed."
    echo "Please run: sudo dnf install ImageMagick"
    exit 1
fi

# Restore Mode
if [ "$MODE" == "restore" ]; then
    if [ -d "$BACKUP_DIR" ]; then
        echo "Restoring from master backup..."
        rm -rf "$HOME/.local/share/icons/hicolor"
        mkdir -p "$HOME/.local/share/icons/hicolor"
        cp -a "$BACKUP_DIR"/* "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor"
        echo "Restore complete! Please log out and log back in."
    else
        echo "No backup found to restore."
    fi
    exit 0
fi

# Setup output dir and master backup
if [ "$MODE" == "test" ]; then
    OUTPUT_DIR="$TEST_DIR"
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    echo "Running in TEST mode. Icons will be saved to $OUTPUT_DIR"
else
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "Creating master backup of local hicolor icons..."
        mkdir -p "$BACKUP_DIR"
        if [ -d "$HOME/.local/share/icons/hicolor" ]; then
            cp -a "$HOME/.local/share/icons/hicolor"/* "$BACKUP_DIR/" 2>/dev/null || true
        fi
    fi
    mkdir -p "$OUTPUT_DIR"
fi

# Generate the master squircle mask
convert -size 256x256 xc:none -fill white -draw "roundrectangle 0,0 256,256 55,55" "$MASK_FILE"

# Function to find best icon
# Function to find best icon
find_best_icon() {
    local icon_name="$1"
    local all_found=""
    
    for path in "/var/lib/flatpak/exports/share/icons" \
                "/usr/local/share/icons" \
                "/usr/share/icons" \
                "/usr/local/share/pixmaps" \
                "/usr/share/pixmaps" \
                "$HOME/.local/share/icons_squircle_backup"; do
        if [ -d "$path" ]; then
            local found=$(find "$path" \( -type f -o -type l \) \( -name "${icon_name}.png" -o -name "${icon_name}.svg" \) 2>/dev/null | grep -v "\-symbolic")
            if [ -n "$found" ]; then
                all_found="$all_found$found\n"
            fi
        fi
    done
    
    if [ -d "$HOME/.local/share/icons" ]; then
        local found=$(find "$HOME/.local/share/icons" -not -path "*/hicolor/*" \( -type f -o -type l \) \( -name "${icon_name}.png" -o -name "${icon_name}.svg" \) 2>/dev/null | grep -v "\-symbolic")
        if [ -n "$found" ]; then
            all_found="$all_found$found\n"
        fi
    fi
    
    local best_icon=""
    if [ -n "$all_found" ]; then
        best_icon=$(echo -e "$all_found" | grep "/scalable/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/1024x1024/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/512x512/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/256x256/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/192x192/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/128x128/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/96x96/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/72x72/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/64x64/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/48x48/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep "/32x32/" | head -n 1)
        [ -z "$best_icon" ] && best_icon=$(echo -e "$all_found" | grep -v "^$" | head -n 1)
    fi
    
    echo "$best_icon"
}



# App directories (order matters: local overrides system)
APP_DIRS=(
    "$HOME/.local/share/applications"
    "/var/lib/flatpak/exports/share/applications"
    "/usr/share/applications"
)

echo "Starting normalization engine..."

declare -A PROCESSED_APPS

# Loop through all apps
for app_dir in "${APP_DIRS[@]}"; do
    if [ ! -d "$app_dir" ]; then continue; fi
    
    for desktop in "$app_dir"/*.desktop; do
        [ -f "$desktop" ] || continue
        
        desktop_base=$(basename "$desktop")
        if [[ -n "${PROCESSED_APPS[$desktop_base]}" ]]; then
            # Already processed a higher priority version of this desktop file
            continue
        fi
        
        # Extract Icon line
        ICON_VALUE=$(grep -m 1 "^Icon=" "$desktop" | cut -d'=' -f2 | tr -d '\r')
        [ -z "$ICON_VALUE" ] && continue
        
        ICON_PATH=""
        ICON_NAME=""
        
        # Prevent recursive squirclification!
        if [[ "$ICON_VALUE" == "$HOME/.local/share/icons/hicolor/256x256/apps/"* ]]; then
            ICON_VALUE=$(basename "$ICON_VALUE")
            ICON_VALUE="${ICON_VALUE%.*}"
        fi
        
        if [[ "$ICON_VALUE" == /* ]]; then
            if [ -f "$ICON_VALUE" ]; then
                ICON_PATH="$ICON_VALUE"
                ICON_NAME="custom_${desktop_base%.*}"
                OUTPUT_FILE="$OUTPUT_DIR/${ICON_NAME}.png"
                
                # Restore old backups from flawed in-place logic if they exist
                if [[ "$ICON_VALUE" == "$HOME"* ]] && [ -f "${ICON_VALUE}.source_bak" ]; then
                    mv "${ICON_VALUE}.source_bak" "$ICON_VALUE" 2>/dev/null || true
                fi
                
                if [ "$MODE" != "test" ]; then
                    if [[ "$app_dir" != "$HOME/.local/share/applications" ]]; then
                        cp "$desktop" "$HOME/.local/share/applications/$desktop_base"
                        desktop="$HOME/.local/share/applications/$desktop_base"
                        chmod +x "$desktop"
                    fi
                    sed -i "s|^Icon=.*|Icon=$OUTPUT_FILE|" "$desktop"
                fi
            fi
        else
            ICON_PATH=$(find_best_icon "$ICON_VALUE")
            ICON_NAME="$ICON_VALUE"
            OUTPUT_FILE="$OUTPUT_DIR/${ICON_NAME}.png"
            
            if [ "$MODE" != "test" ]; then
                if [[ "$app_dir" != "$HOME/.local/share/applications" ]]; then
                    cp "$desktop" "$HOME/.local/share/applications/$desktop_base"
                    desktop="$HOME/.local/share/applications/$desktop_base"
                fi
                # Point explicitly to the new generated squircle
                sed -i "s|^Icon=.*|Icon=$OUTPUT_FILE|" "$desktop"
            fi
        fi
        
        if [ -n "$ICON_PATH" ]; then
            PROCESSED_APPS[$desktop_base]=1
            
            # Skip logic
            needs_generation=1
            if [ "$FORCE" -eq 0 ]; then
                src_mod=$(stat -c %Y "$ICON_PATH" 2>/dev/null || echo 0)
                dst_mod=$(stat -c %Y "$OUTPUT_FILE" 2>/dev/null || echo 0)
                if [ "$dst_mod" -gt "$src_mod" ] && [ "$dst_mod" -gt 0 ]; then
                    needs_generation=0
                fi
            fi
            
            if [ "$needs_generation" -eq 0 ]; then
                continue
            fi
            
            echo "Processing: $ICON_NAME (Source: $ICON_PATH)"
            
            # True transparency check
            # First run advanced background check to see if it's inherently padded
            mean_a=$(LC_ALL=C convert -density 384 -background none "$ICON_PATH" -format "%[fx:mean.a]" info: 2>/dev/null)
            if [ -z "$mean_a" ]; then
                mean_a=1
            fi
            is_solid=$(awk -v a="$mean_a" 'BEGIN {print (a > 0.95) ? 1 : 0}')
            
            if [ "$is_solid" -eq 1 ]; then
                # Solid Logic: Inherently has background.
                # Find the dominant background color by sampling the top-center edge (safely below transparent corners).
                # This guarantees we extract the true padding color (e.g. White for Chrome, Blue for Trello)
                # and avoids the 'magenta transparency' bug caused by alpha removal on PNGs.
                bg_color=$(LC_ALL=C convert "$ICON_PATH" -resize 256x256\! -crop 1x1+128+15 +repage -alpha off -depth 8 -format "%[hex:u]" info: 2>/dev/null)
                if [[ ! "$bg_color" =~ ^[0-9A-Fa-f]{6}$ ]]; then
                    bg_color="FFFFFF"
                fi
                
                # Solid icons already fill the full canvas with their own background.
                # Check if the logo is too close to the edge. If so, apply dynamic padding.
                bg_hex=$(convert "$ICON_PATH" -crop "1x1+0+0" +repage -format "%[hex:u]" info: 2>/dev/null | cut -c 1-6)
                trim_info=$(convert "$ICON_PATH" -bordercolor "#$bg_hex" -border 1x1 -fuzz 5% -trim -format "%w %h" info: 2>/dev/null)
                trim_w=$(echo $trim_info | awk '{print $1}')
                trim_h=$(echo $trim_info | awk '{print $2}')
                max_dim=$(( trim_w > trim_h ? trim_w : trim_h ))
                
                # If logo is > 192px but < 250px (not full-bleed), pad it to match Freeform size (192)
                if [ -n "$max_dim" ] && [ "$max_dim" -gt 192 ] && [ "$max_dim" -lt 250 ]; then
                    scale_pct=$(awk "BEGIN {print int((192 / $max_dim) * 100)}")
                    convert -size 256x256 xc:"#$bg_hex" \
                        \( "$ICON_PATH" -resize ${scale_pct}% \) \
                        -gravity center -composite \
                        "$MASK_FILE" -alpha Set -compose DstIn -composite \
                        "$OUTPUT_FILE" 2>/dev/null
                else
                    # Just mask directly
                    convert -background none "$ICON_PATH" -resize 256x256\! \
                        "$MASK_FILE" -alpha Set -compose DstIn -composite \
                        "$OUTPUT_FILE" 2>/dev/null
                fi
            else
                # Freeform Logic
                
                dom_hex=$("$(dirname "$(realpath "$0")")/get_icon_bg.py" "$ICON_PATH" "$ICON_NAME" 2>/dev/null)
                
                if [[ "$dom_hex" == SOLID:* ]]; then
                    BG_COLOR="${dom_hex#SOLID:}"
                    bounds=$(convert -density 384 -background none "$ICON_PATH" -channel A -threshold 90% +channel -format "%@" info: 2>/dev/null)
                    convert "$MASK_FILE" \
                        -fill "$BG_COLOR" -colorize 100 \
                        \( -density 384 -background none "$ICON_PATH" -crop "$bounds" +repage -resize 256x256^ -gravity center -extent 256x256 \) -gravity center -composite \
                        "$MASK_FILE" -compose DstIn -composite \
                        "$OUTPUT_FILE" 2>/dev/null
                else
                    dom_hex=${dom_hex#HIST:}
                    if [ "$COLOR_MODE" -eq 1 ]; then
                        if [[ "$dom_hex" =~ ^#[0-9A-Fa-f]{6}$ ]]; then
                            BG_COLOR="$dom_hex"
                        else
                            BG_COLOR="#FFFFFF"
                        fi
                    elif [ "$DARK_MODE" -eq 1 ]; then
                        BG_COLOR="#222222"
                    else
                        BG_COLOR="#FFFFFF"
                    fi
                    
                    convert -size 256x256 xc:"$BG_COLOR" \
                        \( -density 384 -background none "$ICON_PATH" -resize 180x180 -gravity center -extent 256x256 \) \
                        -gravity center -composite \
                        "$MASK_FILE" -alpha Set -compose DstIn -composite \
                        "$OUTPUT_FILE" 2>/dev/null
                fi
            fi
            # Omni-Override (Only for relative paths or root absolute paths that rely on the theme cache)
            if [ -f "$OUTPUT_FILE" ] && [ "$MODE" != "test" ] && [[ ! ("$ICON_VALUE" == /* && "$ICON_VALUE" == "$HOME"*) ]]; then
                HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
                
                # Cleanup the broken SVG wrappers/PNGs from previous flawed runs
                rm -f "$HICOLOR_DIR/scalable/apps/${ICON_NAME}.png"
                
                # Symlink to other raster sizes (safely)
                for size in 32x32 48x48 64x64 128x128 512x512; do
                    mkdir -p "$HICOLOR_DIR/$size/apps"
                    target_file="$HICOLOR_DIR/$size/apps/${ICON_NAME}.png"
                    # Never overwrite an existing regular file (source icon) with a symlink!
                    if [ ! -f "$target_file" ] || [ -L "$target_file" ]; then
                        ln -sf "../../256x256/apps/${ICON_NAME}.png" "$target_file"
                    fi
                done
                
                # Create a strict SVG 1.1 wrapper to absolutely override system Flatpak/Native SVGs
                mkdir -p "$HICOLOR_DIR/scalable/apps"
                base64_data=$(base64 -w 0 "$OUTPUT_FILE")
                cat <<XML > "$HICOLOR_DIR/scalable/apps/${ICON_NAME}.svg"
<svg width="256" height="256" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <image xlink:href="data:image/png;base64,$base64_data" width="256" height="256"/>
</svg>
XML
        fi
        fi
    done
done

# Post-processing
if [ "$MODE" == "test" ]; then
    HTML_FILE="$OUTPUT_DIR/preview.html"
    bg_style="#eee"
    text_style="#222"
    if [ "$DARK_MODE" -eq 1 ]; then
        bg_style="#222"
        text_style="#eee"
    fi
    echo "<html><head><style>body{background:$bg_style;color:$text_style;font-family:sans-serif;} .grid{display:flex;flex-wrap:wrap;gap:20px;padding:20px;} .item{text-align:center;width:100px;} img{width:80px;height:80px;border-radius:18px;box-shadow:0 4px 6px rgba(0,0,0,0.3);}</style></head><body><h2>Squircle Test Preview</h2><div class='grid'>" > "$HTML_FILE"
    
    for img in "$OUTPUT_DIR"/*.png; do
        if [ -f "$img" ]; then
            name=$(basename "$img" .png)
            echo "<div class='item'><img src='$(basename "$img")'><br><small>$name</small></div>" >> "$HTML_FILE"
        fi
    done
    
    echo "</div></body></html>" >> "$HTML_FILE"
    echo "Test complete! Opening preview..."
    xdg-open "$HTML_FILE" 2>/dev/null
else
    echo -e "\n${GREEN}✔ Engine complete! Changes applied to system cache.${NC}"

    # Ensure index.theme exists so GNOME treats our local hicolor as a primary theme, not a fallback
    if [ ! -f "$HOME/.local/share/icons/hicolor/index.theme" ] && [ -f "/usr/share/icons/hicolor/index.theme" ]; then
        cp /usr/share/icons/hicolor/index.theme "$HOME/.local/share/icons/hicolor/index.theme"
    fi

    if [ "$MODE" != "test" ]; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1
    fi
    
    # Reload desktop databases in case we patched desktop files
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    
    echo ""
    echo "⚠️  Please log out and log back in to see changes in the App Grid."
fi
