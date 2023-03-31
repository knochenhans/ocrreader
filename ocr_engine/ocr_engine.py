import io
from abc import abstractmethod
from dataclasses import dataclass, field
from math import sqrt

import cv2  # type: ignore
import numpy
import tesserocr as tesserocr  # type: ignore
from iso639 import Lang
from PIL import Image
from PySide6 import QtCore, QtGui

# from box_editor.box_editor_scene import Box
from ocr_engine.ocr_results import OCRResultBlock


@dataclass
class OCREngine():
    name: str = ''
    languages: list[str] = field(default_factory=list)
    threadpool: QtCore.QThreadPool = QtCore.QThreadPool()

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

    # def recognize_raw(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> str | None:
    #     return None

    # def recognize(self, image: QtGui.QPixmap, ppi: float, language: Lang = Lang('English'), raw=False) -> list[OCRResultBlock] | None:
    #     return None

    @abstractmethod
    def start_recognize_thread(self, callback, box, image: QtGui.QPixmap, ppi: float, language: Lang = Lang('English'), raw=False):
        pass

    @abstractmethod
    def analyse_layout(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> list[OCRResultBlock] | None:
        return None

    # def parse_hocr(self, hocr: str, image_size: QtCore.QSize, ppi: float, language: Lang) -> list[HOCR_OCRResultBlock]:
    #     '''Parse box into result block'''
    #     soup = BeautifulSoup(hocr, 'html.parser')

    #     blocks = []

    #     for div in soup.find_all('div', class_='ocr_carea'):
    #         if isinstance(div, Tag):
    #             block = HOCR_OCRResultBlock(image_size=image_size, ppi=ppi, language=language)
    #             block.split_title_data(div)
    #             blocks.append(block)

    #     # Add safety margin sometimes needed for correct recognition
    #     margin = 5

    #     for block in blocks:
    #         block.bbox.adjust(-margin, -margin, margin, margin)

    #     return blocks

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


class OCREngineManager():
    def __init__(self, engines=[]) -> None:
        self.engines = engines

        # TODO: Use last engine in list for now
        self.current_engine = engines[-1]

    def get_current_engine(self) -> OCREngine:
        return self.current_engine
