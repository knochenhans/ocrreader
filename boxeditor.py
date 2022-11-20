import math

import enchant
from iso639 import Lang
from odf import style
from odf import text as odftext
from odf.opendocument import OpenDocumentText
from odf.text import P
from PySide6 import QtCore, QtGui, QtWidgets

from boxproperties import BOX_PROPERTY_TYPE, BoxProperties
from ocrengine import OCREngineManager
from project import Page, Project


class BoxColor():
    '''Color properties to represent different box types'''

    def __init__(self, brush: QtGui.QBrush = QtGui.QBrush(), pen: QtGui.QPen = QtGui.QPen(), brush_selected: QtGui.QBrush = QtGui.QBrush(), pen_selected: QtGui.QPen = QtGui.QPen()):
        self.brush = brush
        self.pen = pen
        self.brush_selected = brush_selected
        self.pen_selected = pen_selected


class BoxEditor(QtWidgets.QGraphicsView):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project) -> None:
        super().__init__(parent)

        self.project = project
        self.property_editor = property_editor
        self.current_page = None
        self.custom_scene = BoxEditorScene(self, engine_manager, self.property_editor, self.project, None)
        self.setScene(self.custom_scene)
        self.origin = QtCore.QPoint()
        self.current_scale = 1.0

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)
        self.setDisabled(True)

    def load_page(self, page: Page):
        self.custom_scene.clear()
        self.custom_scene.box_counter = 0
        self.custom_scene.current_box = None
        self.custom_scene.set_page_as_background(page)

        self.setEnabled(True)
        self.current_page = page
        self.custom_scene.current_page = self.current_page

        for box_property in page.box_properties:
            # Restore existing boxes for this page
            self.custom_scene.restore_box(box_property)

        self.property_editor.recognition_widget.reset()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        '''Handle zooming and scrolling by mouse'''

        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            scaleFactor = 1.02
            degrees = event.angleDelta().y()
            if degrees > 0:
                self.current_scale *= scaleFactor
            else:
                self.current_scale /= scaleFactor

            self.resetTransform()
            self.scale(self.current_scale, self.current_scale)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        '''Setup movement by mouse'''
        if event.buttons() == QtCore.Qt.MiddleButton:
            self.origin = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        '''Handle movement by mouse'''
        if event.buttons() == QtCore.Qt.MiddleButton:
            oldPoint = self.mapToScene(self.origin)
            newPoint = self.mapToScene(event.pos())
            translation = newPoint - oldPoint

            self.translate(translation.x(), translation.y())

            self.origin = event.pos()

        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # Get selected boxes:
        boxes = self.get_boxes(True)

        match event.key():
            # case QtCore.Qt.Key_A:
            #     self.auto_align()
            case QtCore.Qt.Key_I:
                for box in boxes:
                    box.set_type_to_image()
            case QtCore.Qt.Key_T:
                for box in boxes:
                    box.set_type_to_text()
            case QtCore.Qt.Key_R:
                for box in boxes:
                    box.recognize_text()
            case QtCore.Qt.Key_Delete:
                for box in boxes:
                    self.scene().remove_box(box)
            case _:
                super().keyPressEvent(event)

    def get_boxes(self, only_selected: bool = False) -> list:
        boxes = []

        for item in self.scene().items():
            if isinstance(item, Box):
                if only_selected:
                    if item in self.scene().selectedItems():
                        boxes.append(item)
                else:
                    boxes.append(item)

        boxes.sort(key=lambda x: x.properties.order)
        return boxes

    def export_odt(self):
        # text = QtGui.QTextDocument()
        # cursor = QtGui.QTextCursor(text)

        boxes = self.get_boxes(False)

        textdoc = OpenDocumentText()

        for b, box in enumerate(boxes):
            # cursor.insertHtml(box.properties.ocr_result_block.get_text().toHtml())

            # if b < (len(boxes) - 1):
            # cursor.insertText('\n\n')

            p = P(text=box.properties.ocr_result_block.get_text(self.project.default_paper_size).toPlainText())
            textdoc.text.addElement(p)

        textdoc.save('/tmp/headers.odt')

        # print(text.toPlainText())


