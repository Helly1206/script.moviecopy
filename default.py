import os
import xbmc
import xbmcaddon
import xbmcgui
from xbmc import getCondVisibility as condition, translatePath as translate, log as xbmc_log
from subprocess import PIPE, Popen
import multiprocessing
import shutil

__scriptdebug__ = False
__guitest__ = False

__addon__      = xbmcaddon.Addon()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__datapath__ = xbmc.translatePath(os.path.join('special://temp/', __addonname__))
__logfile__ = os.path.join(__datapath__, __addonname__ + '.log')
__LS__ = __addon__.getLocalizedString

# Globals needed for writeLog()
LASTMSG = ''
MSGCOUNT = 0
#

#path and icons
__path__ = os.path.dirname(os.path.abspath(__file__))
__filename__ = os.path.basename(os.path.abspath(__file__))

__IconStop__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'stop.png'))
__IconError__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'error.png'))
__IconMovieRoll__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'movieroll.png'))

#Load all settings
__src_folder__ = __addon__.getSetting('src_folder') #"/mnt/htpc_disk/test/" 
__dest_folder1__ = __addon__.getSetting('dest_folder1')
__dest_folder2__ = __addon__.getSetting('dest_folder2')
__dest_folder3__ = __addon__.getSetting('dest_folder3')
__dest_folder4__ = __addon__.getSetting('dest_folder4')
__dest_folder5__ = __addon__.getSetting('dest_folder5')
__entire_folder__ = True if __addon__.getSetting('entire_folder').upper() == 'TRUE' else False
__video_files__ = __addon__.getSetting('video_files').lower()
__subtitle_files__ = True if __addon__.getSetting('subtitle_files').upper() == 'TRUE' else False
__background_copy__ = True if __addon__.getSetting('background_copy').upper() == 'TRUE' else False
__move_files__ = True if __addon__.getSetting('move_files').upper() == 'TRUE' else False
__remove_source__ = True if __addon__.getSetting('remove_source').upper() == 'TRUE' else False
__timeout_rate__ = int(__addon__.getSetting('timeout_rate'))

__video_extensions__ = xbmc.getSupportedMedia('video')
__video_extensions2__ = __video_extensions__.decode('utf-8').split('|')
__subs_extensions__ = ".srt|.idx|.sub|.smi|.ssa"
__subs_extensions2__ = __subs_extensions__.decode('utf-8').split('|')

DLG_TYPE_FOLDER = 0
DLG_TYPE_FILE = 1

PB_BUSY = 0
PB_CANCELED = 1
PB_TIMEOUT = 2

####################################### GLOBAL FUNCTIONS #####################################

def notifyOSD(header, message, icon):
    xbmc.executebuiltin('XBMC.Notification(%s,%s,5000,%s)' % (header.encode('utf-8'), message.encode('utf-8'), icon))

def writeDebug(message, level=xbmc.LOGNOTICE):
    if __scriptdebug__ == True:
        writeLog("[Debug] %s" % message, level)

def writeLog(message, level=xbmc.LOGNOTICE):
    global LASTMSG, MSGCOUNT
    if LASTMSG == message:
        MSGCOUNT = MSGCOUNT + 1
        return
    else:
        LASTMSG = message
        MSGCOUNT = 0
        xbmc.log('%s: %s' % (__addonid__, message.encode('utf-8')), level)  

def GUI_Browse(title, defaultPath=None, dialogType=DLG_TYPE_FILE, mask=''):
        """

        @param title:
        @param dialogType: Integer - 0 : ShowAndGetDirectory
                                     1 : ShowAndGetFile
                                     2 : ShowAndGetImage
                                     3 : ShowAndGetWriteableDirectory

        shares         : string or unicode - from sources.xml. (i.e. 'myprograms')
        mask           : [opt] string or unicode - '|' separated file mask. (i.e. '.jpg|.png')
        useThumbs      : [opt] boolean - if True autoswitch to Thumb view if files exist.
        treatAsFolder  : [opt] boolean - if True playlists and archives act as folders.
        default        : [opt] string - default path or file.

        enableMultiple : [opt] boolean - if True multiple file selection is enabled.

        """
        if defaultPath is None:
            defaultPath = xbmc.translatePath("special://home")

        browseDialog = xbmcgui.Dialog()
        destFolder = browseDialog.browse(dialogType, title, 'programs', mask, True, True, defaultPath)
        if destFolder == defaultPath:
            destFolder = ""
        return destFolder

def GUI_SelectSourceFolder(defaultPath=None):
	return GUI_Browse(__LS__(50000), defaultPath, dialogType=DLG_TYPE_FOLDER)

