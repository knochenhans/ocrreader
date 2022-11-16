from PySide6 import QtCore

from hocrdata import HOCR_Data
from ocr_result_line import OCRResultLine


class OCRResultParagraph(HOCR_Data):
    def __init__(self, paragraph):
        super().__init__(paragraph['title'])
        self.lines = []

        for line in paragraph.find_all('span', class_='ocr_line'):
            self.lines.append(OCRResultLine(line))

    def get_avg_height(self) -> int:
        sum_height = 0

        for line in self.lines:
            sum_height += line.x_size

        return round(sum_height / len(self.lines))

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

        for line in self.lines:
            line.translate(distance)
