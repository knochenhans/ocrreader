import math
from enum import Enum, auto

from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from ocrengine import OCREngine


class BOX_OCR_PROPERTY_TYPE(Enum):
    TEXT = auto()
    IMAGE = auto()


class Project():
    def __init__(self, language=Lang(name='English')):
        self.language = language


class BoxOCRProperties():
    def __init__(self, order=0, rect=QtCore.QRect(), type: BOX_OCR_PROPERTY_TYPE = BOX_OCR_PROPERTY_TYPE.TEXT, text='', language=Lang(name='English')):
        self.order = order
        self.rect = rect
        self.type = type
        self.text = text
        self.language = language


class BoxEditorScene(QtWidgets.QGraphicsScene):
    def __init__(self, engine: OCREngine) -> None:
        super().__init__(parent=None)
        self.box = None
        self.image = QtGui.QPixmap('/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm')
        self.setSceneRect(self.image.rect())
        self.engine = engine
        self.box_counter = 0

    def addBox(self, rect: QtCore.QRectF):
        """Add new box and give it an order number"""
        self.box = Box(rect, self.engine, self)
        self.box.setSelected(True)
        self.box.properties.order = self.box_counter
        self.box_counter = + 1
        self.addItem(self.box)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
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
        if self.box:
            self.box.updatePropertiesRect()
            self.box = None
        super().mouseReleaseEvent(event)

    def drawBackground(self, painter, rect: QtCore.QRectF) -> None:
        painter.drawPixmap(self.sceneRect(), self.image, QtCore.QRectF(self.image.rect()))


class BoxColor():
    def __init__(self, brush: QtGui.QBrush = QtGui.QBrush(), pen: QtGui.QPen = QtGui.QPen(), brush_selected: QtGui.QBrush = QtGui.QBrush(), pen_selected: QtGui.QPen = QtGui.QPen()):
        self.brush = brush
        self.pen = pen
        self.brush_selected = brush_selected
        self.pen_selected = pen_selected


class BoxEditor(QtWidgets.QGraphicsView):
    def __init__(self, parent, engine: OCREngine) -> None:
        super().__init__(parent)

        self.setScene(BoxEditorScene(engine))
        self.origin = QtCore.QPoint()
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() == QtCore.Qt.CTRL:
            scaleFactor = 1.03
            degrees = event.angleDelta().y()
            if degrees > 0:
                self.scale(scaleFactor, scaleFactor)
            else:
                self.scale(1 / scaleFactor, 1 / scaleFactor)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.MiddleButton:
            self.origin = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.MiddleButton:
            oldPoint = self.mapToScene(self.origin)
            newPoint = self.mapToScene(event.pos())
            translation = newPoint - oldPoint

            self.translate(translation.x(), translation.y())

            self.origin = event.pos()

        super().mouseMoveEvent(event)


class Box(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect: QtCore.QRectF, engine: OCREngine, scene: BoxEditorScene) -> None:
        super().__init__(rect, parent=None)

        self.setAcceptHoverEvents(True)

        self.moving = False
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemIsMovable)

        self.properties = BoxOCRProperties()

        self.setRect(rect)
        self.updatePropertiesRect()

        self.engine = engine
        self.scene_ = scene

        self.number = QtWidgets.QGraphicsSimpleTextItem(self)
        
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
            self.updatePropertiesRect()
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
        self.updatePropertiesRect()
        super().mouseReleaseEvent(event)

    def updatePropertiesRect(self):
        self.properties.rect = QtCore.QRectF(self.mapToScene(self.rect().topLeft()), self.mapToScene(self.rect().bottomRight())).toAlignedRect()

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: QtWidgets.QWidget) -> None:
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

        pos = self.rect().bottomLeft()
        pos.setX(pos.x() + 5)
        pos.setY(pos.y() - 20)
        self.number.setPos(pos)
        self.number.setText(str(self.properties.order + 1))

        self.update()

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
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

        image_action = QtGui.QAction('Image')
        image_action.triggered.connect(self.set_type_to_image)

        image_read = QtGui.QAction('Read')
        image_read.triggered.connect(self.read)

        self.menu.addAction(text_action)
        self.menu.addAction(image_action)
        self.menu.addAction(image_read)
        self.menu.exec(event.screenPos())

    def read(self):
        image: QtGui.QPixmap = self.scene_.image
        text = self.engine.read(image.copy(self.properties.rect), self.properties.language.pt2t)

        print(text)

    def set_type_to_text(self):
        self.properties.type = BOX_OCR_PROPERTY_TYPE.TEXT

    def set_type_to_image(self):
        self.properties.type = BOX_OCR_PROPERTY_TYPE.IMAGE