def GUI_LookupDestination():
    nfolders=0
    dest = []
    DestinationFolder = ""
    if __dest_folder1__: 
        nfolders += 1
        dest.append(__dest_folder1__)
    if __dest_folder2__: 
        nfolders += 1
        dest.append(__dest_folder2__)
    if __dest_folder3__:
        nfolders += 1
        dest.append(__dest_folder3__)
    if __dest_folder4__:
        nfolders += 1
        dest.append(__dest_folder4__)
    if __dest_folder5__: 
        nfolders += 1
        dest.append(__dest_folder5__)

    if nfolders == 1:
        DestinationFolder = dest[0]
    elif nfolders > 1:
        dialog = xbmcgui.Dialog()
        selected = dialog.select(__LS__(50001), dest)
        if selected != -1:
            DestinationFolder = dest[selected]
            
    writeDebug('Selected Destination: %s' % DestinationFolder)

    return DestinationFolder


####################################### MOVIECOPY FUNCTIONS #####################################

# CopyFiles
class CopyFiles(object):
    def __init__(self):
        self.p = None

    def CopyFolder(self, source, destination):
        try:
            if os.path.exists(destination):
                if os.path.isdir(destination):
                    self.RemoveFolder(destination)
                else:
                    os.remove(destination)
            if __move_files__ == True:
                os.renames(source, destination)
            else:
                shutil.copytree(source, destination)
        except IOError, e:
            notifyOSD(__addonname__,__LS__(50002) % e,__IconError__);
        return 0

    def CopyFiles(self, files, destination):
        try:
            for f in files:
                if __move_files__ == True:
                    shutil.move(f, destination)
                else:
                    shutil.copy(f, destination)
        except IOError, e:
            notifyOSD(__addonname__,__LS__(50003) % e,__IconError__);
        return 0

    def RemoveFolder(self, source):
        try:
            shutil.rmtree(source)
        except IOError, e:
            notifyOSD(__addonname__,__LS__(50004) % e,__IconError__);
        return 0

    def proc_copy(self, source, destination, files):
        if __entire_folder__ == True:
            writeDebug("Copy entire folder %s" % source)
            self.CopyFolder(source, destination)
        else:
            writeDebug("Copy files %s" % files)
            self.CopyFiles(files, destination)
        if __remove_source__ == True:
            writeDebug("Remove Source: %s" % source)
            self.RemoveFolder(source)            

    def StartCopy(self, source, destination, files):
        self.p = multiprocessing.Process(target=self.proc_copy, args=(source, destination, files))
        self.p.start()

    def BusyCopy(self):
        return self.p.is_alive()

    def KillCopy(self,wait):
        #hope we'll never need it, not a very nice solution
        cmdline('kill -9 %s'%(format(self.p.pid)))
        if wait: self.p.join()

#CopyProgress
class CopyProgressBar(object):
    def __init__(self, MovieName="", log=False):
        self.log = log
        self.f = None
        self.header = __LS__(50005) % (MovieName)
        self.message = __LS__(50006)
        self.time = 0
        self.percent = 0
        self.size = 0
        if __background_copy__:
            self.pb = xbmcgui.DialogProgressBG()
        else:
            self.pb = xbmcgui.DialogProgress()
        self.timeout = 0       

    def GetTime(self, time):
        rettime = ""
        if (time < 60):
            rettime = ("%ds" % (time))
        else:
            rettime = ("%d:%02d" % (time/60,time%60))
        return rettime

    def GetRate(self, done): 
        if done == 0 or self.time == 0:
            return "0.0"
        return ("%.1f" % (float(done)/(float(self.time)*1024.0*1024.0)))

    def GetETA(self, done):
        if done == 0 or self.time == 0:
            return "Inf"
        else:
            rate = float(done)/float(self.time)
            timetbd = (self.size/rate) - self.time
        return self.GetTime(timetbd)

    def Create(self, size):
        retval = PB_BUSY
        self.size = size
        if __timeout_rate__ > 0:
            self.timeout = size/(__timeout_rate__*1024*1024)
        writeDebug("Copy Timeout: %d s" % (self.timeout))
        if self.log:
            if not os.path.exists(__datapath__): os.makedirs(__datapath__)
            self.f = open(__logfile__, 'w')

        if self.size > 0:
            self.pb.create(self.header,self.message % (self.GetTime(self.time),self.GetETA(0),self.GetRate(0),str(self.percent)))
            self.pb.update(self.percent)
        else:
            retval = PB_CANCELED
        return retval

    def Update(self, done):
        retval = PB_BUSY
        if not __background_copy__:
	    if self.pb.iscanceled():
               retval = PB_CANCELED
	if self.timeout > 0 and self.time > self.timeout:
            retval = PB_TIMEOUT
        if retval == PB_BUSY:
            self.percent = int(done * 100 / self.size)
            self.pb.update(self.percent, self.header, self.message % (self.GetTime(self.time),self.GetETA(done),self.GetRate(done),str(self.percent)))
            writeDebug(self.message % (self.GetTime(self.time),self.GetETA(done),self.GetRate(done),str(self.percent)))
            if self.log:
                self.f.write('%s, %s, %s, %s\n' % (self.GetTime(self.time),self.GetETA(done),self.GetRate(done),str(self.percent)))
        return retval

    def Wait(self):
        xbmc.sleep(1000)
        self.time += 1

    def UpdateAndWait(self, done):
        retval = self.Update(done)
        if retval == PB_BUSY:
            self.Wait()
        return retval

    def Close(self):
        self.pb.close()
        if self.log:
            self.f.close()

