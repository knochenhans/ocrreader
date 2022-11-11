from iso639 import Lang
from papersize import SIZES


class Project():
    def __init__(self, name='New Project', language: Lang = Lang('English'), papersize=SIZES['a4']):
        self.name = name
        self.language = language
        self.papersize = papersize
