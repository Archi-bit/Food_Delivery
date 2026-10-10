"""Original procedural food illustrations. No external assets or APIs."""
import math
import random
from io import BytesIO
from PIL import Image, ImageDraw


def artwork(index, kind='Основное'):
    rng = random.Random(index)
    im = Image.new('RGB', (1000, 650), ['#f2dfc6', '#dce9d5', '#eed2bf', '#dce5e9'][index % 4])
    d = ImageDraw.Draw(im)
    # Tablecloth lines and plate shadows.
    for x in range(-650, 1200, 120):
        d.line((x, 0, x+650, 650), fill='#ffffff', width=2)
    d.ellipse((247, 64, 797, 614), fill='#c4baa4')
    d.ellipse((225, 40, 775, 590), fill='#fffcf3')
    d.ellipse((255, 70, 745, 560), outline='#e9e1d0', width=3)
    if kind == 'Пицца':
        d.ellipse((285, 100, 715, 530), fill='#c78744')
        d.ellipse((302, 117, 698, 513), fill='#e3b863')
        for _ in range(16):
            x, y = rng.randint(350, 625), rng.randint(155, 435)
            d.ellipse((x, y, x+40, y+40), fill='#bd4e38', outline='#e78963', width=3)
            d.ellipse((x+25, y-12, x+40, y+5), fill='#52713f')
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            d.line((500, 315, 500+205*math.cos(rad), 315+205*math.sin(rad)), fill='#af7537', width=3)
    elif kind == 'Салаты':
        for _ in range(75):
            x, y = rng.randint(310, 645), rng.randint(130, 460)
            d.ellipse((x, y, x+rng.randint(30, 70), y+rng.randint(20, 45)), fill=rng.choice(['#67994b', '#83ae56', '#487b47']))
        for _ in range(20):
            x, y = rng.randint(330, 620), rng.randint(160, 425)
            d.ellipse((x, y, x+35, y+28), fill='#d26542')
            d.rectangle((x+32, y+26, x+50, y+43), fill='#f9efd5')
    elif kind == 'Десерты':
        d.polygon([(350, 400), (650, 430), (560, 200), (350, 300)], fill='#c3865c')
        d.polygon([(350, 300), (650, 330), (650, 430), (350, 400)], fill='#e1b98a')
        for y in [330, 360, 390]:
            d.line((350, y, 650, y+30), fill='#fff1cf', width=12)
        d.polygon([(350, 300), (650, 330), (560, 190)], fill='#f5dfb5')
        for x, y in [(530, 220), (560, 250), (590, 270), (490, 260)]:
            d.ellipse((x, y, x+27, y+27), fill='#a84746')
        d.ellipse((540, 200, 570, 210), fill='#51845d')
    elif kind == 'Напитки':
        d.rounded_rectangle((345, 110, 650, 510), radius=35, fill='#e2ebdf', outline='#9cb5a2', width=7)
        d.rounded_rectangle((365, 200, 630, 488), radius=20, fill=['#ce7255', '#d7b34e'][index % 2])
        d.ellipse((365, 177, 630, 235), fill='#f5d784')
        for x, y in [(390, 250), (470, 280), (540, 245)]:
            d.rounded_rectangle((x, y, x+55, y+60), radius=9, fill='#f6e8ca')
        d.line((565, 360, 605, 75), fill='#f8f6e8', width=15)
        d.ellipse((290, 365, 410, 485), fill='#759348')
        d.ellipse((300, 375, 400, 475), fill='#d8dc87')
        for angle in range(0, 360, 60):
            rad=math.radians(angle)
            d.line((350,425,350+46*math.cos(rad),425+46*math.sin(rad)),fill='#f9f2c7',width=3)
    elif kind == 'Завтраки':
        for x, y in [(345, 155), (510, 155), (420, 325)]:
            d.ellipse((x, y, x+140, y+120), fill='#bb8648')
            d.ellipse((x+8, y+8, x+132, y+106), fill='#e9bc68')
            d.ellipse((x+30, y+20, x+80, y+60), fill='#fff4de')
        for _ in range(18):
            x,y=rng.randint(330,620),rng.randint(135,450)
            d.ellipse((x,y,x+15,y+14),fill='#c45249')
    elif index % 3 == 1:
        # Pleated dumplings, each with a visible folded centre.
        for x,y in [(335,135),(485,125),(405,270),(555,275),(320,400)]:
            d.ellipse((x,y,x+120,y+90),fill='#d9bb83')
            d.ellipse((x,y-10,x+115,y+72),fill='#f1dfb7')
            for offset in [-28,-10,10,28]:
                d.line((x+55,y+35,x+55+offset,y),fill='#bd9e6c',width=3)
            d.line((x+55,y+8,x+55,y+65),fill='#bd9e6c',width=4)
    else:
        d.ellipse((290, 105, 710, 525), fill='#d9a957')
        for _ in range(260):
            x,y=rng.randint(320,670),rng.randint(125,495)
            if ((x-500)/185)**2+((y-315)/185)**2<1:
                d.line((x,y,x+10,y+3),fill=rng.choice(['#f6d991','#edc575','#d9ad50']),width=3)
        for _ in range(24):
            x,y=rng.randint(360,610),rng.randint(180,420)
            d.rounded_rectangle((x,y,x+32,y+22),radius=6,fill=rng.choice(['#855743','#b26d46','#df7c38']))
        for _ in range(14):
            x,y=rng.randint(350,640),rng.randint(170,440)
            d.ellipse((x,y,x+15,y+9),fill='#527644')
    out=BytesIO()
    im.resize((800,520),Image.Resampling.LANCZOS).save(out,'JPEG',quality=90)
    return out.getvalue()
