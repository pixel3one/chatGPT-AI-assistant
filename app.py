import os
import sys
from datetime import datetime
from configparser import ConfigParser
import markdown
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QSlider,
							 QTabWidget, QTextEdit, QTextBrowser, QMenu, QMenuBar, QSplitter, 
							 QToolButton, QStatusBar,
							 QHBoxLayout, QVBoxLayout, QFormLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent, QThread
from PyQt6.QtGui import QIcon, QTextCursor, QShortcut, QKeySequence
from chatgpt import ChatGPT
from db import ChatGPTDatabase

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)		

def current_timestamp(format_pattern='%y_%m_%d_%H%M%S'):
	return datetime.now().strftime(format_pattern)

class ChatGPTThread(QThread):
	clear_input = pyqtSignal()
	response_received = pyqtSignal(dict)	

	def __init__(self, parent):
		super().__init__(parent)
		self.ai_assistant = parent
		
	def run(self):
		text_string = self.ai_assistant.message_input.toHtml()
		self.clear_input.emit()
		
		# make an api call to OpenAI ChatGPT model
		max_tokens = self.ai_assistant.max_tokens.value()
		temperature = float('{0:.2f}'.format(self.ai_assistant.temperature.value() / 100))
		response = self.ai_assistant.chatgpt.send_request(text_string.strip(), max_tokens=max_tokens, temperature=temperature)
		self.clear_input.emit()
		self.response_received.emit(response)

