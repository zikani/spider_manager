"""
Convert SVG to ICO format for Windows executable icon.
Requires: cairosvg (pip install cairosvg)
"""
import sys
from pathlib import Path

try:
    from PIL import Image
    import cairosvg
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install cairosvg Pillow")
    sys.exit(1)


def svg_to_ico(svg_path: Path, ico_path: Path, sizes: list[int] = None):
    """Convert SVG to ICO with multiple sizes."""
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    
    print(f"Converting {svg_path} to {ico_path}")
    
    png_data = cairosvg.svg2png(url=str(svg_path), output_width=256, output_height=256)
    img = Image.open(io.BytesIO(png_data))
    
    img.save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
    )
    
    print(f"Successfully created {ico_path}")


if __name__ == "__main__":
    import io
    
    svg_file = Path("resources/icons/brand/spider_logo.svg")
    ico_file = Path("resources/icons/brand/spider_logo.ico")
    
    if not svg_file.exists():
        print(f"SVG file not found: {svg_file}")
        sys.exit(1)
    
    svg_to_ico(svg_file, ico_file)