# FileInfo
class FileInfo(object):
    #def __init__(self):

    def GetDestination(self, destfolder, filename):
        return os.path.join(destfolder,self.GetFileName(filename))

    def CheckDestination(self, destination):
        rv = True
        if not os.path.isdir(destination):
            if not os.path.exists(destination):
                os.mkdir(destination)
            else:
                rv = False
        return rv

    def GetFileName(self, filename, slash=True):
        if filename[-1:] == "/":
            head, tail = os.path.split(filename)
            head, tail = os.path.split(head)
            if slash:
                tail = "%s/" % tail
        else: 
            head, tail = os.path.split(filename)
        return tail

    def IsVideoFile(self,filename):
        name, ext = os.path.splitext(filename)
        return ext.lower() in __video_extensions2__

    def IsSubtitleFile(self,filename):
        name, ext = os.path.splitext(filename)
        return ext.lower() in __subs_extensions2__

    def GetSelectVideoFiles(self, folder, files):
        if __video_files__ == "select":
            vfiles = []
            nvfiles = len(self.GetVideoFiles(folder, vfiles))
            vfile = GUI_Browse(__LS__(50007), defaultPath=folder, dialogType=DLG_TYPE_FILE, mask=__video_extensions__)
            if vfile:
                if os.path.exists(vfile):
                    if self.IsVideoFile(vfile):
                        files.append(vfile)
                        selectedvfiles = 1
                while selectedvfiles < nvfiles and vfile:
                    vfile = GUI_Browse(__LS__(50008), defaultPath=folder, dialogType=DLG_TYPE_FILE, mask=__video_extensions__)
                    if vfile:
                        if os.path.exists(vfile):
                            if self.IsVideoFile(vfile):
                                files.append(vfile)
                                selectedvfiles += 1
        else:
            files = self.GetVideoFiles(folder, files)
            if __video_files__ == "largest":
                files = self.GetLargestVideoFile(files)
        return files

    def GetLargestVideoFile(self, files):
        retfiles = []
        writeDebug("Select largest video file")
        lsize = 0 
        for f in files:
            if self.IsVideoFile(f):
                if os.path.getsize(f) > lsize: # or lsize == 0:
                    lsize = os.path.getsize(f)
                    lfile = f
            else:
                retfiles.append(f) # hold non video files
        if lsize > 0:
            retfiles.append(lfile)
        return retfiles;

    def GetVideoFiles(self, folder, files):
        if os.path.isdir(folder):
            for item in os.listdir(folder):
                itempath = os.path.join(folder, item)
                if os.path.isfile(itempath):
                    if self.IsVideoFile(itempath):
                        files.append(itempath)
                elif os.path.isdir(itempath):
                    files = self.GetVideoFiles(itempath, files)
        return files

    def GetSubtitleFiles(self, folder, files):
        if os.path.isdir(folder):
            for item in os.listdir(folder):
                itempath = os.path.join(folder, item)
                if os.path.isfile(itempath):
                    if self.IsSubtitleFile(itempath):
                        files.append(itempath)
                elif os.path.isdir(itempath):
                    files = self.GetSubtitleFiles(itempath, files)
        return files

    def GetFilesSize(self, folder, files):
        if os.path.isdir(folder):
            total_size = os.path.getsize(folder)
            if files != []:
                for s in files:         
                    if os.path.isfile(s):
                        total_size += os.path.getsize(s)
        else:
            total_size = 0
        return total_size

    def GetFolderSize(self, folder):
        if os.path.isdir(folder):
            total_size = os.path.getsize(folder)
            for item in os.listdir(folder):
                itempath = os.path.join(folder, item)
                if os.path.isfile(itempath):
                    total_size += os.path.getsize(itempath)
                elif os.path.isdir(itempath):
                    total_size += self.GetFolderSize(itempath)
        else:
            total_size = 0
        return total_size

    def BuildFilesList(self, folder):
        files = []
        if os.path.isdir(folder):
            files = self.GetSelectVideoFiles(folder, files);
            files = self.GetSubtitleFiles(folder, files);
        return files