class AIAssistant(QWidget):
	def __init__(self, parent=None):
		super().__init__()
		self.chatgpt = ChatGPT(API_KEY)
		self.t = ChatGPTThread(self)

		self.layout = {}
		self.layout['main'] = QVBoxLayout()
		self.setLayout(self.layout['main'])

		self.init_ui()
		self.init_set_default_settings()
		self.init_configure_signals()

		self.t = ChatGPTThread(self)
		self.t.clear_input.connect(self.message_input.clear)
		self.t.response_received.connect(self.update_covnersation_window)

	def init_ui(self):
		# add sub layout manager
		self.layout['inputs'] = QFormLayout()

		# add sliders
		self.max_tokens = QSlider(Qt.Orientation.Horizontal, minimum=10, maximum=100000, singleStep=500, pageStep=500, value=200, toolTip='Maxium token ChatGPT can consume')
		self.temperature = QSlider(Qt.Orientation.Horizontal, minimum=0, maximum=200, value=10, toolTip='Randomness of the response')

		# organize widgets	  
		# ----------------	  
		# maximum token slider
		self.max_token_value = QLabel('0.0')
		self.layout['slider_layout'] = QHBoxLayout()
		self.layout['slider_layout'].addWidget(self.max_token_value)
		self.layout['slider_layout'].addWidget(self.max_tokens)
		self.layout['inputs'].addRow(QLabel('Token Limit:'), self.layout['slider_layout'])

		# temperature slider
		self.temperature_value = QLabel('0.0')
		self.layout['slider_layout2'] = QHBoxLayout()
		self.layout['slider_layout2'].addWidget(self.temperature_value)
		self.layout['slider_layout2'].addWidget(self.temperature)
		self.layout['inputs'].addRow(QLabel('Temperature:'), self.layout['slider_layout2'])
		self.layout['main'].addLayout(self.layout['inputs'])

		splitter = QSplitter(Qt.Orientation.Vertical)		
		self.layout['main'].addWidget(splitter)

		# conversation window
		self.conversation_window = QTextBrowser(openExternalLinks=True)
		self.conversation_window.setReadOnly(True)
		splitter.addWidget(self.conversation_window) 

		self.intput_window = QWidget()
		self.layout['input entry'] = QHBoxLayout(self.intput_window)

		self.message_input = QTextEdit(placeholderText='Enter your prompt here')
		self.message_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.layout['input entry'].addWidget(self.message_input)

		# create buttons
		self.btn_submit = QPushButton('&Submit', clicked=self.post_message)
		self.btn_clear = QPushButton('&Clear', clicked=self.reset_input)
		# self.btn_test = QPushButton('&Test', clicked=self.test)

		self.layout['buttons'] = QVBoxLayout()
		self.layout['buttons'].addWidget(self.btn_submit)
		self.layout['buttons'].addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignTop)
		# self.layout['buttons'].addWidget(self.btn_test, alignment=Qt.AlignmentFlag.AlignTop)
		self.layout['input entry'].addLayout(self.layout['buttons'])

		splitter.addWidget(self.intput_window)
		splitter.setSizes([800, 200])

		# add status bar
		self.status = QStatusBar()
		self.status.setStyleSheet('font-size: 12px; color: white;')
		self.layout['main'].addWidget(self.status)

	def init_set_default_settings(self):
		# token slider
		self.max_tokens.setTickPosition(QSlider.TickPosition.TicksBelow)
		self.max_tokens.setTickInterval(500)
		self.max_tokens.setTracking(True)
		self.max_token_value.setText('{0:,}'.format(self.max_tokens.value()))

		# temperature slider
		self.temperature.setTickPosition(QSlider.TickPosition.TicksBelow)
		self.temperature.setTickInterval(10)
		self.temperature.setTracking(True)
		self.temperature_value.setText('{0:.2f}'.format(self.temperature.value() / 100))

	def init_configure_signals(self):
		self.max_tokens.valueChanged.connect(lambda: self.max_token_value.setText('{0: ,}'.format(self.max_tokens.value())))
		self.temperature.valueChanged.connect(lambda: self.temperature_value.setText('{0: .2f}'.format(self.temperature.value() / 100)))

	def update_covnersation_window(self, message):			
		if 'error' in message:
			self.status.setStyleSheet('''
				color: red;
			''')
			self.clear_input()
			self.status.showMessage(message['error'].user_message)
			return
		
		self.status.setStyleSheet('''
			color: white;
		''')

		cursor = self.conversation_window.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.End)
		self.conversation_window.setTextCursor(cursor)

		markdown_converted = markdown.markdown(message['content']) + '<p></p>'
		self.conversation_window.insertHtml('<p style="color:#fd9620"> <strong>[ChatGPT]: </strong><br>')
		self.conversation_window.insertHtml(markdown_converted)
		self.conversation_window.insertHtml('<br>')

		self.status.showMessage('Tokens used: {0}'.format(message['usage']))
			
		self.btn_submit.setEnabled(True)
		self.btn_submit.setText('&Submit')

	def post_message(self):
		if not self.message_input.toPlainText():
			self.status.showMessage('Prompt field is empty.')
			return
		else:
			self.status.clearMessage()

		self.btn_submit.setEnabled(False)
		self.btn_submit.setText('Waiting...')

		text_string = self.message_input.toHtml()

		cursor = self.conversation_window.textCursor()
		cursor.movePosition(QTextCursor.MoveOperation.End)
		self.conversation_window.setTextCursor(cursor)

		self.conversation_window.insertHtml('<p style="color:#5caa00"> <strong>[User]: </strong><br>')
		self.conversation_window.insertHtml(text_string)
		self.conversation_window.insertHtml('<br')
		self.conversation_window.insertHtml('<br')
	
		self.t.start()
		self.t.quit()

	def reset_input(self):
		self.message_input.clear()		
		self.status.clearMessage()

	def clear_input(self):
		self.btn_submit.setEnabled(True)
		self.btn_submit.setText('&Submit')
		self.message_input.clear()

	def zoom_in(self):
		font = self.message_input.font()
		# increase font size only when current size is less than 30 pixel
		if font.pixelSize() < 30:
			self.message_input.setStyleSheet('font-size: {0}px'.format(font.pixelSize() + 2))
			self.conversation_window.setStyleSheet('font-size: {0}px;'.format(font.pixelSize() + 2))

	def zoom_out(self):		
		font = self.message_input.font()
		# decrease font size only when current size is smaller than 5
		if font.pixelSize() > 5:
			self.message_input.setStyleSheet('font-size: {0}px'.format(font.pixelSize() - 2))
			self.conversation_window.setStyleSheet('font-size: {0}px;'.format(font.pixelSize() - 2))		
	
class TabManager(QTabWidget):
	# add customized signals
	plusClicked = pyqtSignal()

	def __init__(self, parent=None):
		super().__init__(parent)
		# add tab close button
		self.setTabsClosable(True)

		# Create the add tab button and implement signals
		self.add_tab_button = QToolButton(self, text='+')
		self.add_tab_button.clicked.connect(self.plusClicked)
		self.setCornerWidget(self.add_tab_button)

		self.tabCloseRequested.connect(self.closeTab)

	def closeTab(self, tab_index):
		if self.count() == 1:
			return  
		self.removeTab(tab_index)

