from pathlib import Path
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QPen, QBrush
from PySide6.QtSvg import QSvgRenderer
from PIL import Image

ASSETS = Path("assets")
SOURCE = ASSETS / "waraka_logo.svg"
if not SOURCE.exists():
    raise FileNotFoundError(f"Missing official logo: {SOURCE}")

app = QGuiApplication.instance() or QGuiApplication([])
renderer = QSvgRenderer(str(SOURCE))
if not renderer.isValid():
    raise RuntimeError("WARAKA SVG logo could not be loaded.")

size = 1024
image = QImage(size, size, QImage.Format_ARGB32)
image.fill(Qt.transparent)
painter = QPainter(image)
painter.setRenderHint(QPainter.Antialiasing, True)
painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

# Recreate the supplied square app-icon treatment: white rounded tile,
# blue outline, and the original vertical WARAKA mark centered without distortion.
painter.setPen(QPen(QColor("#292fac"), 18))
painter.setBrush(QBrush(QColor("#ffffff")))
painter.drawRoundedRect(QRectF(40, 40, 944, 944), 110, 110)

source_size = renderer.defaultSize()
scale = min(240 / source_size.width(), 355 / source_size.height())
width = source_size.width() * scale
height = source_size.height() * scale
target = QRectF((size - width) / 2, (size - height) / 2, width, height)
renderer.render(painter, target)
painter.end()

png_path = ASSETS / "waraka_icon_source.png"
image.save(str(png_path))
icon = Image.open(png_path).convert("RGBA")
for name in ("waraka.ico", "pdf_splitter.ico"):
    icon.save(ASSETS / name, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
png_path.unlink(missing_ok=True)
print("Created WARAKA Windows icons using the supplied icon layout.")
