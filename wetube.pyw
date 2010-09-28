#!/usr/bin/env python

import os
import sys
import time
import urllib2
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import utube

__author__ = "Viranch Mehta"
__author_email__ = "viranch.mehta@gmail.com"
__version__ = '0.9'

class Item (QTreeWidgetItem):

	def __init__ (self, parent, columns):
		super (Item, self).__init__(parent, columns)
		self.info = {}
		self.parent = parent
		self.ref_url = ''
		self.target_dir = ''
		self.vid_id = ''
		
		self.title = 'This video'
		self.pbar = QProgressBar()
		self.downloader = QThread()
		self.downloader.run = self.download
		self.stop_download = False
		self.t = QThread()
		self.t.run = self.extract_info

	def extract_info (self):
		self.setText (1, 'Extracting info')
		if self.info=={}:
			self.info = utube.get_video_info(self.ref_url)
		if self.info == None:
			self.t.emit (SIGNAL('error()'))
			self.setText (1, 'Error')
			self.stop_download = True
			return

		self.info['ref_url'] = self.ref_url
		if self.info['title']=='':
			self.info['stitle'] = self.text(0)
		else:
			self.title = self.info['title']
		
		if self.info['title']!='':
			self.setText (0, self.info['title'])
		self.setText (4, self.info['ext']+' ('+str(self.info['format'])+')')
		self.info['target'] = self.target_dir+os.sep+self.info['stitle']+'.'+self.info['ext']
		self.setText (5, self.info['target'])
		self.setText (1, '')
		self.getSize()

	def getSize (self):
		try:
			l=self.info['length']
		except KeyError:
			req = urllib2.Request(self.info['url'], None, utube.std_headers)
			f = urllib2.urlopen ( req )
			l = self.info['length'] = int( f.info()['Content-length'] )
			f.close()
		if l > 1024*1024:
			self.setText ( 3, str(round(l/1024.0/1024.0, 2))+' MB' )
		elif l > 1024:
			self.setText ( 3, str(round(l/1024.0, 2))+' KB' )
		else:
			self.setText ( 3, str(l)+' B' )
		self.pbar.setRange (0, l)
		if os.path.isfile (self.info['target']):
			self.downloader.emit ( SIGNAL('doneSize(int)'), os.path.getsize(self.info['target']) )

	def download (self):
		if self.stop_download:
			return
		self.setText (1, 'Downloading')
		done_size = 0
		req = urllib2.Request(self.info['url'], None, utube.std_headers)
		open_mode = 'wb'
		if os.path.isfile (self.info['target']):
			done_size = os.path.getsize (self.info['target'])
			req.add_header ('Range', 'bytes=%d-' % done_size)
			open_mode = 'ab'
		self.downloader.emit (SIGNAL('doneSize(int)'), done_size)
		if done_size>=self.info['length']:
			self.setText (1, 'Complete')
			return
		
		vid = open ( self.info['target'], open_mode )
		f = urllib2.urlopen ( req )
		while done_size<self.info['length'] and not self.stop_download:
			s = f.read (1024*5)
			vid.write (s)
			done_size += len(s)
			self.downloader.emit (SIGNAL('doneSize(int)'), done_size)
		f.close()
		vid.close()
		if self.stop_download:
			self.setText (1, 'Paused')
		else:
			self.setText (1, 'Complete')