class AppWindow(QWidget):
	def __init__(self):
		super().__init__()
		self.window_width, self.window_height = 720, 720
		self.setMinimumSize(self.window_width, self.window_height)
		self.setWindowIcon(QIcon(resource_path('robot.png')))
		# self.setWindowIcon(QIcon(os.path.join(os.getcwd(), 'robot.png')))
		self.setWindowTitle('ChatGPT AI Assistant (By Glen Gemeniano) v-1')
		self.setStyleSheet('''
			QWidget {
				font-size: 15px;				
			}
		''') 
		self.tab_index_tracker = 1	
		self.layout = {}

		self.layout['main'] = QVBoxLayout()
		self.setLayout(self.layout['main'])

		self.layout['main'].insertSpacing(0, 19)

		self.init_ui()
		self.init_configure_signal()
		self.init_menu()
		self.init_shortcut_assignment()

	def init_ui(self):
		# add tab  manager
		self.tab_manager = TabManager()
		self.layout['main'].addWidget(self.tab_manager)

		# ai_assistant = AIAssistant()
		self.tab_manager.addTab(AIAssistant(), 'Conversation #{0}'.format(self.tab_index_tracker))
		self.set_tab_focus()

	def init_menu(self):
		self.menu_bar = QMenuBar(self)

		file_menu = QMenu('&File', self.menu_bar)
		file_menu.addAction('&Save output', self.save_output)
		file_menu.addAction('S&ave log do DB', self.save_conversation_log_to_db)
		self.menu_bar.addMenu(file_menu)

		# view menu
		view_menu = QMenu('&View', self.menu_bar)
		view_menu.addAction('Zoom &in', self.zoom_in)
		view_menu.addAction('Zoom &out', self.zoom_out)
		self.menu_bar.addMenu(view_menu)

	def init_shortcut_assignment(self):
		shortcut_add_tab = QShortcut(QKeySequence('Ctrl+Shift+A'), self)
		shortcut_add_tab.activated.connect(self.add_tab)

	def init_configure_signal(self):
		self.tab_manager.plusClicked.connect(self.add_tab)

	def set_tab_focus(self):
		activate_tab = self.tab_manager.currentWidget()
		activate_tab.message_input.setFocus()

	def add_tab(self):
		self.tab_index_tracker += 1
		# ai_assistant = AIAssistant()
		self.tab_manager.addTab(AIAssistant(), 'Conversation #{0}'.format(self.tab_index_tracker))
		self.tab_manager.setCurrentIndex(self.tab_manager.count()-1)
		self.set_tab_focus()

	def save_output(self):
		active_tab = self.tab_manager.currentWidget()
		conversation_window_log = active_tab.conversation_window.toPlainText()
		timestamp = current_timestamp()
		with open('{0}_Chat Log.txt'.format(timestamp), 'w', encoding='UTF-8') as _f:
			_f.write(conversation_window_log)
		active_tab.status.showMessage('''File saved at {0}/{1}_Chat Log.txt'''.format(os.getcwd(), timestamp))

	def save_conversation_log_to_db(self):		
		timestamp = current_timestamp('%Y-%m-%d %H:%M:%S')		
		active_tab = self.tab_manager.currentWidget()
		messages = str(active_tab.chatgpt.messages).replace("'", "''")
		values = f"'{messages}','{timestamp}'"

		db.insert_record('message_logs', 'messages, created', values)
		active_tab.status.showMessage('Record inserted')

	def closeEvent(self, event):
		"""
		QWidget Close event
		"""
		db.close()

		# close threads
		for window in self.findChildren(AIAssistant):
			window.t.quit()

	def zoom_in(self):
		active_tab = self.tab_manager.currentWidget()
		active_tab.zoom_in()
   
	def zoom_out(self):
		active_tab = self.tab_manager.currentWidget()
		active_tab.zoom_out()

if __name__ == '__main__':
	# load openai API key
	config = ConfigParser()
	config.read('api_key.ini')
	API_KEY = config.get('openai', 'APIKEY')

	# init ChatGPT SQLite database
	db = ChatGPTDatabase('chatgpt.db')
	db.create_table(
		'message_logs ',
		'''
			message_log_no INTEGER PRIMARY KEY AUTOINCREMENT,
			messages TEXT,
			created TEXT
		'''
	)

	# construct application instance
	app = QApplication(sys.argv)
	app.setStyle('fusion')

	# load css skin
	qss_style = open(resource_path('css_skins/dark_orange_style.qss'), 'r')
	app.setStyleSheet(qss_style.read())

	# launch app window
	app_window = AppWindow()
	app_window.show()

	sys.exit(app.exec())