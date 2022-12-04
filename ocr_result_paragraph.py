from PySide6 import QtCore

from hocr_data import HOCR_Data
from ocr_result_line import OCRResultLine


class OCRResultParagraph(HOCR_Data):
    def __init__(self, paragraph=None):
        self.lines = []

        if paragraph:
            super().__init__(paragraph['title'])

            for line in paragraph.find_all('span', class_='ocr_line'):
                self.lines.append(OCRResultLine(line))

        else:
            super().__init__()

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

    def write(self, file: QtCore.QDataStream):
        file.writeQVariant(self.bbox)

        file.writeInt16(len(self.lines))

        for line in self.lines:
            line.write(file)

    def read(self, file: QtCore.QDataStream):
        self.bbox = file.readQVariant()

        line_count = file.readInt16()

        for l in range(line_count):
            line = OCRResultLine()
            line.read(file)

