from dataclasses import dataclass, field
import ntpath

from iso639 import Lang
from papersize import SIZES, parse_length
from PySide6 import QtCore, QtGui

from box_editor.box_data import BoxData


@dataclass
class Page():
    image_path: str = ''
    name: str = ''
    #self.blocks = []
    box_datas: list[BoxData] = field(default_factory=list)
    paper_size: str = ''

    def __post_init__(self):
        self.set_paper_size(self.paper_size)

    def set_paper_size(self, paper_size):
        self.paper_size = paper_size
        if paper_size:
            self.ppi = self.calc_density(SIZES[paper_size])
        else:
            # Let's assume 300 ppi as a fallback value for now
            self.ppi = 300.0

    def calc_density(self, paper_size: str) -> float:
        # TODO: Let's assume 1:1 pixel ratio for now, so ignore width
        height_in = int(parse_length(paper_size.split(' x ')[1], 'in'))

        return QtGui.QImage(self.image_path).size().height() / height_in

    def write(self, file: QtCore.QDataStream):
        file.writeString(self.image_path)
        file.writeString(self.name)
        file.writeString(self.paper_size)
        file.writeFloat(self.ppi)

        file.writeInt16(len(self.box_datas))

        for box_datas in self.box_datas:
            box_datas.write(file)

    def read(self, file: QtCore.QDataStream):
        self.image_path = file.readString()
        self.name = file.readString()
        self.paper_size = file.readString()
        self.ppi = file.readFloat()

        box_datas_count = file.readInt16()

        for b in range(box_datas_count):
            box_data = BoxData()
            box_data.read(file)
            self.box_datas.append(box_data)

    def clear(self):
        self.box_datas.clear()


@dataclass
class Project():
    name: str = ''
    default_language: Lang = Lang('English')
    default_paper_size: str = 'a4'
    current_page_idx: int = 0
    pages: list[Page] = field(default_factory=list)
    header_y: float = 0.0
    footer_y: float = 0.0
    remove_hyphens = False

    # Save format revision for loading
    format_revision = 7

    # def add_page(self, image_path: str, paper_size: str = SIZES['a4']) -> None:
    #     self.pages.append(Page(image_path, ntpath.basename(image_path), paper_size))

    def add_page(self, page: Page):
        self.pages.append(page)

    def remove_page(self, page: Page):
        self.pages.remove(page)

    def write(self, file: QtCore.QDataStream):
        file.writeInt16(self.format_revision)
        file.writeString(self.name)
        file.writeString(self.default_language.name)
        file.writeString(self.default_paper_size)
        file.writeInt16(self.current_page_idx)
        file.writeFloat(self.header_y)
        file.writeFloat(self.footer_y)
        file.writeBool(self.remove_hyphens)

        file.writeInt16(len(self.pages))
        for page in self.pages:
            page.write(file)

    def read(self, file: QtCore.QDataStream):
        format_revision = file.readInt16()

        if format_revision != self.format_revision:
            raise ValueError(f'Revision of project file is {format_revision} is incompatible with {self.format_revision}. Project file cannot be loaded')

        self.name = file.readString()
        self.default_language = Lang(file.readString())
        self.default_paper_size = file.readString()
        self.current_page_idx = file.readInt16()
        self.header_y = file.readFloat()
        self.footer_y = file.readFloat()
        self.remove_hyphens = file.readBool()

        page_count = file.readInt16()
        for p in range(page_count):
            page = Page()
            page.read(file)
            self.add_page(page)