class Box(QtWidgets.QGraphicsRectItem):
    text_recognized = QtCore.Signal(str)

    def __init__(self, rect: QtCore.QRectF, engine_manager: OCREngineManager, scene) -> None:
        super().__init__(rect, parent=None)

        self.engine_manager = engine_manager
        self.scene_ = scene

        self.moving = False

        # Setup order number for painting
        self.number_widget = QtWidgets.QGraphicsSimpleTextItem(self)
        self.number_widget.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Setup recognition checkmark symbol for painting
        checkmark = QtGui.QPixmap('resources/icons/check-line.png').scaledToWidth(16, QtCore.Qt.SmoothTransformation)
        self.recognized_widget = QtWidgets.QGraphicsPixmapItem(checkmark, self)
        self.recognized_widget.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        self.recognized_widget.hide()

        self.setAcceptHoverEvents(True)

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsFocusable)

        self.properties = BoxProperties()
        self.properties.language = self.scene_.project.default_language

        self.setRect(rect)
        self.updateProperties()

        # Define colors for different box types

        # Text box

        brush_text = QtGui.QBrush(QtGui.QColor(94, 156, 235, 150))
        brush_text.setStyle(QtCore.Qt.SolidPattern)

        brush_text_selected = brush_text

        pen_text = QtGui.QPen(QtGui.QColor(94, 156, 235, 150))
        pen_text.setWidth(2)
        pen_text.setStyle(QtCore.Qt.SolidLine)
        pen_text.setCosmetic(False)

        pen_text_selected = pen_text
        pen_text_selected = QtGui.QPen(QtGui.QColor(94, 156, 235, 255))
        pen_text_selected.setWidth(3)

        self.color_text = BoxColor(brush_text, pen_text, brush_text_selected, pen_text_selected)

        # Image box

        brush_image = brush_text
        brush_image = QtGui.QBrush(QtGui.QColor(227, 35, 35, 150))

        brush_image_selected = brush_image

        pen_image = pen_text
        pen_image = QtGui.QPen(QtGui.QColor(227, 35, 35, 150))

        pen_image_selected = pen_image
        pen_image_selected = QtGui.QPen(QtGui.QColor(227, 35, 35, 255))

        self.color_image = BoxColor(brush_image, pen_image, brush_image_selected, pen_image_selected)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Handle scaling via mouse'''
        if self.moving:
            self.scene().clearSelection()
            self.setSelected(True)
            self.prepareGeometryChange()
            pos = event.pos().toPoint()

            rect = self.rect()

            if self.left:
                rect.setLeft(pos.x())
            if self.right:
                rect.setRight(pos.x())
            if self.top:
                rect.setTop(pos.y())
            if self.bottom:
                rect.setBottom(pos.y())

            self.setRect(rect.normalized())
            self.update()
            self.updateProperties()
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.LeftButton:
            self.origin_rect = self.rect()
            if self.left or self.right or self.top or self.bottom:
                self.moving = True
            else:
                super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.moving = False
        self.updateProperties()
        super().mouseReleaseEvent(event)

    def updateProperties(self) -> None:
        '''Update properties with current box position'''
        self.properties.rect = QtCore.QRectF(self.mapToScene(self.rect().topLeft()), self.mapToScene(self.rect().bottomRight())).toAlignedRect()

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: QtWidgets.QWidget) -> None:
        '''Paint background and border using colors defined by type and update order number item'''
        color = BoxColor()

        if self.properties.type == BOX_PROPERTY_TYPE.TEXT:
            color = self.color_text
        else:
            color = self.color_image

        if self.isSelected():
            painter.setPen(color.pen_selected)
            painter.setBrush(color.brush_selected)
        else:
            painter.setPen(color.pen)
            painter.setBrush(color.brush)

        painter.drawRect(self.rect())

        # TODO: Position not working correctly with ItemIgnoresTransformations
        # Update ordner number
        self.number_widget.setText(str(self.properties.order + 1))

        pos = self.rect().bottomLeft()
        pos.setX(pos.x() + 5)
        pos.setY(pos.y() - self.number_widget.boundingRect().height() - 10)
        br = self.mapToScene(pos)
        self.number_widget.setPos(self.mapFromScene(br))

        # Update recognition checkmark
        if self.properties.recognized:
            pos = self.rect().bottomLeft()
            pos.setX(pos.x() + self.number_widget.boundingRect().width() + 5)
            pos.setY(pos.y() - self.recognized_widget.boundingRect().height() - 10)
            br = self.mapToScene(pos)
            self.recognized_widget.setPos(self.mapFromScene(br))
            self.recognized_widget.show()
        else:
            self.recognized_widget.hide()

        # Update word confidence visualisation
        if self.properties.words:
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

            for word in self.properties.words:
                if word.confidence < 90:
                    painter.setBrush(QtGui.QColor(255, 0, 0, (1 - (word.confidence / 100)) * 200))
                    painter.drawRect(word.bbox.translated(self.rect().topLeft().toPoint()))

        # Paragraphs
        if self.properties.ocr_result_block:
            paragraphs = self.properties.ocr_result_block.paragraphs
            if paragraphs:
                if len(paragraphs) > 1:
                    for p, paragraph in enumerate(self.properties.ocr_result_block.paragraphs):
                        if p > 0:
                            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 150), 0, QtCore.Qt.SolidLine))
                            rect = paragraph.bbox.translated(self.rect().topLeft().toPoint())
                            painter.drawLine(rect.topLeft(), rect.topRight())

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        '''Show size grips at the box' margin'''
        self.top = False
        self.right = False
        self.bottom = False
        self.left = False

        cursor = QtGui.QCursor(QtGui.Qt.ArrowCursor)
        if math.isclose(event.pos().x(), self.rect().x(), rel_tol=0.01):
            self.left = True
        if math.isclose(event.pos().x(), self.rect().x() + self.rect().width(), rel_tol=0.01):
            self.right = True
        if math.isclose(event.pos().y(), self.rect().y(), rel_tol=0.01):
            self.top = True
        if math.isclose(event.pos().y(), self.rect().y() + self.rect().height(), rel_tol=0.01):
            self.bottom = True

        if self.top or self.bottom:
            cursor = QtGui.QCursor(QtGui.Qt.SizeVerCursor)
        if self.left or self.right:
            cursor = QtGui.QCursor(QtGui.Qt.SizeHorCursor)

        if self.top and self.right or self.bottom and self.left:
            cursor = QtGui.QCursor(QtGui.Qt.SizeBDiagCursor)
        if self.top and self.left or self.bottom and self.right:
            cursor = QtGui.QCursor(QtGui.Qt.SizeFDiagCursor)

        self.setCursor(cursor)

        super().hoverMoveEvent(event)

    def contextMenuEvent(self, event: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        self.menu = QtWidgets.QMenu()

        text_action = QtGui.QAction('Text')
        text_action.triggered.connect(self.set_type_to_text)

        self.menu.addAction(text_action)

        image_action = QtGui.QAction('Image')
        image_action.triggered.connect(self.set_type_to_image)

        self.menu.addAction(image_action)

        if self.properties.type == BOX_PROPERTY_TYPE.TEXT:
            read_action = QtGui.QAction('Read')
            read_action.triggered.connect(self.recognize_text)
            self.menu.addAction(read_action)

            auto_align_action = QtGui.QAction('Auto align')
            auto_align_action.triggered.connect(self.auto_align)
            self.menu.addAction(auto_align_action)

        self.menu.exec(event.screenPos())

    def auto_align(self) -> None:
        '''Automatically align box to recognized text'''
        # engine = self.engine_manager.get_current_engine()

        # block = engine.read(self.get_image(), self.properties.language)

        # if block:
        #     final_rect = QtCore.QRect(self.properties.rect.x() + block.bbox.x(), self.properties.rect.y() + block.bbox.y(), block.bbox.width(), block.bbox.height())
        #     self.properties.rect = final_rect
        #     self.setRect(final_rect)
        #     self.properties.recognized = True

        # self.scene_.update_property_editor()
        # self.update()
        pass

    def recognize_text(self) -> None:
        '''Delegate recognition to scene in case new boxes are detected'''
        if self.properties.recognized:
            button = QtWidgets.QMessageBox.question(self.scene_.parent(), 'Recognize again?', 'Text recognition has already been run for this box. Run again?')

            if button == QtWidgets.QMessageBox.Yes:
                self.scene_.recognize_box(self)
        else:
            self.scene_.recognize_box(self)

    def get_image(self) -> QtGui.QPixmap:
        '''Return part of the image within selection'''
        image: QtGui.QPixmap = self.scene_.image
        return image.copy(self.properties.rect)

    def set_type_to_text(self) -> None:
        self.properties.type = BOX_PROPERTY_TYPE.TEXT

    def set_type_to_image(self) -> None:
        self.properties.type = BOX_PROPERTY_TYPE.IMAGE


class BoxEditorScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project, page: Page) -> None:
        super().__init__(parent)
        self.current_box = None

        self.project = project
        self.current_page = page
        self.image = QtGui.QPixmap()
        # self.set_page_as_background(0)
        self.engine_manager = engine_manager
        self.box_counter = 0

        self.property_editor = property_editor

        # Setup connection to property editor
        self.selectionChanged.connect(self.update_property_editor)
        self.property_editor.recognition_widget.text_edit.editingFinished.connect(self.update_text)
        self.property_editor.recognition_widget.language_combo.currentTextChanged.connect(self.update_language)

    def update_text(self) -> None:
        if len(self.selectedItems()) > 1:
            button = QtWidgets.QMessageBox.question(self.parent(), 'Edit text of multiple boxes?', 'Multiple boxes are currently selected, do you want to set the current text for all selected box?')

            if button == QtWidgets.QMessageBox.No:
                return
        for item in self.selectedItems():
            item.properties.text = self.property_editor.recognition_widget.text_edit.document()
            self.update_property_editor()

    def update_language(self, text) -> None:
        for item in self.selectedItems():
            item.properties.language = Lang(text)

    def update_property_editor(self) -> None:
        '''Update property editor with the currently selected box'''
        for item in self.selectedItems():
            self.property_editor.recognition_widget.box_selected(item.properties)

    def add_box(self, rect: QtCore.QRectF) -> Box:
        '''Add new box and give it an order number'''
        self.current_box = Box(rect, self.engine_manager, self)
        self.current_box.properties.order = self.box_counter
        self.box_counter += 1
        self.addItem(self.current_box)
        self.current_page.box_properties.append(self.current_box.properties)
        # self.box.text_recognized.connect(self.parent.update_property_editor)
        return self.current_box

    def restore_box(self, box_properties: BoxProperties) -> Box:
        '''Restore a box in the editor using box properties stored in the project'''
        self.current_box = Box(QtCore.QRectF(box_properties.rect), self.engine_manager, self)
        self.current_box.properties = box_properties
        self.box_counter += 1
        self.addItem(self.current_box)
        return self.current_box

    def remove_box(self, box: Box) -> None:
        '''Remove a box from the editor window and project'''
        self.removeItem(box)
        self.current_page.box_properties.remove(box.properties)
        #self.box_counter -= 1

        # Renumber items
        self.box_counter = 0
        self.current_box = None

        for item in reversed(self.items()):
            if isinstance(item, Box):
                item.properties.order = self.box_counter
                self.box_counter += 1
                item.update()

    def recognize_box(self, box: Box):
        '''Run OCR for box and update properties with recognized text in selection'''
        engine = self.engine_manager.get_current_engine()

        blocks = engine.recognize(box.get_image(), self.current_page.px_per_mm, box.properties.language)

        if isinstance(blocks, list):
            if len(blocks) > 1:

                new_boxes = []

                # Multiple text blocks have been recognized within the selection, replace original box with new boxes
                for block in blocks:
                    # Add new blocks at the recognized positions and adjust child elements
                    new_box = self.add_box(QtCore.QRectF(block.bbox.translated(box.rect().topLeft().toPoint())))
                    dist = box.rect().topLeft() - new_box.rect().topLeft()
                    new_box.properties.ocr_result_block = block

                    # Move paragraph lines and word boxes accordingly
                    new_box.properties.ocr_result_block.translate(dist.toPoint())

                    new_box.properties.words = new_box.properties.ocr_result_block.get_words()
                    new_box.properties.text = new_box.properties.ocr_result_block.get_text(True)

                    new_box.properties.recognized = True
                    new_box.update()

                    self.current_box = None

                    new_boxes.append(new_box)

                # Remove original box
                self.remove_box(box)

                new_boxes[0].setSelected(True)
            else:
                box.properties.ocr_result_block = blocks[0]
                box.properties.words = blocks[0].get_words()
                box.properties.text = blocks[0].get_text(True)
                box.properties.recognized = True
            self.update_property_editor()
            box.update()

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Handle adding new box by mouse'''
        if not self.itemAt(event.scenePos(), QtGui.QTransform()):
            if event.buttons() == QtCore.Qt.LeftButton:
                if not self.current_box:
                    rect = QtCore.QRectF()
                    rect.setTopLeft(event.scenePos())
                    rect.setBottomRight(event.scenePos())

                    self.add_box(rect)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.current_box:
                if self.current_box:
                    rect = self.current_box.rect()
                    rect.setBottomRight(event.scenePos())
                    self.current_box.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Commit changes after drawing box or remove if too small'''
        if self.current_box:
            corner = self.current_box.rect().topLeft()
            if (event.scenePos().x() - corner.x()) > 10 and (event.scenePos().y() - corner.y()) > 10:
                self.current_box.updateProperties()
                self.current_box.setSelected(True)
                self.current_box.setFocus()
            else:
                self.remove_box(self.current_box)
            self.current_box = None
        super().mouseReleaseEvent(event)

    def set_page_as_background(self, page: Page):
        self.image = QtGui.QPixmap(page.image_path)
        self.setSceneRect(self.image.rect())
        # self.project.current_page_idx = page_number

    def drawBackground(self, painter, rect: QtCore.QRectF) -> None:
        '''Setup background image for page'''
        if self.image:
            painter.drawPixmap(self.sceneRect(), self.image, QtCore.QRectF(self.image.rect()))
