import os
import math
from PIL import Image, ImageDraw, ImageFont

def generate_icons():
    icons_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "static", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    sizes = [
        ("icon-180.png", 180, False),
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True)  # Safe zone: centered within 80% circle
    ]

    for filename, size, is_maskable in sizes:
        img = Image.new("RGBA", (size, size), (10, 14, 26, 255)) # Dark navy
        draw = ImageDraw.Draw(img)

        # Scale factor relative to 512px
        scale = size / 512.0
        center = size / 2.0

        # Subtle dark gradient circular background glow
        glow_radius = (180.0 if is_maskable else 210.0) * scale
        for r in range(int(glow_radius), 0, -6):
            alpha = int(45 * (1.0 - (r / glow_radius)))
            draw.ellipse(
                [center - r, center - r, center + r, center + r],
                fill=(0, 240, 255, alpha)
            )

        # Rounded background card if not maskable
        if not is_maskable:
            card_pad = 20 * scale
            draw.rounded_rectangle(
                [card_pad, card_pad, size - card_pad, size - card_pad],
                radius=int(60 * scale),
                outline=(0, 240, 255, 60),
                width=max(int(3 * scale), 1)
            )

        # Draw Infinity Route Symbol
        # Parametric lemniscate of Bernoulli: x = a*cos(t)/(1+sin(t)^2), y = a*sin(t)*cos(t)/(1+sin(t)^2)
        a = (130.0 if is_maskable else 155.0) * scale
        points = []
        steps = 180
        for i in range(steps):
            t = 2.0 * math.pi * (i / float(steps))
            denom = 1.0 + math.sin(t) ** 2
            x = center + (a * math.cos(t)) / denom
            y = center + (a * math.sin(t) * math.cos(t)) / denom
            points.append((x, y))

        line_w = max(int(22 * scale), 4)

        # Draw outer glow of the route
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            draw.line([p1, p2], fill=(138, 43, 226, 90), width=line_w + int(12 * scale))

        # Draw main neon cyan route
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            draw.line([p1, p2], fill=(0, 240, 255, 255), width=line_w)

        # Draw inner core white route line
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            draw.line([p1, p2], fill=(255, 255, 255, 220), width=max(line_w // 3, 2))

        # Origin waypoint marker (Green) on left loop
        ox, oy = points[steps // 4]
        mr = 18 * scale
        draw.ellipse([ox - mr, oy - mr, ox + mr, oy + mr], fill=(0, 230, 118, 255), outline=(255, 255, 255, 255), width=int(3 * scale))

        # Destination waypoint marker (Purple/Pink) on right loop
        dx, dy = points[3 * steps // 4]
        draw.ellipse([dx - mr, dy - mr, dx + mr, dy + mr], fill=(255, 0, 127, 255), outline=(255, 255, 255, 255), width=int(3 * scale))

        # Central quantum orb (Center)
        cr = 14 * scale
        draw.ellipse([center - cr, center - cr, center + cr, center + cr], fill=(0, 240, 255, 255), outline=(255, 255, 255, 255), width=int(2 * scale))

        # Save icon
        out_path = os.path.join(icons_dir, filename)
        img.save(out_path, "PNG")
        print(f"Saved {out_path} ({size}x{size})")

if __name__ == "__main__":
    generate_icons()
