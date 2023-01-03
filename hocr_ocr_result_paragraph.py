from dataclasses import dataclass, field

from bs4 import Tag
from PySide6 import QtCore

from hocr_data import HOCR_Data
from hocr_ocr_result_line import HOCR_OCRResultLine


@dataclass
class HOCR_OCRResultParagraph(HOCR_Data):
    lines: list[HOCR_OCRResultLine] = field(default_factory=list)

    def split_title_data(self, paragraph):
        if paragraph:
            self.title_data = paragraph['title']
            super().split_title_data()

            for span in paragraph.find_all('span', class_='ocr_line'):
                line = HOCR_OCRResultLine()
                line.split_title_data(span)
                self.lines.append(line)

    # def get_avg_height(self) -> int:
    #     sum_height = 0

    #     for line in self.lines:
    #         sum_height += line.x_size

    #     return round(sum_height / len(self.lines))

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
            line = HOCR_OCRResultLine()
            line.read(file)
