import io
from math import sqrt

import cv2
import numpy
import pytesseract
from bs4 import BeautifulSoup
from iso639 import Lang
from PIL import Image, ImageEnhance
from PySide6 import QtCore, QtGui
from sklearn.cluster import KMeans
import tesserocr as tesserocr

# from collections import Counter
# from matplotlib import image as img
# import matplotlib.pyplot as plt
# import matplotlib.image as mpimg

from ocr_result_block import OCRResultBlock
from ocr_result_line import OCRResultLine
from ocr_result_paragraph import OCRResultParagraph
from ocr_result_word import OCRResultWord


class OCREngine():
    def __init__(self, name: str):
        self.name = name
        self.languages = []

    def pixmap_to_pil(self, pixmap: QtGui.QPixmap) -> Image.Image:
        '''Convert into PIL image format'''
        bytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(bytes)
        buffer.open(QtCore.QIODevice.ReadWrite)
        # pixmap.save(buffer, 'PNG', 100)
        pixmap.save(buffer, 'BMP')
        pil_image = Image.open(io.BytesIO(buffer.data()))
        buffer.close()

        return pil_image

    def recognize_raw(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> str | None:
        return None

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False) -> list[OCRResultBlock] | None:
        return None

    def analyse_layout(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> list[OCRResultBlock] | None:
        return None

    def parse_hocr(self, hocr: str, image_size: QtCore.QSize, px_per_mm: float, language: Lang) -> list[OCRResultBlock]:
        '''Parse box into result block'''
        soup = BeautifulSoup(hocr, 'html.parser')

        blocks = []

        for div in soup.find_all('div', class_='ocr_carea'):
            blocks.append(OCRResultBlock(image_size, px_per_mm, block=div, language=language))

        # Add safety margin sometimes needed for correct recognition
        margin = 5

        for block in blocks:
            block.bbox.adjust(-margin, -margin, margin, margin)

        return blocks

    def add_safety_margin(self, block: OCRResultBlock, margin: int) -> OCRResultBlock:
        '''Add safety margin for better recognition'''
        block.bbox.setTopLeft(block.bbox.translated(-margin, -margin).topLeft())
        block.bbox.setBottomRight(block.bbox.translated(margin, margin).bottomRight())
        return block

    def find_lines(self, image: QtGui.QPixmap) -> list:
        lines = []

        image_cv2 = numpy.array(image.toImage().copy().bits()).reshape((image.height(), image.width(), 4))

        blur = cv2.GaussianBlur(image_cv2, (3, 3), 0)
        sat = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)[:, :, 1]
        thresh = cv2.threshold(sat, 50, 255, cv2.THRESH_BINARY)[1]

        gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
        otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1000, 1))
        dilate = cv2.dilate(otsu, kernel, iterations=2)

        # dilate = cv2.bitwise_not(dilate)

        cnts = cv2.findContours(dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]

        for c in reversed(cnts):
            x, y, w, h = cv2.boundingRect(c)

            lines.append(QtCore.QRect(x, y, w, h))

        return lines


