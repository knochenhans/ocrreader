from PySide6 import QtCore


class HOCR_Data():
    def __init__(self, title_data: str = '') -> None:
        self.bbox = QtCore.QRect()

        if title_data:
            data_lines = title_data.split('; ')

            for data_line in data_lines:
                tokens = data_line.split(' ')

                if tokens[0] == 'bbox':
                    self.bbox = QtCore.QRect(int(tokens[1]), int(tokens[2]), int(tokens[3]) - int(tokens[1]), int(tokens[4]) - int(tokens[2]))

    def translate(self, distance: QtCore.QPoint) -> None:
        pass
