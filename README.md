# Normalizer

A highly sophisticated, automated icon normalizer for GNOME that dynamically transforms all installed application icons into beautifully consistent, themed squircles.

Unlike static icon themes, this engine reads your actual system and user applications and applies intelligent image processing to standardize them into normalized squircles while perfectly preserving the original branding and colors.

## Features

- **Automated Squirclification:** Automatically applies a squircle mask to all installed icons.
- **Intelligent Background Generation:** 
  - Extracts the most prominent saturated color from the icon.
  - Automatically generates a gorgeous pale/pastel background to ensure the logo pops.
  - Falls back to pure white or dark backgrounds for grayscale/black-and-white logos.
- **Smart Framing Detection:** Uses multi-pass inset checking to differentiate between "solid blocks of color" and "framed borders", so framed icons (like Console or Nautilus) don't bleed awkwardly outside the squircle.
- **Camouflage Prevention:** Checks contrast to ensure the logo doesn't dissolve into the background.
- **Web App & Custom Icon Support:** Safely handles Firefox PWAs and custom icons (set via LibreMenuEditor) without overwriting your pristine original SVG/PNG files. Custom icons are aggregated cleanly into the system cache.
- **Non-Destructive:** Operates entirely by modifying a cache folder (`~/.local/share/icons/hicolor/256x256/apps/`) and tweaking local `.desktop` files. System-wide icons are never permanently altered.

## Requirements

- Python 3
- ImageMagick (`convert` or `magick`)
- `colorthief` (Python library)
- `Pillow` (Python library)

To install dependencies:
```bash
pip install colorthief Pillow
sudo dnf install ImageMagick # (Or equivalent for your distro)
```

## Usage

Run the bash script to scan your `.desktop` files and generate the normalizer cache:

```bash
./normalizer.sh --force --color
```

Once the engine finishes, log out of your GNOME session and log back in to see the changes applied perfectly across your App Grid!

## License
MIT