####################################### SETTINGS FUNCTIONS #####################################

def cmdline(command):
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return process.communicate()[0]


def PrintHelp():
    writeLog("MovieCopy Usage: ")
    writeLog("No arguments: GUI controlled, with arguments: external access")
    writeLog("-l: log the copy progress in logfile")
    writeLog("-h: show this help")
    writeLog("-s <folder>: Select source folder")
    writeLog("-f <file1|file2|filen>: Select source files (seperated by '|')")
    writeLog("-d <folder>: Select destination")

####################################### START MAIN SERVICE #####################################

writeLog("MovieCopy Started ...")

__manual_source__ = True
__manual_files__ = True
__manual_destination__ = True
__log_progress__ = False

if len(sys.argv) > 1:
    i = 1
    cmd = True
    while i < len(sys.argv):
        if cmd:
            if sys.argv[i].lower() == "-l":
                __log_progress__ = True
            elif sys.argv[i].lower() == "-h":
                PrintHelp()
            elif sys.argv[i].lower() == "-s":
                cmd = False
            elif sys.argv[i].lower() == "-f":
                cmd = False
            elif sys.argv[i].lower() == "-d":
                cmd = False
            else:
                writeLog("Invalid option: %s" % sys.argv[i])
        else:
            if sys.argv[i-1].lower() == "-s":
                SourceFolder = sys.argv[i]
                __manual_source__ = False
                cmd = True
            elif sys.argv[i-1].lower() == "-f":
                Files = sys.argv[i].split('|')
                __manual_files__ = False
                cmd = True
            elif sys.argv[i-1].lower() == "-d":
                DestinationFolder = sys.argv[i]
                __manual_destination__ = False
                cmd = True
            else:
                writeLog("Error in options: %s" % sys.argv[i])
        i += 1

Size = 0
if __manual_source__:
    SourceFolder = GUI_SelectSourceFolder(__src_folder__)
if not SourceFolder:
    notifyOSD(__addonname__,__LS__(50009),__IconError__);
    writeLog("No Source Folder Selected, quit ...", xbmc.LOGERROR)
else:
    fi = FileInfo()   
    if __entire_folder__:
        Size = fi.GetFolderSize(SourceFolder)
        Files = []
    else:
        if __manual_files__:
            Files = fi.BuildFilesList(SourceFolder)
        if Files == []:
            notifyOSD(__addonname__,__LS__(50010),__IconError__);
            writeLog("No Video Files to Copy, quit ...", xbmc.LOGERROR)
        else:
            Size = fi.GetFilesSize(SourceFolder,Files)

if Size > 0: 
    if __manual_destination__:
        DestinationFolder=GUI_LookupDestination() 
    if not DestinationFolder:
        notifyOSD(__addonname__,__LS__(50011),__IconError__);
        writeLog("No Destination Folder Selected, quit ...", xbmc.LOGERROR)  
        Size = 0

if Size > 0:
    CopyDestination = fi.GetDestination(DestinationFolder,SourceFolder) 
    writeDebug("Source Folder: %s" % (SourceFolder))
    writeDebug("FilesSize: %d" % (Size))
    writeDebug("Copy Destination: %s" % (CopyDestination))

    #CopyDestination = "/mnt/htpc_disk/test/desttest" 

    if fi.CheckDestination(CopyDestination) and not __guitest__:
        # Create progress bar
        cpb = CopyProgressBar(fi.GetFileName(SourceFolder,False),__log_progress__)       
        pbStatus = cpb.Create(Size)

        # Start copy process
        if (pbStatus == PB_BUSY):
            cf = CopyFiles()
            cf.StartCopy(SourceFolder, CopyDestination, Files)

            while cf.BusyCopy() and (pbStatus == PB_BUSY) and not xbmc.abortRequested:
                pbStatus = cpb.UpdateAndWait(fi.GetFolderSize(CopyDestination))

            if cf.BusyCopy():
                writeLog("Killing copy process...", xbmc.LOGERROR)
                cf.KillCopy(True)
            del cf

        cpb.Close()
        del cpb

        if pbStatus == PB_CANCELED:
            notifyOSD(__addonname__,__LS__(50012),__IconError__);
            writeLog("Copy Process Canceled by User ...", xbmc.LOGERROR)  
        elif pbStatus == PB_TIMEOUT:
            notifyOSD(__addonname__,__LS__(50013),__IconError__);
            writeLog("Copy Process Canceled by Timeout ...", xbmc.LOGERROR) 

    del fi

writeLog("MovieCopy Ready ...")

