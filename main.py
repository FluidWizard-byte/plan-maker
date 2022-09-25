import math
from datetime import date
import random
from fpdf import FPDF
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from MainWindow import Ui_MainWindow
import os
import glob

report_possible=True
currentPosX=0
currentPosY=0
currentLength=0
totalLength=0
current_decor=''
counter=0
decor=[]
x1=0
x2=0
y1=0
y2=0
MODES = ['picker', 'nline', 'circle','text', 'furniture','text','line', 'rect', 'polygon','generate']

CANVAS_DIMENSIONS = 950, 420

furniture_dir='./furnitures/'
gen_dir='./generate/'
furniture_sprite_dir='./furniture_sprite'
tmp_dir='./temp/'

furnitures=[os.path.join(furniture_dir, f) for f in os.listdir(furniture_dir)]
sprites = [os.path.join(furniture_sprite_dir, f) for f in os.listdir(furniture_sprite_dir)]

PREVIEW_PEN = QPen(QColor(Qt.green), 1, Qt.SolidLine)



def build_font(config):
 
    font = config['font']
    font.setPointSize(config['fontsize'])
    font.setBold(config['bold'])
    font.setItalic(config['italic'])
    font.setUnderline(config['underline'])
    return font

def calculate_distance(x1,y1,x2,y2):
        global currentLength, totallength
        distance=math.sqrt( ((x2-x1)**2)+((y2-y1)**2) )
        normalize_dist=distance/10
        currentLength=normalize_dist
        return currentLength
  

