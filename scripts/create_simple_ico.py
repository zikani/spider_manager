"""
Create a simple ICO file for Windows executable.
This creates a basic icon without requiring external SVG conversion tools.
"""
from PIL import Image, ImageDraw
from pathlib import Path


def create_spider_icon(ico_path: Path):
    """Create a simple spider web icon."""
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center = size // 2
        radius = size // 2 - 2
        
        for i in range(8):
            angle = i * (360 / 8)
            import math
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            draw.line([(center, center), (x, y)], fill=(100, 100, 200, 255), width=max(1, size // 32))
        
        for i in range(3):
            r = radius * (i + 1) / 3
            draw.ellipse([center - r, center - r, center + r, center + r], 
                        outline=(100, 100, 200, 255), width=max(1, size // 32))
        
        images.append(img)
    
    images[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"Created icon: {ico_path}")


if __name__ == "__main__":
    ico_file = Path("resources/icons/brand/spider_logo.ico")
    ico_file.parent.mkdir(parents=True, exist_ok=True)
    create_spider_icon(ico_file)
