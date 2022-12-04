from PySide6 import QtCore

from hocr_data import HOCR_Data
from ocr_result_word import OCRResultWord


class OCRResultLine(HOCR_Data):
    def __init__(self, line=None):
        self.x_size = 0.0
        self.baseline = (0.0, 0)
        self.words = []

        if line:
            title_data = line['title']
            super().__init__(title_data)

            data_lines = title_data.split('; ')

            for data_line in data_lines:
                tokens = data_line.split(' ')

                if tokens[0] == 'x_size':
                    self.x_size = float(tokens[1])
                elif tokens[0] == 'baseline':
                    self.baseline = (float(tokens[1]), int(tokens[2]))

            for word in line.find_all('span', class_='ocrx_word'):
                self.words.append(OCRResultWord(word))
        else:
            super().__init__()

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
            word = OCRResultWord()
            word.read(file)
            self.words.append(word)
