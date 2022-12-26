from dataclasses import dataclass, field

from PySide6 import QtCore

from hocr_data import HOCR_Data
from hocr_ocr_result_word import HOCR_OCRResultWord


@dataclass
class HOCR_OCRResultLine(HOCR_Data):
    x_size = 0.0
    baseline = (0.0, 0)
    words: list[HOCR_OCRResultWord] = field(default_factory=list)

    def split_title_data(self, line):
        if line:
            self.title_data = line['title']
            super().split_title_data()

            data_lines = self.title_data.split('; ')

            for data_line in data_lines:
                tokens = data_line.split(' ')

                if tokens[0] == 'x_size':
                    self.x_size = float(tokens[1])
                elif tokens[0] == 'baseline':
                    self.baseline = (float(tokens[1]), int(tokens[2]))

            for span in line.find_all('span', class_='ocrx_word'):
                word = HOCR_OCRResultWord()
                word.split_title_data(span)
                self.words.append(word)

    def translate(self, distance: QtCore.QPoint):
        '''Translate coordinates by a distance'''

        self.bbox = self.bbox.translated(distance)

        for word in self.words:
            word.translate(distance)

    def write(self, file: QtCore.QDataStream):
        file.writeQVariant(self.bbox)
        file.writeFloat(self.x_size)

        file.writeFloat(self.baseline[0])
        file.writeInt16(self.baseline[1])

        file.writeInt16(len(self.words))

        for word in self.words:
            word.write(file)

    def read(self, file: QtCore.QDataStream):
        self.bbox = file.readQVariant()
        self.x_size = file.readFloat()

        baseline = (file.readFloat(), file.readInt16())
        self.baseline = baseline

        words_count = file.readInt16()

        for w in range(words_count):
            word = HOCR_OCRResultWord()
            word.read(file)
            self.words.append(word)