class OCREnginePytesseract(OCREngine):
    def __init__(self) -> None:
        super().__init__('Pytesseract')
        self.languages = pytesseract.get_languages()

    def recognize_text_color(self, image: QtGui.QPixmap) -> QtGui.QColor:
        # TODO: This is much to slow to be useful, find a simpler approach
        image_cv = numpy.array(image.toImage().copy().bits()).reshape((image.height(), image.width(), 4))

        kernel = numpy.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        image_cv = cv2.filter2D(image_cv, -1, kernel)

        final = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)

        final = final.reshape((final.shape[0] * final.shape[1], 3))
        kmeans = KMeans(n_clusters=2)
        kmeans.fit(final)

        r, g, b = kmeans.cluster_centers_[-1]

        white_r, white_g, white_b = (255, 255, 255)
        color_diffs = []
        for color in kmeans.cluster_centers_:
            cr, cg, cb = color
            color_diff = sqrt((white_r - cr)**2 + (white_g - cg)**2 + (white_b - cb)**2)
            color_diffs.append((color_diff, color))

        r, g, b, = sorted(color_diffs, key=lambda x: x[0])[-1][1]

        return QtGui.QColor(r, g, b)

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False, psm_override=3) -> list[OCRResultBlock] | None:
        # TODO: get dpi from boxarea background
        # image.save('/tmp/1.png')
        # estimate: str = pytesseract.image_to_boxes(self.pixmap_to_pil(image))

        # for line in estimate.splitlines():
        #     # char left bottom right top page -> top left / bottom right
        #     m = re.match(r'(.) (\d+) (\d+) (\d+) (\d+) (\d+)', line)

        #     if m:
        #         character = m.group(1)
        #         rects.append(QtCore.QRect(int(m.group(5)), int(m.group(2)), int(m.group(3)), int(m.group(4))))
        #         page = m.group(6)

        # if rects:
        #     # Return top left position of first character and bottom right position of last character
        #     return QtCore.QRect(rects[0].x(), rects[0].y(), rects[-1].right(), rects[-1].bottom())

        # words_rects = []
        # text = ''
        # height = 0
        # height_max = 0
        # estimate: dict = pytesseract.image_to_data(self.pixmap_to_pil(image), output_type=Output.DICT, lang=language.pt2t, config='--oem 2')

        # ret = pytesseract.image_to_data(self.pixmap_to_pil(image), config='--psm 6', output_type=pytesseract.Output.DICT)

        # text = ''

        # line = 0
        # last_line = line

        # for i in range(len(ret['level'])):
        #     line = ret['line_num'][i]

        #     if line != last_line:
        #         text += '\n'
        #         last_line = line

        #     if ret['level'][i] == 5:
        #         text += ret['text'][i] + ' '

        # print(text)

        blocks = []

        paragraph = OCRResultParagraph()

        if raw:
            # Preprocess the image to find lines and scan line by line, maintaining whitespace

            lines = self.find_lines(image)

            for line in lines:
                line_str = pytesseract.image_to_string(self.pixmap_to_pil(image.copy(line)), config='-c preserve_interword_spaces=1 --psm 7').strip()

                # ar = w / float(h)
                # # if ar < 5:
                # cv2.drawContours(image_cv2, [c], -1, (255, 0, 0), -1)

                # for line_str in lines:
                if line_str:
                    word = OCRResultWord()
                    word.text = line_str

                    line = OCRResultLine()
                    line.words.append(word)

                    paragraph.lines.append(line)

            block = OCRResultBlock(image.size(), px_per_mm)
            block.font = QtGui.QFontDatabase().systemFont(QtGui.QFontDatabase().SystemFont.FixedFont)
            block.paragraphs.append(paragraph)

            blocks = [block]
        else:
            hocr = pytesseract.image_to_pdf_or_hocr(self.pixmap_to_pil(image), extension='hocr', lang=language.pt2t, config=f'--psm {psm_override}')

            if isinstance(hocr, bytes):
                blocks = self.parse_hocr(hocr.decode(), image.size(), px_per_mm, language)

                # for block in blocks:
                #     block.foreground_color = self.recognize_text_color(image.copy(block.bbox))

        return blocks


class OCREngineTesserocr(OCREngine):
    def __init__(self):
        super().__init__('TesserOCR')
        self.languages = tesserocr.get_languages()[1]

    def pixmap_strip_header_footer(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> QtGui.QPixmap:
        rect = image.rect()
        rect.setTop(from_header)
        if to_footer:
            rect.setBottom(to_footer)
        return image.copy(rect)

    def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False) -> list[OCRResultBlock] | None:
        blocks = []

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO, lang=language.pt2t) as api:
            api.SetImage(self.pixmap_to_pil(image))
            api.Recognize()
            hocr = api.GetHOCRText(0)

            blocks = self.parse_hocr(hocr, image.size(), px_per_mm, language)

            #TODO: SetSourceResolution
            # TODO: SetRectangle (for multiple OCRs in one step)
            # TODO: GetTextlines (before recognition)
            # TODO: GetWords (before recognition)

        return blocks

    def recognize_raw(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> list[OCRResultBlock] | None:
        blocks = []

        # with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.SINGLE_BLOCK, lang=language.pt2t) as api:
        #     api.SetImage(self.pixmap_to_pil(image))
        #     api.Recognize()
        #     hocr = api.GetHOCRText(0)

        #     blocks = self.parse_hocr(hocr, image.size(), px_per_mm, language)

        return blocks

    # def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False, psm_override=3) -> list[OCRResultBlock] | None:

    def analyse_layout(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> list[OCRResultBlock] | None:
        blocks = []

        margin = 5

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO_ONLY) as api:
            api.SetImage(self.pixmap_to_pil(self.pixmap_strip_header_footer(image, from_header, to_footer)))
            tess_blocks = api.GetComponentImages(tesserocr.RIL.BLOCK, True)

            for tess_block in tess_blocks:
                image, bbox, block_id, paragraph_id = tess_block

                block = OCRResultBlock()
                block.bbox = QtCore.QRect(bbox['x'], bbox['y'] + from_header, bbox['w'], bbox['h'])

                block = self.add_safety_margin(block, margin)

                blocks.append(block)

        return blocks


class OCREngineManager():
    def __init__(self, engines=[]) -> None:
        self.engines = engines

        # TODO: Use last engine in list for now
        self.current_engine = engines[-1]

    def get_current_engine(self) -> OCREngine:
        return self.current_engine