class MainWindow(QMainWindow):

	def __init__ ( self, parent=None ):
		super (MainWindow, self).__init__(parent)

		icon = lambda name: QIcon (os.path.dirname(__file__)+'/icons/'+name)

		self.toolbar = self.addToolBar ('Toolbar')
		self.status = self.statusBar()
		self.status.showMessage ('Ready')

		self.table = QTreeWidget()
		headerItem = self.table.headerItem()
		headerItem.setIcon (0, QIcon(icon('applications-multimedia.png')))
		headerItem.setText (0, 'Title')
		#headerItem.setIcon (1, QIcon(icon('flag-green.png')))
		headerItem.setText (1, 'Status')
		#headerItem.setIcon (2, QIcon(icon('flag-red.png')))
		headerItem.setText (2, 'Downloaded')
		#headerItem.setIcon (3, QIcon(icon('edit-copy.png')))
		headerItem.setText (3, 'Size')
		#headerItem.setIcon (4, QIcon(icon('edit-copy.png')))
		headerItem.setText (4, 'Format')
		#headerItem.setIcon (5, QIcon(icon('flag-green.png')))
		headerItem.setText (5, 'Location')
		self.table.setRootIsDecorated (False)

		addAction = self.createAction ('Add', self.add, QKeySequence.New, 'Add...', icon('document-new.png'))
		rmAction = self.createAction ('Remove', self.remove, QKeySequence.Delete, 'Remove', icon('edit-delete.png'))
		clearAction = self.createAction ('Clear', self.clear, 'Shift+Del', 'Clear', icon('edit-clear-list.png'))
		startAction = self.createAction ('Start/Resume', self.download, QKeySequence.Save, 'Start/Resume Download', icon('media-playback-start.png'))
		pauseAction = self.createAction ('Pause', self.pause, None, 'Pause Download', icon('media-playback-pause.png'))
		aboutAction = self.createAction ('About', self.about, None, 'About', icon('help-about.png'))
		quitAction = self.createAction ('Quit', self.quit, 'Ctrl+Q', 'Quit', icon('application-exit.png'))
		
		self.toolbar.addAction ( addAction )
		self.toolbar.addAction ( rmAction )
		self.toolbar.addAction ( clearAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( startAction )
		self.toolbar.addAction ( pauseAction )
		self.toolbar.addSeparator()
		self.toolbar.addAction ( aboutAction )
		self.toolbar.addAction ( quitAction )
		
		self.tray = QSystemTrayIcon()
		self.tray.setIcon ( icon('tool-animator.png') )
		self.tray.setVisible (True)
		self.trayMenu = QMenu()
		toggleAction = self.createAction ('Show/Hide', self.toggleWindow)
		self.trayMenu.addAction (toggleAction)
		self.trayMenu.addSeparator()
		self.trayMenu.addAction (quitAction)
		self.tray.setContextMenu (self.trayMenu)

		self.setCentralWidget (self.table)
		self.setWindowTitle ('WeTube')
		self.setWindowIcon ( QIcon(icon('acroread.png')) )
		
		self.connect ( self.tray, SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.toggleWindow )

	def loadPrefs (self):
		settings = QSettings ('WeTube', 'WeTube')
		cnt = settings.value('count').toInt()[0]
		for i in range(cnt):
			settings.beginGroup('vid'+str(i))
			vid_id = str ( settings.value('vid_id').toString() )
			ref_url = str ( settings.value('ref_url').toString() )
			if vid_id == '':
				vid_id = utube.get_video_id (ref_url)
			curr = Item (self.table, ['video_'+vid_id, '', '', '', '', ''])
			curr.vid_id = vid_id
			curr.target_dir = os.sep.join (str ( settings.value('target').toString() ).split(os.sep)[:-1])
			curr.ref_url = ref_url
			if len(settings.allKeys())>2:
				for key in settings.allKeys():
					curr.info[str(key)] = str ( settings.value(key).toString() )
			settings.endGroup()
			try: curr.info['length'] = int ( curr.info['length'] )
			except KeyError: pass
			self.add (curr)

	def add (self, new_item=None, startDownload=False):
		if new_item == None:
			import new
			dlg = new.NewDlg(self)
			if dlg.exec_():
				url = str(dlg.urlEdit.text()).strip()
				new_item = Item (self.table, ['video_'+str(dlg.vid_id), '', '', '', '', ''])
				new_item.ref_url = url
				new_item.vid_id = str(dlg.vid_id)
				new_item.target_dir = str(dlg.savetoEdit.text())
				self.add (new_item, dlg.startDownload.isChecked())
		else:
			self.table.addTopLevelItem ( new_item )
			self.table.setItemWidget ( new_item, 2, new_item.pbar )
			self.status.showMessage ('Video added.', 5000)
			self.connect (new_item.t, SIGNAL('error()'), self.trouble)
			self.connect (new_item.downloader, SIGNAL('doneSize(int)'), new_item.pbar.setValue)
			new_item.t.start()
			if startDownload:
				if new_item.t.isRunning():
					self.connect (new_item.t, SIGNAL('finished()'), new_item.downloader.start)
				elif not new_item.stop_download:
					new_item.downloader.start()

	def remove (self):
		if self.table.topLevelItemCount() == 0:
			self.status.showMessage ('Nothing to remove!', 5000)
			return None
		curr = self.table.currentItem()
		if curr is None:
			self.status.showMessage ('No video selected!', 5000)
			return
		if curr.downloader.isRunning():
			curr.stop_download = True
			curr.downloader.wait()
		if curr.t.isRunning():
			curr.t.terminate()
			curr.t.wait()
		self.table.takeTopLevelItem ( self.table.indexOfTopLevelItem(curr) )
		self.status.showMessage ('Removed', 5000)

	def clear (self):
		cnt = self.table.topLevelItemCount()
		if cnt==0:
			self.status.showMessage ('List already clear!', 5000)
			return None
		for i in range (0, cnt):
			curr = self.table.topLevelItem (i)
			if curr.downloader.isRunning():
				curr.stop_download = True
				curr.downloader.wait()
			if curr.t.isRunning():
				curr.t.terminate()
				curr.t.wait()
		self.table.clear()
		self.status.showMessage ('List cleared', 5000)

	def download (self):
		curr = self.table.currentItem()
		if curr is None:
			return
		if curr.t.isRunning():
			self.connect (curr.t, SIGNAL('finished()'), curr.downloader.start)
		elif not curr.downloader.isRunning():
			curr.downloader.start()
	
	def pause (self):
		curr = self.table.currentItem()
		if curr is None:
			return
		if curr.downloader.isRunning():
			curr.stop_download = True
			curr.downloader.wait()
			curr.stop_download = False

	def trouble (self):
		QMessageBox.critical (self, 'Error', utube._err[0])

	def about (self):
		return

	def closeEvent(self, event):
		if self.isVisible():
			self.hide()
		event.ignore()

	def toggleWindow (self, reason=QSystemTrayIcon.Trigger):
		if reason == QSystemTrayIcon.Trigger:
			self.hide() if self.isVisible() else self.show()

	def quit (self):
		settings = QSettings ('WeTube', 'WeTube')
		cnt = self.table.topLevelItemCount()
		settings.setValue ('count', cnt)
		for i in range (cnt):
			curr = self.table.topLevelItem (i)
			if curr.t.isRunning():
				curr.t.terminate()
			if curr.downloader.isRunning():
				curr.stop_download = True
				curr.downloader.wait()
			settings.beginGroup ('vid'+str(i))
			for key in curr.info.keys():
				settings.setValue (key, curr.info[key])
			if curr.info == {}:
				settings.setValue ('ref_url', curr.ref_url)
				settings.setValue ('target', curr.target_dir+os.sep)
			settings.endGroup()
		qApp.quit()

	def createAction (self, text, slot=None, shortcut=None, tip=None, icon=None, checkable=False, signal='triggered()'):
		action = QAction (text, self)
		if icon is not None:
			action.setIcon (icon)
		if shortcut is not None:
			action.setShortcut (shortcut)
		if tip is not None:
			action.setToolTip (tip)
			action.setStatusTip (tip)
		if slot is not None:
			self.connect (action, SIGNAL(signal), slot)
		action.setCheckable (checkable)
		return action

if __name__=='__main__':
	app = QApplication (sys.argv)
	window = MainWindow()
	window.showMaximized()
	window.loadPrefs()
	app.exec_()
