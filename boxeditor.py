import math
from enum import Enum, auto

from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from ocrengine import OCRBlock, OCREngine, OCREngineManager, OCRWord
from project import Project


class BOX_OCR_PROPERTY_TYPE(Enum):
    TEXT = auto()
    IMAGE = auto()


class BoxOCRProperties():
    def __init__(self, order=0, rect=QtCore.QRect(), type: BOX_OCR_PROPERTY_TYPE = BOX_OCR_PROPERTY_TYPE.TEXT, text=QtGui.QTextDocument(), language: Lang = Lang('English'), ocr_block: OCRBlock = OCRBlock(), words: list = []):
        self.order = order
        self.rect = rect
        self.type = type
        self.text = text
        self.language = language
        self.recognized = False
        self.ocr_block = ocr_block
        self.words = words


class BoxEditorScene(QtWidgets.QGraphicsScene):
    def __init__(self, engine_manager: OCREngineManager, property_editor, page_image: QtGui.QPixmap, project: Project) -> None:
        super().__init__(parent=None)
        self.box = None
        self.image = page_image
        self.setSceneRect(self.image.rect())
        self.engine_manager = engine_manager
        self.box_counter = 0
        self.project = project

        self.property_editor = property_editor

        self.selectionChanged.connect(self.update_property_editor)

    def update_property_editor(self):
        '''Update property editor with the currently selected box'''
        if self.selectedItems():
            self.property_editor.select_box(self.selectedItems()[0].properties)

    def addBox(self, rect: QtCore.QRectF):
        '''Add new box and give it an order number'''
        self.box = Box(rect, self.engine_manager, self)
        self.box.properties.order = self.box_counter
        self.box_counter += 1
        self.addItem(self.box)
        # self.box.text_recognized.connect(self.parent.update_property_editor)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Handle adding new box by mouse'''
        if not self.itemAt(event.scenePos(), QtGui.QTransform()):
            if event.buttons() == QtCore.Qt.LeftButton:
                if not self.box:
                    rect = QtCore.QRectF()
                    rect.setTopLeft(event.scenePos())
                    rect.setBottomRight(event.scenePos())

                    self.addBox(rect)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.LeftButton:
            if self.box:
                if self.box:
                    rect = self.box.rect()
                    rect.setBottomRight(event.scenePos())
                    self.box.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Commit changes after drawing box or remove if too small'''
        if self.box:
            corner = self.box.rect().topLeft()
            if (event.scenePos().x() - corner.x()) > 10 and (event.scenePos().y() - corner.y()) > 10:
                self.box.updateProperties()
                self.box.setSelected(True)
                self.box.setFocus()
            else:
                self.removeItem(self.box)
                self.box_counter -= 1
            self.box = None
        super().mouseReleaseEvent(event)

    def drawBackground(self, painter, rect: QtCore.QRectF) -> None:
        '''Setup background image for page'''
        painter.drawPixmap(self.sceneRect(), self.image, QtCore.QRectF(self.image.rect()))


class BoxColor():
    '''Color properties to represent different box types'''

    def __init__(self, brush: QtGui.QBrush = QtGui.QBrush(), pen: QtGui.QPen = QtGui.QPen(), brush_selected: QtGui.QBrush = QtGui.QBrush(), pen_selected: QtGui.QPen = QtGui.QPen()):
        self.brush = brush
        self.pen = pen
        self.brush_selected = brush_selected
        self.pen_selected = pen_selected


class BoxEditor(QtWidgets.QGraphicsView):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project, page_image_filename: str) -> None:
        super().__init__(parent)

        self.project = project
        self.property_editor = property_editor

        self.setScene(BoxEditorScene(engine_manager, self.property_editor, QtGui.QPixmap(page_image_filename), self.project))
        self.origin = QtCore.QPoint()
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)
        self.current_scale = 1.0

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        '''Handle zooming and scrolling by mouse'''
        if event.modifiers() == QtCore.Qt.CTRL:
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


class Box(QtWidgets.QGraphicsRectItem):
    text_recognized = QtCore.Signal(str)

    def __init__(self, rect: QtCore.QRectF, engine_manager: OCREngineManager, scene: BoxEditorScene) -> None:
        super().__init__(rect, parent=None)

        self.engine_manager = engine_manager
        self.scene_ = scene

        self.moving = False

        # Setup order number
        self.number_widget = QtWidgets.QGraphicsSimpleTextItem(self)
        self.number_widget.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Setup recognition checkmark symbol
        checkmark = QtGui.QPixmap('resources/icons/check-line.png').scaledToWidth(16, QtCore.Qt.SmoothTransformation)
        self.recognized_widget = QtWidgets.QGraphicsPixmapItem(checkmark, self)
        self.recognized_widget.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        self.recognized_widget.hide()

        self.setAcceptHoverEvents(True)

        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsFocusable)

        self.properties = BoxOCRProperties()
        self.properties.language = self.scene_.project.language

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
        '''Handle box' scaling via mouse'''
        if self.moving:
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
        '''Paint box' background and border using colors defined by type and update order number item'''
        color = BoxColor()

        if self.properties.type == BOX_OCR_PROPERTY_TYPE.TEXT:
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

        # Update word confidence
        if self.properties.words:
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

            for word in self.properties.words:
                if word.confidence < 90:
                    painter.setBrush(QtGui.QColor(255, 0, 0, (1 - (word.confidence / 100)) * 200))
                    painter.drawRect(word.bbox.translated(self.rect().topLeft().toPoint()))

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        '''Show size grips at the box' margin'''
        self.top = False
        self.right = False
        self.bottom = False
        self.left = False

        cursor = QtGui.QCursor(QtGui.Qt.ArrowCursor)
        if math.isclose(event.pos().x(), self.rect().x(), rel_tol=0.02):
            self.left = True
        if math.isclose(event.pos().x(), self.rect().x() + self.rect().width(), rel_tol=0.02):
            self.right = True
        if math.isclose(event.pos().y(), self.rect().y(), rel_tol=0.02):
            self.top = True
        if math.isclose(event.pos().y(), self.rect().y() + self.rect().height(), rel_tol=0.02):
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

        if self.properties.type == BOX_OCR_PROPERTY_TYPE.TEXT:
            read_action = QtGui.QAction('Read')
            read_action.triggered.connect(self.recognize_text)
            self.menu.addAction(read_action)

            auto_align_action = QtGui.QAction('Auto align')
            auto_align_action.triggered.connect(self.auto_align)
            self.menu.addAction(auto_align_action)

        self.menu.exec(event.screenPos())

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        match event.key():
            case QtCore.Qt.Key_A:
                self.auto_align()
            case QtCore.Qt.Key_I:
                self.set_type_to_image()
            case QtCore.Qt.Key_T:
                self.set_type_to_text()
            case QtCore.Qt.Key_R:
                self.recognize_text()
            case QtCore.Qt.Key_Delete:
                self.scene().removeItem(self)
            case _:
                super().keyPressEvent(event)

    def auto_align(self) -> None:
        '''Automatically align box to recognized text'''
        engine = self.engine_manager.get_current_engine()

        block = engine.read(self.get_image(), self.properties.language)

        if block:
            final_rect = QtCore.QRect(self.properties.rect.x() + block.bbox.x(), self.properties.rect.y() + block.bbox.y(), block.bbox.width(), block.bbox.height())
            self.properties.rect = final_rect
            self.setRect(final_rect)
            self.properties.recognized = True

        self.scene_.update_property_editor()
        self.update()

    def recognize_text(self) -> None:
        '''Run OCR and update properties with recognized text in selection'''
        engine = self.engine_manager.get_current_engine()

        block = engine.read(self.get_image(), self.properties.language)

        if block:
            self.properties.ocr_block = block
            self.properties.words = block.get_words()
            #self.properties.text = block.get_text()
            self.properties.recognized = True
            self.scene_.update_property_editor()
        self.update()

    def get_image(self) -> QtGui.QPixmap:
        '''Return part of the image within selection'''
        image: QtGui.QPixmap = self.scene_.image
        return image.copy(self.properties.rect)

    def set_type_to_text(self) -> None:
        self.properties.type = BOX_OCR_PROPERTY_TYPE.TEXT

    def set_type_to_image(self) -> None:
        self.properties.type = BOX_OCR_PROPERTY_TYPE.IMAGE
