import unittest
from property_editor import DocumentHelper
from PySide6 import QtGui

class HyphenRemoverTest(unittest.TestCase):
    def test1(self):
        document = QtGui.QTextDocument()
        # document.setHtml('<p><span>Test, um</span><span> festzu-</span></p>\n<p><span>stellen, ob</span><span> Hypen-</span></p>\n<p><span>Remover auch wirk-</span></p>\n<p><span>lich funktioniert.</span></p><p><span>Denn das wäre toll!</span><span> 12-3-</span></p><p><span>4</span></p>')
        document.setHtml('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n<html><head><meta name="qrichtext" content="1" /><meta charset="utf-8" /><style type="text/css">\np, li { white-space: pre-wrap; }\nhr { height: 1px; border-width: 0; }\nli.unchecked::marker { content: "\\2610"; }\nli.checked::marker { content: "\\2612"; }\n</style></head><body style=" font-family:\'Sans\'; font-size:10pt; font-weight:400; font-style:normal;">\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">mit</span><span style=" font-size:9pt;"> dem </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.094118);">Amiga«</span><span style=" font-size:9pt;"> fehlt nicht.</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Dort wird auf die Benutzung</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.117647);">von</span><span style=" font-size:9pt;"> damals schon erhältlichen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Programmen wie Graphicraft,</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Deluxe-Paint, Textcraft und</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Musicraft eingegangen.</span></p>\n<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:9pt;"><br /></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Auch die »Grundlagen des</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">CLI« kommen nicht zu kurz, ih-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">nen ist ein eigener Teil des Bu-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">ches</span><span style=" font-size:9pt;"> gewidmet. In direktem</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">Zusammenhang</span><span style=" font-size:9pt;"> dazu stehen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">auch die Dateien und Dateiver-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">zeichnisse </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">und</span><span style=" font-size:9pt;"> deren Ge-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">brauch vom </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.117647);">CLI</span><span style=" font-size:9pt;"> </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.117647);">aus.</span><span style=" font-size:9pt;"> Außer-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">dem werden </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">sämtliche</span><span style=" font-size:9pt;"> </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">Kom-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.101961);">mandos</span><span style=" font-size:9pt;"> des </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">CLI/beschrieben,</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">wobei</span><span style=" font-size:9pt;"> der Text-Editor »ed« ein</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">eigenes Kapitel füllt. Nachdem</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">dieser Teil des Buches mit eini-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">gen wichtigen Tips für das </span><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">CLI</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">abgeschlossen</span><span style=" font-size:9pt;"> wurde, folgen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Kapitel über die Chips, Grafik,</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Sound, und die Schnittstellen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">des Amiga. Abschließend fin-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">den sich Hinweise über die</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Programmierung aller Spra-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.094118);">chen,</span><span style=" font-size:9pt;"> speziell wird dabei auf</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Basic eingegangen. Dazu sei</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">aber bemerkt, daß die letzten</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Kapitel nicht mehr sehr um-</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">fangreich sind und mehr zur</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Abrundung des 450 Seiten</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">starken Werks dienen. Das</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Buch kann allen Anfängern</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">empfohlen werden, die einen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Begleiter auf der Reise in die</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt;">Welt des Amiga nicht missen</span></p>\n<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-size:9pt; background-color:rgba(255,0,0,0.082353);">wollen.</span><span style=" font-size:9pt;"> (M.Marek/rb)</span></p></body></html>')
        document_helper = DocumentHelper(document, 'de')

        text_correct = 'mit dem Amiga« fehlt nicht. Dort wird auf die Benutzung von damals schon erhältlichen Programmen wie Graphicraft, Deluxe-Paint, Textcraft und Musicraft eingegangen.\n\nAuch die »Grundlagen des CLI« kommen nicht zu kurz, ihnen ist ein eigener Teil des Buches gewidmet. In direktem Zusammenhang dazu stehen auch die Dateien und Dateiverzeichnisse und deren Gebrauch vom CLI aus. Außerdem werden sämtliche Kommandos des CLI/beschrieben, wobei der Text-Editor »ed« ein eigenes Kapitel füllt. Nachdem dieser Teil des Buches mit einigen wichtigen Tips für das CLI abgeschlossen wurde, folgen Kapitel über die Chips, Grafik, Sound, und die Schnittstellen des Amiga. Abschließend finden sich Hinweise über die Programmierung aller Sprachen, speziell wird dabei auf Basic eingegangen. Dazu sei aber bemerkt, daß die letzten Kapitel nicht mehr sehr umfangreich sind und mehr zur Abrundung des 450 Seiten starken Werks dienen. Das Buch kann allen Anfängern empfohlen werden, die einen Begleiter auf der Reise in die Welt des Amiga nicht missen wollen. (M.Marek/rb)'

        self.maxDiff = None
        self.assertEqual(document_helper.remove_hyphens().toPlainText(), text_correct)


if __name__ == '__main__':
    unittest.main()
