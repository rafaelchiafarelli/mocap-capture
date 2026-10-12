"""Interim: print-ready ChArUco 5x3 board (FreeMoCap '5x3 Charuco') on A0 landscape at exact scale.

Made the board decided in studio-setup decision 2 (2026-10-12):
/mnt/g/mocap-studio-downloads/calibration/charuco-5x3-200mm-A0.pdf
Replaced by `mocap-capture board pdf` (studio-setup board/2), which reads the
board from config.yaml instead of these constants. Needs opencv-contrib + Pillow:

    python tools/make_charuco_board.py OUT.pdf /path/to/DejaVuSans.ttf
"""
import sys
import cv2
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1]
PX_PER_MM = 10                      # 254 dpi
SQUARES_X, SQUARES_Y = 5, 3
SQUARE_MM, MARKER_MM = 200, 160     # marker = 0.8 x square, as FreeMoCap defines it
PAGE_W_MM, PAGE_H_MM = 1189, 841    # A0 landscape

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
board = cv2.aruco.CharucoBoard((SQUARES_X, SQUARES_Y), SQUARE_MM / 1000, MARKER_MM / 1000, dictionary)
bw, bh = SQUARES_X * SQUARE_MM * PX_PER_MM, SQUARES_Y * SQUARE_MM * PX_PER_MM
img = board.generateImage((bw, bh), marginSize=0, borderBits=1)

page = Image.new("L", (PAGE_W_MM * PX_PER_MM, PAGE_H_MM * PX_PER_MM), 255)
ox, oy = (page.width - bw) // 2, (page.height - bh) // 2
page.paste(Image.fromarray(img), (ox, oy))

draw = ImageDraw.Draw(page)
font = ImageFont.truetype(sys.argv[2], 90)
label = (f"FreeMoCap '5x3 Charuco' | {SQUARES_X}x{SQUARES_Y} squares | square {SQUARE_MM} mm | marker {MARKER_MM} mm | "
         f"DICT_4X4_250 | A0 landscape, print at 100% (NO fit-to-page) | measure a square with a caliper -> measured_square_length_mm")
draw.text((ox, oy + bh + 60), label, fill=0, font=font)
# 100 mm scale bar to check the print scale
bar_y = oy - 200
draw.rectangle((ox, bar_y, ox + 100 * PX_PER_MM, bar_y + 40), fill=0)
draw.text((ox + 100 * PX_PER_MM + 40, bar_y - 30), "this bar must measure exactly 100 mm", fill=0, font=font)
page.save(out, "PDF", resolution=25.4 * PX_PER_MM)
print("saved", out, page.size)
