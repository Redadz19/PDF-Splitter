from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import math

OUT = Path("assets")
OUT.mkdir(exist_ok=True)
S = 1024
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# Soft blue rounded-square app tile.
shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.rounded_rectangle((72, 72, 952, 952), radius=190, fill=(0, 35, 90, 100))
shadow = shadow.filter(ImageFilter.GaussianBlur(34))
im.alpha_composite(shadow)

tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
px = tile.load()
for y in range(S):
    for x in range(S):
        if (x-512)**2+(y-512)**2 < 455**2:
            t = (x+y)/(2*S)
            px[x,y] = (int(19+22*t), int(112+65*t), int(207+35*t), 255)
mask = Image.new("L",(S,S),0)
md=ImageDraw.Draw(mask)
md.rounded_rectangle((54,54,970,970),radius=205,fill=255)
im.alpha_composite(Image.composite(tile,Image.new("RGBA",(S,S),(0,0,0,0)),mask))

d=ImageDraw.Draw(im)
# White document with folded top-right corner.
doc=[(230,150),(610,150),(785,325),(785,825),(230,825)]
d.polygon(doc,fill=(255,255,255,255))
d.polygon([(610,150),(610,325),(785,325)],fill=(206,229,250,255))
d.line([(610,150),(610,325),(785,325)],fill=(106,169,224,255),width=13)
# Text lines.
d.rounded_rectangle((300,390,700,425),radius=16,fill=(38,100,165,255))
d.rounded_rectangle((300,465,690,495),radius=14,fill=(151,184,214,255))
d.rounded_rectangle((300,525,650,555),radius=14,fill=(151,184,214,255))
# PDF red label.
d.rounded_rectangle((270,600,610,735),radius=34,fill=(226,48,54,255),outline=(255,255,255,255),width=12)
# bold PDF lettering using default scalable font fallback.
from PIL import ImageFont
font=None
for candidate in ["C:/Windows/Fonts/arialbd.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
    try:
        font=ImageFont.truetype(candidate,104); break
    except OSError:
        pass
if font:
    d.text((440,666),"PDF",font=font,fill="white",anchor="mm",stroke_width=1)
else:
    d.text((365,625),"PDF",fill="white")
# Blue scissors overlay at lower-right: two rings and crossed blades.
d.line([(590,690),(835,850)],fill=(255,255,255,255),width=48)
d.line([(620,850),(830,680)],fill=(255,255,255,255),width=48)
d.line([(590,690),(835,850)],fill=(13,83,164,255),width=25)
d.line([(620,850),(830,680)],fill=(13,83,164,255),width=25)
for cx,cy in [(565,665),(595,875)]:
    d.ellipse((cx-68,cy-68,cx+68,cy+68),fill=(15,95,180,255),outline=(255,255,255,255),width=18)
    d.ellipse((cx-31,cy-31,cx+31,cy+31),fill=(235,246,255,255))
# Export multi-size Windows icon.
im.save(OUT/"pdf_splitter.ico",format="ICO",sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("Created assets/pdf_splitter.ico")