class Canvas(QLabel):

    mode = 'rectangle'

    primary_color = QColor(Qt.black)
    secondary_color = None

    primary_color_updated = pyqtSignal(str)
    secondary_color_updated = pyqtSignal(str)

    # Store configuration settings, including pen width, fonts etc.
    config = {

        'size': 1,
        'fill': True,
        'font': QFont('Consolas'),
        'fontsize': 9,
        'bold': False,
        'italic': False,
        'underline': False,
    }

    active_color = None
    preview_pen = None

    timer_event = None

    current_furniture = None

    def initialize(self):
        self.background_color = QColor(Qt.white)
        
        self.reset()

    def save_tmp(self):
        global counter
        n=str(counter)
        path=tmp_dir+'tmp'+n+'.png'
        pixmap = self.pixmap()
        pixmap.save(path, "PNG" )
        counter+=1

    def reset(self):
        global report_possible, currentLength, totalLength, current_decor, decor
        report_possible=True
        currentLength=0
        totalLength=0
        current_decor=''
        decor=[]
        self.setPixmap(QPixmap(*CANVAS_DIMENSIONS))

        self.pixmap().fill(self.background_color)

    def set_primary_color(self, hex):
        self.primary_color = QColor(hex)

    
    def set_config(self, key, value):
        self.config[key] = value

    def set_mode(self, mode):
        # Clean up active timer animations.
        self.timer_cleanup()
        # Reset  (all)
        self.active_shape_fn = None
        self.active_shape_args = ()

        self.origin_pos = None

        self.current_pos = None
        self.last_pos = None

        self.history_pos = None
        self.last_history = []

        self.current_text = ""
        self.last_text = ""

        self.last_config = {}

        self.dash_offset = 0
        self.locked = False
        # Apply the mode
        self.mode = mode

    def reset_mode(self):
        self.set_mode(self.mode)

    def on_timer(self):
        if self.timer_event:
            self.timer_event()

    def timer_cleanup(self):
        if self.timer_event:
            # Stop the timer and cleanup.
            timer_event = self.timer_event
            self.timer_event = None
            timer_event(final=True)

     # Mouse events.

    def mousePressEvent(self, e):
        fn = getattr(self, "%s_mousePressEvent" % self.mode, None)
        if fn:
            return fn(e)

    def mouseMoveEvent(self, e):
        global currentPosX, currentPosY
        fn = getattr(self, "%s_mouseMoveEvent" % self.mode, None)
        if fn:
            return fn(e)
        currentPosX=e.pos().x()
        currentPosY=e.pos().y()

    def mouseReleaseEvent(self, e):
        fn = getattr(self, "%s_mouseReleaseEvent" % self.mode, None)
        if fn:
            return fn(e)
        

    def mouseDoubleClickEvent(self, e):
        fn = getattr(self, "%s_mouseDoubleClickEvent" % self.mode, None)
        if fn:
            return fn(e)
        

    # furniture
    def furniture_mousePressEvent(self, e):
        global decor 
        p = QPainter(self.pixmap())
        furniture = self.current_furniture
        p.drawPixmap(e.x() - furniture.width() // 2, e.y() - furniture.height() // 2, furniture)
        
        self.update()
        decor.append(current_decor)
        #print(decor)
        self.save_tmp()
        

    # Generic poly events
    def generic_poly_mousePressEvent(self, e):
        global x1,y1,x2,y2,totalLength
        if e.button() == Qt.LeftButton:
            if self.history_pos:
                self.history_pos.append(e.pos())
            else:
                self.history_pos = [e.pos()]
                self.current_pos = e.pos()
                self.timer_event = self.generic_poly_timerEvent

        elif e.button() == Qt.RightButton and self.history_pos:
            # right click=abort
            self.timer_cleanup()
            self.reset_mode()
        try:
            a=len(self.history_pos)
        except:
            a=0
               
        if(a>1):
            x1,y1=self.history_pos[-2].x(), self.history_pos[-2].y()
            x2,y2=e.pos().x(),e.pos().y()
            calculate_distance(x1,x2,y1,y2)
            totalLength+=currentLength
        

    def generic_poly_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        pen.setDashOffset(self.dash_offset)
        p.setPen(pen)
        if self.last_history:
            getattr(p, self.active_shape_fn)(*self.last_history)

        if not final:
            self.dash_offset -= 1
            pen.setDashOffset(self.dash_offset)
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(*self.history_pos + [self.current_pos])

        self.update()
        self.last_pos = self.current_pos
        self.last_history = self.history_pos + [self.current_pos]

    def generic_poly_mouseMoveEvent(self, e):
        global currentPosX,currentPosY
        self.current_pos = e.pos()
        currentPosX=e.pos().x()
        currentPosY=e.pos().y()
        

    def generic_poly_mouseDoubleClickEvent(self, e):
        
        self.timer_cleanup()
        p = QPainter(self.pixmap())
        p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        # Note the brush is ignored for polylines.
        if self.secondary_color:
            p.setBrush(QBrush(self.secondary_color))

        getattr(p, self.active_shape_fn)(*self.history_pos + [e.pos()])
        self.update()
        self.reset_mode()
        self.save_tmp()

        

    # Generic shape events
    def generic_shape_mousePressEvent(self, e):
        global x1,y1
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.timer_event = self.generic_shape_timerEvent
        x1,y1=e.pos().x(), e.pos().y()
        

    def generic_shape_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        pen.setDashOffset(self.dash_offset)
        p.setPen(pen)
        if self.last_pos:
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, self.last_pos), *self.active_shape_args)

        if not final:
            self.dash_offset -= 1
            pen.setDashOffset(self.dash_offset)
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, self.current_pos), *self.active_shape_args)

        self.update()
        self.last_pos = self.current_pos

    def generic_shape_mouseMoveEvent(self, e):
        global currentPosX,currentPosY
        self.current_pos = e.pos()
        currentPosX=e.pos().x()
        currentPosY=e.pos().y()


    def generic_shape_mouseReleaseEvent(self, e):
        global x2,y2
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))

            #if self.config['fill']:
             #   p.setBrush(QBrush(self.secondary_color))
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, e.pos()), *self.active_shape_args)
            self.update()

            x2,y2=e.pos().x(), e.pos().y()
            calculate_distance(x1,x2,y1,y2)
        self.reset_mode()
        self.save_tmp()


    # Text events

    def keyPressEvent(self, e):
        if self.mode == 'text':
            if e.key() == Qt.Key_Backspace:
                self.current_text = self.current_text[:-1]
            else:
                self.current_text = self.current_text + e.text()

    def text_mousePressEvent(self, e):
       
        if e.button() == Qt.LeftButton and self.current_pos is None:
            self.current_pos = e.pos()
            self.current_text = ""
            self.timer_event = self.text_timerEvent

        elif e.button() == Qt.LeftButton:

            self.timer_cleanup()
            # Draw the text to the image
            p = QPainter(self.pixmap())
            p.setRenderHints(QPainter.Antialiasing)
            font = build_font(self.config)
            p.setFont(font)
            pen = QPen(self.primary_color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.drawText(self.current_pos, self.current_text)
            self.update()

            self.reset_mode()
        

        elif e.button() == Qt.RightButton and self.current_pos:
            self.reset_mode()

        self.save_tmp()

    def text_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = PREVIEW_PEN
        p.setPen(pen)
        if self.last_text:
            font = build_font(self.last_config)
            p.setFont(font)
            p.drawText(self.current_pos, self.last_text)

        if not final:
            font = build_font(self.config)
            p.setFont(font)
            p.drawText(self.current_pos, self.current_text)

        self.last_text = self.current_text
        self.last_config = self.config.copy()
        self.update()


   # Line events

    def line_mousePressEvent(self, e):
        global x1,y1
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.preview_pen = PREVIEW_PEN
        self.timer_event = self.line_timerEvent
        x1,y1=e.pos().x(), e.pos().y()

    def line_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            p.drawLine(self.origin_pos, self.last_pos)

        if not final:
            p.drawLine(self.origin_pos, self.current_pos)

        self.update()
        self.last_pos = self.current_pos

    def line_mouseMoveEvent(self, e):
        global currentPosX,currentPosY
        self.current_pos = e.pos()
        currentPosX=e.pos().x()
        currentPosY=e.pos().y()

    def line_mouseReleaseEvent(self, e):
        global x2,y2,totalLength
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

            p.drawLine(self.origin_pos, e.pos())
            self.update()
        
        x2,y2=e.pos().x(), e.pos().y()
        calculate_distance(x1,x2,y1,y2)
        totalLength+=currentLength
        self.reset_mode()
        self.save_tmp()


    
    # Rectangle events

    def rect_mousePressEvent(self, e):
        
        self.active_shape_fn = 'drawRect'
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.generic_shape_mousePressEvent(e)

    def rect_timerEvent(self, final=False):
        self.generic_shape_timerEvent(final)

    def rect_mouseMoveEvent(self, e):
        self.generic_shape_mouseMoveEvent(e)
        
    def rect_mouseReleaseEvent(self, e):
        global totalLength,currentLength
        self.generic_shape_mouseReleaseEvent(e)
        l=(math.sqrt(((currentLength**2)/2)))*4
        totalLength+=l
        

        
        

     # circle events

    def circle_mousePressEvent(self, e):
        self.active_shape_fn = 'drawEllipse'
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.generic_shape_mousePressEvent(e)
        

    def circle_timerEvent(self, final=False):
        self.generic_shape_timerEvent(final)

    def circle_mouseMoveEvent(self, e):
        self.generic_shape_mouseMoveEvent(e)

    def circle_mouseReleaseEvent(self, e):
        global totalLength, currentLength
        self.generic_shape_mouseReleaseEvent(e)
        circ=2*math.pi*(currentLength/2)
        totalLength+=circ
        
        
    # Polygon events

    def polygon_mousePressEvent(self, e):
        self.active_shape_fn = 'drawPolygon'
        self.preview_pen = PREVIEW_PEN
        self.generic_poly_mousePressEvent(e)
        
    def polygon_timerEvent(self, final=False):
        self.generic_poly_timerEvent(final)

    def polygon_mouseMoveEvent(self, e):
        self.generic_poly_mouseMoveEvent(e)

    def polygon_mouseDoubleClickEvent(self, e):
        self.generic_poly_mouseDoubleClickEvent(e)
        

    # Polyline events

    def nline_mousePressEvent(self, e):
        self.active_shape_fn = 'drawPolyline'
        self.preview_pen = PREVIEW_PEN
        self.generic_poly_mousePressEvent(e)
        
    def nline_timerEvent(self, final=False):
        self.generic_poly_timerEvent(final)

    def nline_mouseMoveEvent(self, e):
        self.generic_poly_mouseMoveEvent(e)

    def nline_mouseDoubleClickEvent(self, e):
        self.generic_poly_mouseDoubleClickEvent(e)
        
    
    #color picker events
    def picker_mousePressEvent(self,e):
        color = QColorDialog.getColor()
        self.set_primary_color(color)
        
class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        # Replace canvas placeholder from QtDesigner.
        self.horizontalLayout.removeWidget(self.canvas)
        self.canvas = Canvas()
        self.canvas.initialize()
        # We need to enable mouse tracking to follow the mouse without the button pressed.
        self.canvas.setMouseTracking(True)
        # Enable focus to capture key inputs.
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.horizontalLayout.addWidget(self.canvas)

        # Setup the mode buttons
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)

        for mode in MODES:
            btn = getattr(self, '%sButton' % mode)
            btn.pressed.connect(lambda mode=mode: self.canvas.set_mode(mode))
            mode_group.addButton(btn)

        
        # Initialize  timer.
        self.timer = QTimer()
        self.timer.timeout.connect(self.canvas.on_timer)
        self.timer.setInterval(100)
        self.timer.start()


        # Setup the furniture state.
        self.current_furniture_n = -1
        self.next_furniture()
        self.nextFurnitureButton.pressed.connect(self.next_furniture)

        #menu items
        self.actionSave.triggered.connect(self.save_file)
        self.actionOpen.triggered.connect(self.open_file)
        self.actionNew.triggered.connect(self.canvas.initialize)
        self.actionClear.triggered.connect(self.canvas.reset)
        self.actionExit.triggered.connect(self.exit)
        self.actionHorozontal_Flip.triggered.connect(self.horizontal_flip)
        self.actionVertical_Flip.triggered.connect(self.vertical_flip)
        self.actionColor_Invert.triggered.connect(self.color_invert)
        self.actionSave_Report.triggered.connect(self.make_report)
        self.actionAbout.triggered.connect(self.about_txt)
        self.generateButton.clicked.connect(self.generate)
        self.actionUndo.triggered.connect(self.undo)
       
        
        self.show()

    def undo(self):
        global counter
        n=str(counter-2)
        path=tmp_dir+'tmp'+n+'.png'
        print(path)
        pixmap = QPixmap()
        pixmap.load(path)
        self.canvas.setPixmap(pixmap)
        self.canvas.save_tmp()


    def make_report(self):
        height=9
        wallarea=round(height*totalLength)
        
        
        if (report_possible and wallarea>0):
            

            drywall_low=f'{round(wallarea*100):,}'
            drywall_high=f'{round(wallarea*300):,}'

            brick_low=f'{round(wallarea*2700):,}'
            brick_high=f'{round(wallarea*4500):,}'

            stone_veenere_low=f'{round(wallarea*1000):,}'
            stone_veenere_high=f'{round(wallarea*2500):,}'

            wood_paneling_low=f'{round(wallarea*700):,}'
            wood_paneling_high=f'{round(wallarea*3500):,}'

            decor_items={}

            for item in decor:
                decor_items[item]=decor.count(item)
            
            print(decor_items)

            itemlist=[]
            quantity=[]
            pricelist=[]
            costlist=[]

            for key in list(decor_items.keys()):
                txt=key
                start=txt.find('_')
                itemlist.append(txt[:start])
                pricelist.append(txt[start+1:])
            
            for value in list(decor_items.values()):
                quantity.append(value)
            
            for i in range (0,len(itemlist)):
                costlist.append(int(quantity[i])*int(pricelist[i]))

            # print(itemlist)
            # print(quantity)
            # print(pricelist)
            # print(costlist)

            total_cost=0
            for cost in costlist:
                total_cost+=cost
            
            total_fcost=f'{total_cost:,}'

            

            current_date=date.today().strftime("%B %d, %Y")
            pdf=FPDF()
            
            pdf.add_page()
            pdf.image("./bg/letterhead_cropped.png", 0, 0, 210) 
            pdf.set_font('Helvetica','',12)
            
            pdf.cell(40,10,f'Degign',ln=True)
            
            pixmap=self.canvas.pixmap()
            pixmap.save('./tmp.png', "PNG" )
            
            pdf.image("./tmp.png",5,90,210)
            os.remove('tmp.png')
            
            pdf.add_page()
            pdf.cell(40,10,f'{current_date}',ln=True)
            pdf.cell(40,10,f'This report contains cost estimation for walls and furniture, it is assumed walls are 9 feet tall',ln=True)
            pdf.cell(30,10,f'Material cost estimates for combined wall area {wallarea} sq.ft',ln=True)

            pdf.cell(30,10,f'Drywall: NPR {drywall_low} - NPR {drywall_high}',ln=True)
            pdf.cell(30,10,f'Brick: NPR {brick_low} - NPR {brick_high}',ln=True)
            pdf.cell(30,10,f'Stine veneere: NPR {stone_veenere_low} - NPR {stone_veenere_high}',ln=True)
            pdf.cell(30,10,f'Wood paneling: NPR {wood_paneling_low} - NPR {wood_paneling_high}',ln=True)

            pdf.cell(30,10,f'Cost estimate for furniture is NPR {total_fcost}',ln=True)
            pdf.cell(30,10,f'The cost break down is given below',ln=True)

            for i in range (0,len(itemlist)):
                pdf.cell(30,10,f'item {i+1} : {itemlist[i]}',ln=True)
                pdf.image(furniture_dir+itemlist[i]+".png", None, None, 32,32)
                pdf.cell(30,10,f'{quantity[i]} * {pricelist[i]}',ln=True)
                

            path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "PDF file (*.pdf)")
            
            try:
                pdf.output(path,'F')
            except:
                print('invalid path')
        else:
            QMessageBox.about(self, "Error",
                          "<p>Reports can only be generated on your own non empty designs</p>")

    def generate(self):
        global report_possible
        report_possible=False
        fname=gen_dir+random.choice(os.listdir(gen_dir))
        pixmap = QPixmap()
        pixmap.load(fname)
        self.canvas.setPixmap(pixmap)

    def about_txt(self):
        QMessageBox.about(self, "About Plan Maker",
                          "<p>This is a simple Application made with PyQt5 that allows toy to make designs.The basics are like paint application.</p>")

    #save image
    def save_file(self):

        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "PNG Image file (*.png)")

        if path:
            pixmap = self.canvas.pixmap()
            pixmap.save(path, "PNG" )
    
    #open image
    def open_file(self):
        global report_possible 
        report_possible=False
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "PNG image files (*.png); JPEG image files (*jpg); All files (*.*)")
        

        if path:
            pixmap = QPixmap()
            pixmap.load(path)

            width,height=pixmap.width(),pixmap.height()
            canvasw,canvash=CANVAS_DIMENSIONS

            if width/canvasw < height/canvash:  
                pixmap = pixmap.scaledToWidth(canvasw)
                hoff = (pixmap.height() - canvash) // 2
                pixmap = pixmap.copy(
                    QRect(QPoint(0, hoff), QPoint(canvasw, pixmap.height()-hoff))
                )

            elif width/canvasw > height/canvash:  
                pixmap = pixmap.scaledToHeight(canvash)
                woff = (pixmap.width() - canvasw) // 2
                pixmap = pixmap.copy(
                    QRect(QPoint(woff, 0), QPoint(pixmap.width()-woff, canvash))
                )

            self.canvas.setPixmap(pixmap)
        
    
    #exit
    def exit(self):
        files = glob.glob(tmp_dir+'*')
        for f in files:
            os.remove(f)
        self.close()
        
    
    #flip horizontal
    def horizontal_flip(self):
        pixmap = self.canvas.pixmap()
        self.canvas.setPixmap(pixmap.transformed(QTransform().scale(-1, 1)))
    
    #flip vertical
    def vertical_flip(self):
        pixmap = self.canvas.pixmap()
        self.canvas.setPixmap(pixmap.transformed(QTransform().scale(1, -1)))

    #color inverse
    def color_invert(self):
        img = QImage(self.canvas.pixmap())
        img.invertPixels()
        pixmap = QPixmap()
        pixmap.convertFromImage(img)
        self.canvas.setPixmap(pixmap)

    def next_furniture(self):
        global current_decor
        self.current_furniture_n += 1
        if self.current_furniture_n >= len(sprites):
            self.current_furniture_n = 0

        pixmap = QPixmap(sprites[self.current_furniture_n])
        self.nextFurnitureButton.setIcon(QIcon(pixmap))

        self.canvas.current_furniture = pixmap

        pn=sprites[self.current_furniture_n]
        start=pn.find('\\')
        end=pn.find('.p')

        decor=pn[start+1:end]
        current_decor=decor
        

        
    

if __name__ == '__main__':

    app = QApplication([])
    window = MainWindow()
    def update_label():
        window.label_4.setText(str(currentLength))
        window.label_3.setText('('+str(currentPosX)+','+str(currentPosY)+')')
        
    timer=QTimer()
    timer.timeout.connect(update_label)
    timer.start(10)
    app.exec_()