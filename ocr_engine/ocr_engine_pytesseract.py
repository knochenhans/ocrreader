import cv2
import numpy
import pytesseract
from iso639 import Lang
from hocr_ocr_result_block import (HOCR_OCRResultBlock, OCRResultLine,
                              HOCR_OCRResultParagraph, HOCR_OCRResultWord)
from PySide6 import QtCore, QtGui
from sklearn.cluster import KMeans

from ocr_engine import OCREngine


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

    def recognize(self, image: QtGui.QPixmap, ppi: float, language: Lang = Lang('English'), raw=False, psm_override=3) -> list[HOCR_OCRResultBlock] | None:
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

        blocks: list[HOCR_OCRResultBlock] = []

        paragraph = HOCR_OCRResultParagraph()

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
                    word = HOCR_OCRResultWord()
                    word.text = line_str

                    line = OCRResultLine()
                    line.words.append(word)

                    paragraph.lines.append(line)

            block = HOCR_OCRResultBlock(image_size=image.size(), ppi=ppi)
            block.font = QtGui.QFontDatabase().systemFont(QtGui.QFontDatabase().SystemFont.FixedFont)
            block.paragraphs.append(paragraph)

            blocks = [block]
        else:
            hocr = pytesseract.image_to_pdf_or_hocr(self.pixmap_to_pil(image), extension='hocr', lang=language.pt2t, config=f'--psm {psm_override}')

            if isinstance(hocr, bytes):
                blocks = self.parse_hocr(hocr.decode(), image.size(), ppi, language)

                # for block in blocks:
                #     block.foreground_color = self.recognize_text_color(image.copy(block.bbox))

        return blocks