from abc import abstractmethod
from dataclasses import dataclass

from PySide6 import QtCore


@dataclass
class HOCR_Data():
    title_data: str = ''
    bbox: QtCore.QRect = QtCore.QRect()

    def split_title_data(self):
        if self.title_data:
            data_lines = self.title_data.split('; ')

            for data_line in data_lines:
                tokens = data_line.split(' ')

                if tokens[0] == 'bbox':
                    self.bbox = QtCore.QRect(int(tokens[1]), int(tokens[2]), int(tokens[3]) - int(tokens[1]), int(tokens[4]) - int(tokens[2]))

    @abstractmethod
    def translate(self, distance: QtCore.QPoint) -> None:
        pass
