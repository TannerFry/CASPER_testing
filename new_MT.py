import sqlite3
import os
from PyQt5 import QtWidgets, Qt, QtGui, QtCore, uic
import GlobalSettings
from PyQt5.QtChart import QChartView
from Algorithms import SeqTranslate
from CSPRparser import CSPRparser
from matplotlib.ticker import MaxNLocator
import gzip
import statistics
from collections import Counter

class Multitargeting(QtWidgets.QMainWindow):
    BAD_instances = {}
    sorted_instances = []

    def __init__(self, parent=None):

        super(Multitargeting, self).__init__()
        uic.loadUi('multitargetingwindow.ui', self)
        self.setWindowIcon(QtGui.QIcon("cas9image.png"))
        self.max_chromo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.min_chromo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.chromo_seed.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)

        v = self.max_chromo.view()
        v.setUniformItemSizes(True)
        v.setLayoutMode(QtWidgets.QListView.Batched)

        # self.loading.hide()
        # Storage containers for the repeats and seed sequences
        self.sq = SeqTranslate()  # SeqTranslate object used in class

        # Initializes the three graphs
        self.chart_view_chro_bar = QChartView()
        self.chart_view_repeat_bar = QChartView()
        self.chart_view_repeat_line = QChartView()

        self.data = ""
        self.shortHand = ""
        self.chromo_length = list()

        # Listeners for changing the seed sequence or the .cspr file
        self.max_chromo.currentIndexChanged.connect(self.min_max_changed)
        self.min_chromo.currentIndexChanged.connect(self.min_max_changed)
        self.chromo_seed.currentIndexChanged.connect(self.seed_chromo_changed)
        self.Analyze_Button.clicked.connect(self.make_graphs)
        self.next.clicked.connect(self.get_next_1000_seeds)
        self.prev.clicked.connect(self.get_prev_1000_seeds)

        # go back to main button
        self.back_button.clicked.connect(self.go_back)

        # Tool Bar options
        self.actionCASPER.triggered.connect(self.changeto_main)

        # Statistics storage variables
        self.max_repeats = 1
        self.average = 0
        self.median = 0
        self.mode = 0
        self.average_unique = 0
        self.average_rep = 0
        self.bar_coords = []
        self.seed_id_seq_pair = {}

        # parser object
        self.parser = CSPRparser("")

        self.ready_chromo_min_max = True
        self.ready_chromo_make_graph = True
        self.directory = 'Cspr files'
        self.info_path = os.getcwd()

        ##################################
        self.scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        self.scene2 = QtWidgets.QGraphicsScene()
        self.graphicsView_2.setScene(self.scene2)
        self.graphicsView.viewport().installEventFilter(self)


    def eventFilter(self, source, event):
        if (event.type() == QtCore.QEvent.MouseMove and source is self.graphicsView.viewport()):
            coord = self.graphicsView.mapToScene(event.pos())
            for i in self.bar_coords:
                x = i[1]
                y1 = i[2]
                y2 = i[3]
                dups = 0
                if ((coord.x() == x or coord.x() == x + 1 or coord.x() == x - 1) and (
                        coord.y() >= y1 and coord.y() <= y2)):

                    listtemp = []
                    for a in self.bar_coords:
                        if (x == a[1] and y1 == a[2] and y2 == a[3]):
                            listtemp.append(a)
                            dups += 1
                    self.scene2 = QtWidgets.QGraphicsScene()
                    self.graphicsView_2.setScene(self.scene2)
                    output = str()
                    i = 1
                    for item in listtemp:
                        ind = item[0]
                        temp = self.event_data[ind]
                        if len(listtemp) > 1 and i < len(listtemp):
                            output += 'Location: ' + str(temp[0]) + ' | Seq: ' + str(temp[1]) + ' | PAM: ' + str(
                                temp[2]) + ' | SCR: ' + str(temp[3]) + ' | DIRA: ' + str(temp[4]) + '\n'
                        else:
                            output += 'Location: ' + str(temp[0]) + ' | Seq: ' + str(temp[1]) + ' | PAM: ' + str(
                                temp[2]) + ' | SCR: ' + str(temp[3]) + ' | DIRA: ' + str(temp[4])
                        i += 1
                    text = self.scene2.addText(output)
                    font = QtGui.QFont()
                    font.setBold(True)
                    font.setPointSize(9)
                    text.setFont(font)

        return Qt.QWidget.eventFilter(self, source, event)


    def launch(self, path):
        os.chdir(path)
        self.directory = path
        self.get_data()


    #come back and update after new file formats are out
    def get_data(self):
        onlyfiles = [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f))]
        orgsandendos = {}
        shortName = {}
        self.endo_drop.clear()
        for file in onlyfiles:
            if file.find('.cspr') != -1:
                newname = file[0:-4]
                s = newname.split('_')
                hold = gzip.open(file, 'r')
                buf = (hold.readline())
                hold.close()
                buf = str(buf)
                buf = buf.strip("'b")
                buf = buf[:len(buf) - 4]
                species = buf[8:buf.find('\n')]
                endo = str(s[1])
                endo = endo.strip('.')
                if species not in shortName:
                    shortName[species] = s[0]
                if species in orgsandendos:
                    orgsandendos[species].append(endo)
                else:
                    orgsandendos[species] = [endo]
                    if self.organism_drop.findText(species) == -1:
                        self.organism_drop.addItem(species)
        self.data = orgsandendos
        self.shortHand = shortName
        temp = self.data[str(self.organism_drop.currentText())]
        temp1 = []
        for i in temp:
            temp1.append(i)
        self.endo_drop.addItems(temp1)
        self.organism_drop.currentIndexChanged.connect(self.changeEndos)

        endo = self.endo_drop.currentText()
        short = self.shortHand[str(self.organism_drop.currentText())]
        file = short + '_' + endo + '_' + 'repeats.db'
        self.filename = file


    #come back and update
    def changeEndos(self):
        self.endo_drop.clear()
        temp = self.data[str(self.organism_drop.currentText())]
        temp1 = []
        for i in temp:
            temp1.append(i)
        self.endo_drop.addItems(temp1)

        endo = self.endo_drop.currentText()
        short = self.shortHand[str(self.organism_drop.currentText())]
        file = short + '_' + endo + '_' + 'repeats.db'
        self.filename = file


    #make all graphs and fill dropdowns
    def make_graphs(self):
        # get the correct file name
        self.chromo_length.clear()
        # file_name = self.shortHand[self.organism_drop.currentText()] + "_" + self.endo_drop.currentText()
        # calculations and setting the windows
        self.plot_repeats_vs_seeds()
        self.bar_seeds_vs_repeats()
        self.fill_min_max()
        self.fill_seed_id_chrom()
        self.fill_Chromo_Text()
        #add back in the statistics later
        # self.nbr_seq.setText(str(len(self.parser.seeds)))
        # self.nbr_unq.setText(str(self.parser.uniq_seq_count()))
        self.avg_rep.setText(str(self.average))
        self.med_rep.setText(str(self.median))
        self.mode_rep.setText(str(self.mode))
        # self.scr_lbl.setText(str(self.average_rep))


    # fill in chromo bar visualization
    def fill_Chromo_Text(self):
        chromo_pos = {}
        #get kstats
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        kstats = []
        for k in c.execute("SELECT * FROM kstats"):
            k = list(k)
            kstats.append(k[0])
        seed = self.chromo_seed.currentText()
        data = list(c.execute("SELECT chromosome, location FROM repeats WHERE seed = ? ", (seed,)).fetchone())
        c.close()
        chromo = data[0].split(',')
        pos = data[1].split(',')
        self.event_data = {}
        for i in range(len(chromo)):
            c = int(chromo[i])
            p = int(pos[i])
            k = int(kstats[c-1])
            new_pos = int((p / k) * 485)
            if c in chromo_pos.keys():
                chromo_pos[c].append(new_pos)
            else:
                chromo_pos[c] = [new_pos]
        i = 0
        self.scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        self.bar_coords.clear()  # clear bar_coords list before creating visual
        ind = 0
        for chromo in chromo_pos:
            pen_blk = QtGui.QPen(QtCore.Qt.black)
            pen_red = QtGui.QPen(QtCore.Qt.red)
            pen_blk.setWidth(3)
            pen_red.setWidth(3)
            if i == 0:
                text = self.scene.addText(str(chromo))
                text.setPos(0, 0)
                font = QtGui.QFont()
                font.setBold(True)
                font.setPointSize(10)
                text.setFont(font)
                self.scene.addRect(40, (i * 25), 525, 25, pen_blk)
            else:
                text = self.scene.addText(str(chromo))
                font = QtGui.QFont()
                font.setBold(True)
                font.setPointSize(10)
                text.setFont(font)
                text.setPos(0, i * 25 + 10 * i)
                self.scene.addRect(40, (i * 25) + 10 * i, 525, 25, pen_blk)
            for k in chromo_pos[chromo]:
                line = self.scene.addLine(k + 40, (i * 25) + 3 + 10 * i, k + 40, (i * 25) + 22 + 10 * i, pen_red)
                temp = []  # used for storing coordinates and saving them in self.bar_coords[]
                temp.append(ind)  # index value
                temp.append(k + 40)  # x value
                temp.append((i * 25) + 3 + 10 * i)  # y1
                temp.append((i * 25) + 22 + 10 * i)  # y2
                self.bar_coords.append(temp)  # push x, y1, and y2 to this list
                ind += 1
            i = i + 1
        self.generate_event_data()


    #get data for chromsome viewer to display
    def generate_event_data(self):
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        seed = seed = self.chromo_seed.currentText()
        data = list(c.execute("SELECT * FROM repeats WHERE seed = ? ", (seed,)).fetchone())
        c.close()
        chromo = data[1].split(',')
        loc = data[2].split(',')
        tail = data[3].split(',')
        score = data[4].split(',')
        self.event_data = {}
        for i in range(len(chromo)):
            if tail[i].find('-') != -1:
                t = tail[i].split('-')
                dira = '-'
            else:
                t = tail[i].split('+')
                dira = '+'
            pam = t[1]
            seq = t[0] + seed
            self.event_data[i] = [loc[i], seq, pam, score[i], dira]


    # creates bar graph num of repeats vs. chromsome
    # this graphs is connected to the repeats_vs_chromo.py file
    # to represent the widget space in the UI file
    def chro_bar_create(self, seed):
        self.repeats_vs_chromo.canvas.axes.clear()
        y = []
        x_labels = []
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        data = c.execute("SELECT chromosome FROM repeats WHERE seed = ? ", (seed,)).fetchone()
        c.close()
        data = data[0].split(',')
        for i in range(len(data)):
            data[i] = int(data[i])
        bar_data = Counter(data)
        for chromo in sorted(bar_data):
            x_labels.append(chromo)
            y.append(bar_data[chromo])
        x = list(range(0, len(x_labels)))

        #the following statements are plottings / formatting for the graph
        self.repeats_vs_chromo.canvas.axes.bar(x, y, align='center')
        self.repeats_vs_chromo.canvas.axes.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.repeats_vs_chromo.canvas.axes.set_ylim(0, max(y) + 1)
        self.repeats_vs_chromo.canvas.axes.set_xticks(x)
        self.repeats_vs_chromo.canvas.axes.set_xticklabels(x_labels)
        self.repeats_vs_chromo.canvas.axes.set_xlabel('Chromosome')
        self.repeats_vs_chromo.canvas.axes.set_ylabel('Number of Repeats')
        self.repeats_vs_chromo.canvas.draw()


    # plots the sequences per Number Repeats bar graph
    # this graph is connected to the seeds_vs_repeats_bar.py file
    # to represent the wdiget space in the UI file
    def bar_seeds_vs_repeats(self):
        self.seeds_vs_repeats_bar.canvas.axes.clear()
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        data = c.execute("SELECT seed, count from repeats").fetchall()
        c.close()
        repeat_data = []
        for obj in data:
            cnt = list(obj)[1]
            repeat_data.append(cnt)
        repeat_data = Counter(repeat_data)
        max_rep = max(repeat_data.values())
        x_labels = []
        y = []
        for rep in sorted(repeat_data, key=repeat_data.get, reverse=True):
            if repeat_data[rep] / max_rep > 0.01:
                x_labels.append(rep)
                y.append(repeat_data[rep])
        x = list(range(0, len(x_labels)))
        # the following are plotting / formatting for the graph
        self.seeds_vs_repeats_bar.canvas.axes.bar(x, y)
        self.seeds_vs_repeats_bar.canvas.axes.set_xticks(x)
        self.seeds_vs_repeats_bar.canvas.axes.set_xticklabels(x_labels)
        self.seeds_vs_repeats_bar.canvas.axes.set_xlabel('Number of Repeats')
        self.seeds_vs_repeats_bar.canvas.axes.set_ylabel('Number of Sequences')
        self.seeds_vs_repeats_bar.canvas.axes.set_title('Number of Sequences per Number of Repeats')


        # rects are all the bar objects in the graph
        rects = self.seeds_vs_repeats_bar.canvas.axes.patches
        rect_vals = []
        # this for loop will calculate the height and create an annotation for each bar
        for rect in rects:
            height = rect.get_height()
            temp = self.seeds_vs_repeats_bar.canvas.axes.text(rect.get_x() + rect.get_width() / 2, height,
                                                              '%d' % int(height),
                                                              ha='center', va='bottom')
            temp.set_visible(False)
            rect_vals.append(temp)

        # function used for when user cursor is hovering over the bar, if hovering over a bar, the
        # height annotatin will appear above the bar, otherwise it will be hidden
        def on_plot_hover(event):
            i = 0
            for rect in rects:
                if rect.contains(event)[0]:
                    rect_vals[i].set_visible(True)
                else:
                    rect_vals[i].set_visible(False)
                i = i + 1
            self.seeds_vs_repeats_bar.canvas.draw()

        # statement to detect cursor hovering over the bars
        self.seeds_vs_repeats_bar.canvas.mpl_connect('motion_notify_event', on_plot_hover)
        # must redraw after every change
        self.seeds_vs_repeats_bar.canvas.draw()


    # plots the repeats per ID number graph as line graph
    # this graph is connected to the repeats_vs_seeds_line.py file
    # to represent the widget space in the UI file
    def plot_repeats_vs_seeds(self):
        self.repeats_vs_seeds_line.canvas.axes.clear()
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        data = c.execute("SELECT seed, count from repeats").fetchall()
        c.close()

        x1 = list(range(0, len(data)))
        y1 = []
        for obj in data:
            y1.append(int(list(obj)[1]))
        y1.sort(reverse=True)

        #get stats
        self.average = statistics.mean(y1)
        self.mode = statistics.mode(y1)
        self.median = statistics.median(y1)

        # clear axes
        self.repeats_vs_seeds_line.canvas.axes.clear()
        # the following are for plotting / formatting
        self.repeats_vs_seeds_line.canvas.axes.plot(x1, y1)
        self.repeats_vs_seeds_line.canvas.axes.set_xlabel('Seed ID Number')
        self.repeats_vs_seeds_line.canvas.axes.set_ylabel('Number of Repeats')
        self.repeats_vs_seeds_line.canvas.axes.set_title('Number of Repeats per Seed ID Number')
        # always redraw at the end
        self.repeats_vs_seeds_line.canvas.draw()


    # fills min and max dropdown windows
    def fill_min_max(self):
        self.max_chromo.currentIndexChanged.disconnect()
        self.min_chromo.currentIndexChanged.disconnect()
        self.max_chromo.clear()
        self.min_chromo.clear()
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        data = c.execute("SELECT MAX(count) from repeats").fetchone()
        c.close()
        max_rep = int(data[0])
        nums = list(range(1, max_rep+1))
        for num in nums:
            self.min_chromo.addItem(str(num))
        for num in sorted(nums, reverse=True):
            self.max_chromo.addItem(str(num))
        self.max_chromo.currentIndexChanged.connect(self.min_max_changed)
        self.min_chromo.currentIndexChanged.connect(self.min_max_changed)


    #fill_seed_id_chrom will fill the seed ID dropdown, and create the chromosome graph
    def fill_seed_id_chrom(self):
        self.chromo_seed.disconnect()
        conn = sqlite3.connect(self.filename)
        c = conn.cursor()
        min_v = int(self.min_chromo.currentText())
        max_v = int(self.max_chromo.currentText())
        data = c.execute("SELECT seed, count from repeats where count >= ?  and count <= ?", (min_v, max_v,)).fetchall()
        c.close()
        model = QtGui.QStandardItemModel()
        parentItem = model.invisibleRootItem()
        i = 0
        self.seeds = []
        for obj in data:
            seed = (list(obj)[0])
            if i > 999:
                break
            else:
                if i == 0:
                    self.chro_bar_create(seed)
                item = QtGui.QStandardItem(seed)
                parentItem.appendRow(item)
                self.seeds.append(seed)
            i += 1
        self.seed_counter = 0
        self.seed_max_counter = len(self.seeds) / 1000
        self.chromo_seed.setModel(model)
        self.chromo_seed.currentIndexChanged.connect(self.seed_chromo_changed)


    def seed_chromo_changed(self):
        self.chro_bar_create(self.chromo_seed.currentText())
        self.fill_Chromo_Text()


    def min_max_changed(self):
        if int(self.min_chromo.currentText()) > int(self.max_chromo.currentText()):
            QtWidgets.QMessageBox.question(self, "Maximum cant be less than Minimum",
                                           "The Minimum number of repeats cant be more than the Maximum",
                                           QtWidgets.QMessageBox.Ok)
        else:
            self.fill_seed_id_chrom()




    # connects to view->CASPER to switch back to the main CASPER window
    def changeto_main(self):
        GlobalSettings.mainWindow.show()
        self.hide()

    # connects to go back button in bottom left to switch back to the main CASPER window
    def go_back(self):
        GlobalSettings.mainWindow.show()
        self.hide()

    # this function calls the closingWindow class.
    def closeEvent(self, event):
        GlobalSettings.mainWindow.closeFunction()
        event.accept()

