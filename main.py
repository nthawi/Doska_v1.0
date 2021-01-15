# Оставь надежду всяк сюда входящий
# Desine sperare qui hic intras
# Lasciate ogni speranza, voi ch’entrate
# Abandon all hope, ye who enter here
# Lasst alle Hoffnung fahren, die ihr hier eintretet

# print("Hello, World!")

from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
from test import Ui_Dialog
from PyQt5.QtCore import QThread, pyqtSignal, QRunnable, Qt, QThreadPool
import string, random, os, sys, _thread, httplib2, time, os.path, shutil
import urllib.request
import requests
import threading
import telebot
import exrex
import math

from telebot import types
from PIL import Image
from resizeimage import resizeimage

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# INIT
app = QtWidgets.QApplication(sys.argv)
Dialog = QtWidgets.QDialog()
ui = Ui_Dialog()
ui.setupUi(Dialog)
Dialog.show()
Dialog.setFixedSize(390, 500)

global traceStop
global fileContent
global scannedUrls
global activeThreads
global activeUrls
global LOGbusy
global currentPosition
global screenedUrls
global chromeThreads
global ignoreArr
global stopBar
global botActive
global username
global token
global bot
global alphabet
global pingDelay
global fullUrls
global tablesCount
global stopCreatePattern

activeUrls = []
fileContent = []
scannedUrls = 0
traceStop = False
activeThreads = 0
currentPosition = 0
screenedUrls = 0
chromeThreads = 1
stopBar = False
botActive = False
username = ""
token = ""
ignoreArr = []
alphabet = ""
pingDelay = 0
fullUrls = []
tablesCount = 0
stopCreatePattern = False
LOGbusy = False

threadLocal = threading.local()

# TELEGRAM
if os.path.isfile("cache/botsettings.txt") == True:

    file = open("cache/botsettings.txt", "r")   

    for line in file: 
        if line[0:6] == "TOKEN:":
            token = line[6:].rstrip('\n').rstrip('\r')
        if line[0:9] == "USERNAME:":
            username = line[9:].rstrip('\n').rstrip('\r')    

    file.close()

bot = telebot.TeleBot(token)

# LOGIC
# create txt file with all posible combinations
def startcreatePattern(message, sendMessage = False):

    global activeThreads

    if activeThreads > 0:

        if sendMessage == True:
            bot.send_message(message.chat.id, "Подожди окончания предыдущей задачи")

        return

    buttonState(False)
    clearTmpFolder()

    n = threading.Thread(target = createPattern, name = "CreatePattern", args=[message, sendMessage])
    n.start()

def createPattern(message, sendMessage = False):

    global alphabet
    global tablesCount
    global fullUrls
    global currentCombinations
    global activeThreads

    activeThreads += 1

    ui.stopCreate.setEnabled(True)

    pattern = str(ui.Pattern.toPlainText())
    pattern = pattern.strip()

    fullPattern = pattern

    partArray = []
    tpartArray = []

    pattern = pattern.replace(".", "\.")
    pattern = pattern.replace("_", "\_")

    domain = str(ui.Pattern_domain.toPlainText())

    maxPatternLen = 3

    if int(countSubstrings(pattern, "[a-]")) > maxPatternLen:

        patternCount = math.ceil(int(countSubstrings(pattern, "[a-]")) / maxPatternLen)

        count = 0

        while count < patternCount:     

            count += 1

            tpattern = pattern.replace("[a-]", "([" + alphabet + "])", maxPatternLen)

            pattern = tpattern[max(map(tpattern.rfind, ")")) + 1:]

            tpattern = tpattern[:max(map(tpattern.rfind, ")")) + 1]

            partArray.append(list(exrex.generate(tpattern)))

        count = 0

        urlMaxCombinations = len(alphabet) ** int(countSubstrings(fullPattern, "[a-]"))

        insertToLog("Starting generate " + str(urlMaxCombinations) + " links...")

        if sendMessage == True:
            bot.send_message(message.chat.id, "Начинаю генерацию " + str(urlMaxCombinations) + " ссылок...")

        currentCombinations = 0

        for partUrl in partArray[count]: # first part

            generatePattern(count + 1, partUrl, len(partArray) - 1, partArray, domain, urlMaxCombinations)

    else:

        pattern = pattern.replace("[a-]", "([" + alphabet + "])")

        fullUrls = list(exrex.generate(pattern))

    file = open("cache/tables/table" + str(tablesCount) + ".txt", "w+")

    tablesCount += 1

    for line in fullUrls:
            
        file.write(line + domain + "\n")  

    file.close()

    if sendMessage == True:
        bot.send_message(message.chat.id, "Список был сгенерирован", reply_markup = botButtons())   

    stopCreatePattern = False
    tablesCount = 0
    currentCombinations = 0

    dfile = open("cache/success.txt","w+")
    dfile.close()

    buttonState(True)
    insertToLog("Success generated")
    loadingBar(100)

    ui.stopCreate.setEnabled(False)

    activeThreads -= 1

def generatePattern(count, partUrl, maxLen, partArray, domain, urlMaxCombinations):

    global fullUrls
    global tablesCount
    global currentCombinations
    global stopCreatePattern

    if count > maxLen:
        return

    for secondPartUrl in partArray[count]: # second parts

        if stopCreatePattern == True:
            break

        currentCombinations += 1

        url = partUrl + secondPartUrl + domain

        if count == maxLen:

            fullUrls.append(url)

            if len(fullUrls) >= 500000:

                currentPercent = round(currentCombinations / urlMaxCombinations * 100)

                loadingBar(round(currentPercent))

                file = open("cache/tables/table" + str(tablesCount) + ".txt", "w+")

                tablesCount += 1

                for line in fullUrls:
                    file.write(line + "\n")                

                file.close()

                fullUrls = []    

        generatePattern(count + 1, url, maxLen, partArray, domain, urlMaxCombinations) 

def stopCreate():

    global stopCreatePattern

    stopCreatePattern = True
    insertToLog("Generation stopped")

    ui.stopCreate.setEnabled(False)

def loadingBar(currentPercent):

    symbols = currentPercent // 5

    count = 0

    text = ""

    while count < symbols:

        text = text + "|"

        count += 1

    ui.countPattern.setText(text + " " + str(currentPercent) + "%")    

# scan
def startBreadwinners(message, sendMessage = False):
    
    ui.stop.setEnabled(True)

    t = threading.Thread(target = startBreadwinner, name = "startBreadwinners", args = [message, sendMessage])
    t.start() 

def startBreadwinner(message, sendMessage):

    global fileContent
    global scannedUrls
    global traceStop

    successContent = []

    filehtml = open("cache/successHtml.html","w+").close()

    folder = 'cache/tables/'

    maxFiles = 0

    for subdir, dirs, files in os.walk(folder):
        for item in os.listdir(folder):
            if not item.startswith('.') and os.path.isfile(os.path.join(folder, item)):
                maxFiles += 1

    counter = 0
    latestFile = ""
    latestLine = 0

    if os.path.isfile("cache/endpoint.txt") == True:
        
        fileEndPoint = open("cache/endpoint.txt", "r") 

        for line in fileEndPoint: 
            if line[0:5] == "FILE:":
                latestFile = line[5:].rstrip('\n').rstrip('\r')
            if line[0:5] == "LINE:":
                latestLine = int(line[5:].rstrip('\n').rstrip('\r'))         

    firstFile = True

    for subdir, dirs, files in os.walk(folder):

        for item in sorted(os.listdir(folder), key=len):

            sorted(folder, key = last_4chars)

            if not item.startswith('.') and os.path.isfile(os.path.join(folder, item)):

                if traceStop:
                    break

                counter += 1

                if latestFile != "" and firstFile == True:
                    if item != latestFile:
                        continue

                file = open(folder + "/" + item, "r")

                if file.mode == 'r':
                    insertToLog("Open file (" + str(counter) + " / " + str(maxFiles) + ")...") 

                    if sendMessage == True:
                        bot.send_message(message.chat.id, "Открываю файл (" + str(counter) + " / " + str(maxFiles) + ")...") 

                continueCount = 0

                for line in file:
                    continueCount += 1

                    if latestLine > 0 and firstFile:
                        if continueCount < latestLine:
                            continue

                    content = line.rstrip('\n').rstrip('\r')

                    if content == "":
                        continue

                    fileContent.append(content)  

                if not firstFile:
                    latestLine = 0

                file.close()

                ui.countScan.setText(str(len(fileContent)))

                t = threading.Thread(target = threadBarScan, name = "threadBar")
                t.start()

                t = threading.Thread(target = breadwinner, name = "Breadwinner", args = [message, item, latestLine, sendMessage])
                t.run()

                firstFile = False

    sortFile("success")

    nullState()

    buttonState(True)

    if ui.autoStart.checkState() == 2:
        startScreenshot()  

    ui.stop.setEnabled(False)

    if sendMessage == True:
        bot.send_message(message.chat.id, "Сканирование завершено. Прогресс сохранен", reply_markup=botButtons())

def last_4chars(x):
    return(x[-2:])

def breadwinner(message, filename, latestLine, sendMessage = False):

    global traceStop
    global activeThreads
    global fileContent
    global activeUrls
    global currentPosition
    global stopBar

    activeUrls = []
    traceStop == False

    buttonState(False)

    count = int(ui.Threads.value())
    counter = 0
    pack = ui.Packs.value()

    while traceStop == False:

        if activeThreads >= count:

            continue

        if counter % 100 == 0 and counter > 0:

            #print("> pseudo " + str(counter * pack))

            if sendMessage == True:
                bot.send_message(message.chat.id, "Скормлено сканеру " + str(counter * pack) + " ссылок, осталось " + str(len(fileContent)) + ". Прогресс сохранен")

            fileS = open("cache/success.txt","a")

            a = activeUrls.copy()

            for line in a:

                fileS.write(line + "\n") 

            fileS.close()

            filehtml = open("cache/successHtml.html","a")

            for line in a:

                filehtml.write("<a href='" + line + "'> " + line + "</a><br>\n") 

            filehtml.close()

            saveStatus(filename, currentPosition + latestLine)

            activeUrls = []

        food = fileContent[:pack]

        del fileContent[:pack]

        if not food:
            break

        activeThreads += 1
        counter += 1

        t = threading.Thread(target = eat, args = [food])
        t.start()

        time.sleep(0.1)

    while activeThreads > 0:
        time.sleep(0.02)        

    stopBar = True

    insertToLog("All threads were stopped") 

    saveStatus(filename, currentPosition + latestLine)

    file = open("cache/success.txt","a")

    for line in activeUrls:
        file.write(line + "\n") 

    file.close()

    filehtml = open("cache/successHtml.html","a")

    for line in activeUrls:

        filehtml.write("<a href='" + line + "'> " + line + "</a><br>\n") 

    filehtml.close()  

def eat(food):

    global activeThreads
    global activeUrls
    global ignoreArr
    global currentPosition
    global pingDelay

    for url in food:

        includeIgnore = False

        currentPosition += 1

        url = "http://" + str(url)

        try:

            http = httplib2.Http(timeout=1)
            resp = http.request(url)[1]
            html = resp.decode()

            for ignorePhrase in ignoreArr:
                
                if best_find(html, ignorePhrase) == True:
                    
                    includeIgnore = True

        except TimeoutException:
            continue
        except:
            continue
        
        time.sleep(float(pingDelay)) 

        if includeIgnore == True:
            continue

        activeUrls.append(url)

    activeThreads -= 1

# screenshot
def startLooker(message, sendMessage = False):

    global fileContent
    global scannedUrls
    global currentPosition

    ui.stopScreenshot.setEnabled(True)

    successContent = []
    currentPosition = 0

    if os.path.isfile("cache/success.txt") == False:

        if sendMessage == True:
            bot.send_message(message.chat.id, "Файл не найден", reply_markup=botButtons())

        insertToLog("File not found", "#c94c4c")
        return

    file = open("cache/success.txt", "r")

    if file.mode == 'r':

        insertToLog("File opened...")     

    for line in file:

        fileContent.append(line.rstrip('\n').rstrip('\r'))  

    file.close()

    ui.countUrl.setText(str(len(fileContent)))

    t = threading.Thread(target = looker, name = "Looker", args = [message, sendMessage])
    t.start()

    t = threading.Thread(target = threadBarUrl, name = "threadBar")
    t.start()

    #t = threading.Thread(target = threadCount, name = "threadCount")
    #t.start()

def looker(message, sendMessage = False):

    global traceStop
    global activeThreads
    global fileContent
    global activeUrls
    global currentPosition
    global stopBar

    activeUrls = []
    traceStop == False
    fileContentArch = fileContent.copy()
    stopped = False

    buttonState(False)

    threads = ui.screenThreads.value()
    counter = 0
    pack = ui.Packs.value()

    while traceStop == False:

        if activeThreads >= threads:
            continue

        food = fileContent[:pack]

        del fileContent[:pack]

        if not food:
            break

        activeThreads += 1
        counter += 1

        t = threading.Thread(target = lookAtFood, args = [food])
        t.start()

        time.sleep(0.1)

    if traceStop == True:
        stopped = True

    while activeThreads > 0:
        time.sleep(0.02)        

    stopBar = True

    insertToLog("All threads were stopped") 

    if sendMessage == True:
        bot.send_message(message.chat.id, "Процесс завершен. Прогресс сохранен", reply_markup = botButtons())

    file = open("cache/success.txt","w+")

    # if you stopped forcibly cutting before the start of the maximum first thread
    if stopped == True:

        backuplen = currentPosition - 1

        fileContentArch = fileContentArch[backuplen:]

        for line in fileContentArch:
            file.write(line + "\n")

    file.close()

    nullState()

    buttonState(True)

    ui.stopScreenshot.setEnabled(False)

def get_driver():
    browser = getattr(threadLocal, 'browser', None)
    if browser is None:
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--lang=en")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36")
        #chrome_options.binary_location = "/usr/bin/google-chrome"
        browser = webdriver.Chrome(executable_path=r'chromedriver', options=chrome_options)
        setattr(threadLocal, 'browser', browser)
    return browser

def lookAtFood(food):

    global activeThreads
    global activeUrls
    global currentPosition

    counter = 0

    # PHANTOMJS
    #cap = webdriver.DesiredCapabilities.PHANTOMJS
    #cap["phantomjs.page.settings.javascriptEnabled"] = False
    #driver = webdriver.PhantomJS(desired_capabilities=cap)

    #headers = { 'Accept':'*/*',
    #    'Accept-Encoding':'gzip, deflate, sdch',
    #    'Accept-Language':'en-US,en;q=0.8',
    #    'Cache-Control':'max-age=0',
    #    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
    #}

    #for key, value in enumerate(headers):
    #    capability_key = 'phantomjs.page.customHeaders.{}'.format(key)
    #    webdriver.DesiredCapabilities.PHANTOMJS[capability_key] = value

    #driver = webdriver.PhantomJS()

    #driver.implicitly_wait(3)
    #driver.set_page_load_timeout(10)
    #driver.set_window_position(0, 0)
    #driver.set_window_size(800,600)

    # CHROME
    chrome_options = Options()
    chrome_options.headless = True
    chrome_options.add_experimental_option( "prefs",{'profile.managed_default_content_settings.javascript': 2})
    #chrome_options.add_argument('log-level=3')
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox') 
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(10)

    #driver = get_driver()
    #driver.set_page_load_timeout(10)

    for url in food:
        currentPosition += 1

        if traceStop == True:
            break

        try:
            driver.get(url) 

            url = url.replace('http://', '')

            path = 'scr\\' + url + '.png'

            driver.save_screenshot(path)       

            if not os.path.isfile(path):
                continue    

            photo = Image.open(path, 'r')

            if photo.height > 900:
                photo = resizeimage.resize_crop(photo, [photo.width, 900])
                photo.save(path, photo.format)

            photo.close()

        except TimeoutException:
            #insertToLog(url + " TimeoutException", "#c94c4c")
            continue

        except WebDriverException:
            #insertToLog(url + " WebDriverException", "#c94c4c")
            continue

    activeThreads -= 1

    driver.close()
    driver.quit()

# other 
def countSubstrings(fullString, substring):
    
    count = 0
    i = -1

    while True:
        i = fullString.find(substring, i + 1)

        if i == -1:
            return count

        count += 1

def stopThreads(message, sendMessage = False):

    global traceStop

    ui.stop.setEnabled(False)
    ui.stopScreenshot.setEnabled(False)

    traceStop = True

    insertToLog("Stopped...", "#c94c4c")

def insertToLog(text, color="black"):  

    ui.LOG.moveCursor(QtGui.QTextCursor.End, QtGui.QTextCursor.MoveAnchor)
    ui.LOG.insertPlainText("[" + time.strftime("%H:%M:%S") + "] " + text + "\n")
    time.sleep(0.02)
    ui.LOG.moveCursor(QtGui.QTextCursor.End, QtGui.QTextCursor.MoveAnchor)


def threadBarScan():

    global traceStop
    global currentPosition
    global stopBar
    global fileContent
    global activeThreads

    while stopBar == False:

        ui.currentScan.setText(str(currentPosition))    

        widgetText = ""

        currentPercent = round(activeThreads / ui.Threads.value() * 100)

        x = 0

        while x <= currentPercent:
            x += 1
            widgetText = widgetText + "|"

        ui.threadWidget.setText(widgetText)
        ui.threadCount.setText(str(activeThreads))    
        
        time.sleep(0.1)

    stopBar = False

    ui.threadWidget.setText("")
    ui.threadCount.setText("0")
    ui.currentScan.setText("0")
    ui.countScan.setText("0")

def threadBarUrl():

    global currentPosition
    global fileContent
    global stopBar
    global activeThreads    

    while stopBar == False:

        widgetText = ""

        x = 0

        currentPercent = round(activeThreads / ui.screenThreads.value() * 100)

        while x <= currentPercent:

            x += 1

            widgetText = widgetText + "|"

        ui.threadWidget.setText(widgetText)
        ui.currentUrl.setText(str(currentPosition))    
        ui.threadCount.setText(str(activeThreads)) 

        time.sleep(0.1)

    stopBar = False

    ui.threadWidget.setText("")
    ui.threadCount.setText("0")
    ui.currentUrl.setText("0")
    ui.countUrl.setText("0")

def settingsOpenClose():

    if ui.openSettings.text() == "<":
        Dialog.setFixedSize(390, 500)
        ui.openSettings.setText(">")
    else:
        Dialog.setFixedSize(768, 500)
        ui.openSettings.setText("<")     

def best_find(string, text):

    if text in string:
        return True
    else:
        return False

def loadSettings():

    global ignoreArr
    global alphabet
    global pingDelay

    ignoreList = ""
    alphabetList = ""

    file = open("cache/ignore.txt", "r+", encoding='utf-8')    

    for line in file:

        ignoreArr.append(line.rstrip('\n').rstrip('\r')) 

        ignoreList = str(ignoreList) + "[" + str(line.rstrip('\n').rstrip('\r')) + "]"

    ui.IgnoreList.setPlainText(ignoreList)

    file.close()

    file = open("cache/alphabet.txt", "r+", encoding='utf-8')    

    for line in file:
        alphabet = alphabet + line.rstrip('\n').rstrip('\r')
        alphabetList = str(alphabetList) + "[" + str(line.rstrip('\n').rstrip('\r')) + "]"

    ui.Alphabet.setPlainText(alphabetList)

    file.close()

    packs = 0
    pingDelay = 0

    file = open("cache/settings.txt", "r+", encoding='utf-8')    

    for line in file: 
        if line[0:6] == "PACKS:":
            packs = line[6:].rstrip('\n').rstrip('\r')
        if line[0:10] == "PINGDELAY:":
            pingDelay = line[10:].rstrip('\n').rstrip('\r') 
        if line[0:12] == "SCANTHREADS:":
            scanThreads = line[12:].rstrip('\n').rstrip('\r') 
        if line[0:14] == "SCREENTHREADS:":
            screenThreads = line[14:].rstrip('\n').rstrip('\r')  

    ui.Packs.setValue(int(packs))
    ui.PingDelay.setValue(float(pingDelay))
    ui.Threads.setValue(int(scanThreads))
    ui.screenThreads.setValue(int(packs))

    file.close()

def sortFile(fileName):
        
    if fileName == False:
        fileName = "success"    

    content = []

    file = open("cache/" + str(fileName) + ".txt", "r+")

    for line in file:
        content.append(line.rstrip('\n').rstrip('\r'))

    file.close()

    open("cache/" + str(fileName) + ".txt", 'w').close() 

    content.sort()
    content = list(dict.fromkeys(content))

    file = open("cache/" + str(fileName) + ".txt", "a")

    for line in content:
        file.write(line + "\n") 

    file.close()   

def addMask():

    text = ui.Pattern.toPlainText()
    ui.Pattern.setPlainText(text + "[a-]")  

def nullState():

    global traceStop
    global fileContent
    global scannedUrls
    global activeThreads
    global activeUrls
    global currentPosition
    global screenedUrls

    activeUrls = []
    fileContent = []
    scannedUrls = 0
    traceStop = False
    activeThreads = 0
    currentPosition = 0
    screenedUrls = 0  

def saveIgnore():

    global ignoreArr

    ignoreArr = []
    ignoreList = ""

    open("cache/ignore.txt", 'w').close()

    file = open("cache/ignore.txt", "r+", encoding='utf-8')    

    ignoreList = str(ui.IgnoreList.toPlainText())
    ignoreList = ignoreList.strip()    
    ignoreList = ignoreList.split("]")

    del ignoreList[-1]

    for line in ignoreList:
        ignoreArr.append(line.replace("[", "")) 

    for line in ignoreArr:
        file.write(line + "\n")

    file.close() 

def saveAlphabet():

    global alphabet

    alphabet = []

    open("cache/alphabet.txt", 'w').close()
    
    file = open("cache/alphabet.txt", "w", encoding = 'utf-8')    

    Alphabet_ = str(ui.Alphabet.toPlainText())
    Alphabet_ = Alphabet_.strip()    
    Alphabet_ = Alphabet_.split("]")

    del Alphabet_[-1]

    for line in Alphabet_:
        alphabet.append(line.replace("[", "")) 

    for line in alphabet:
        file.write(line + "\n")

    file.close() 

def setPlaseholders():

    ui.Pattern.setPlainText(" ")
    ui.Pattern.clear()
    ui.Alphabet.setPlainText(" ")
    ui.Alphabet.clear()
    ui.Token.setPlainText(" ")
    ui.Token.clear()
    ui.Owner.setPlainText(" ")
    ui.Owner.clear()
    ui.Pattern_domain.setPlainText(" ")
    ui.Pattern_domain.clear()

def buttonState(state = True):
    
    ui.createPattern.setEnabled(state)
    ui.startScan.setEnabled(state)
    ui.startScreenshot.setEnabled(state)
    ui.startBot.setEnabled(state)
    ui.addMask.setEnabled(state)

def clearLog():
    
    ui.LOG.setPlainText("")

def createSettings():

    file = open("cache/settings.txt","w+")

    file.write("PACKS:" + str(ui.Packs.value()) + "\n")    
    file.write("PINGDELAY:" + str(round(ui.PingDelay.value(), 1)) + "\n")
    file.write("SCANTHREADS:" + str(ui.Threads.value()) + "\n")
    file.write("SCREENTHREADS:" + str(ui.screenThreads.value()) + "\n") 

    file.close() 

def saveStatus(filename, line):

    file = open("cache/endpoint.txt","w+")

    file.write("FILE:" + str(filename) + "\n")    
    file.write("LINE:" + str(line) + "\n") 

    file.close() 

def clearTmpFolder():

    folder = "scr"

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)

            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    folder = "cache/tables"

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)

            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    open("cache/endpoint.txt", 'w').close()

def clearScrFolder():

    folder = "scr"

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))   

# telegram bot
def activateBot():

    global botActive
    global username
    global token

    ui.Token.setPlainText(str(token))    
    ui.Owner.setPlainText(str(username))

    if token != "":
        
        botActive = True

        t = threading.Thread(target = telegramBot, name = "threadBot")
        t.start() 

def telegramBot():

    global token
    global bot

    while True:
        insertToLog("> bot was enabled")

        try:
            bot.infinity_polling(True)

        except Exception as e:
            logger.error(e)
            time.sleep(15)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):

    global username
    global activeThreads
    
    if message.from_user.username != username:

        bot.reply_to(message, "Ты не моя настоящая мать")
        return 

    if activeThreads > 0:

       bot.send_message(message.chat.id, "Занят, не мешай") 
       return

    bot.reply_to(message, "Привет, что делаем?", reply_markup = botButtons())

@bot.message_handler(func=lambda message: True)
def echo_all(message):

    global username
    global activeThreads
    global traceStop

    if message.from_user.username != username:

        bot.reply_to(message, "Ты не моя настоящая мать")
        return    

    if activeThreads > 0 and message.text != "Остановить" and message.text != "Остановить генерацию":

       bot.send_message(message.chat.id, "Занят, не мешай") 
       return

    if message.text == "Создать паттерн": 
        markup = types.ForceReply(selective = False)
        msg = bot.send_message(message.chat.id, "Введи маску типа [a-][a-][a-](.com):", reply_markup = markup)
        bot.register_next_step_handler(msg, setPatternFromBot)

    elif message.text == "Сканировать":
        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
        item1 = types.KeyboardButton("Остановить")
        markup.add(item1)
        bot.send_message(message.chat.id, "Сканирование запущено", reply_markup = markup) 
        startBreadwinners(message, True)        

    elif message.text == "Скриншотить":

        markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
        item1 = types.KeyboardButton("Остановить")
        markup.add(item1)
        bot.send_message(message.chat.id, "Скриншотер запущен", reply_markup = markup) 
        startLooker(message, True)         

    elif message.text == "Остановить":

        if traceStop:
            return    

        if activeThreads == 0:
            bot.send_message(message.chat.id, "Что делаем дальше?", reply_markup = botButtons())
            return    

        markup = types.ReplyKeyboardRemove(selective = False)

        bot.send_message(message.chat.id, "Останавливаю сканирование (Это займет некоторое время) ...")

        stopThreads(message, True)

    elif message.text == "Остановить генерацию":

        if activeThreads == 0:
            bot.send_message(message.chat.id, "Что делаем дальше?", reply_markup = botButtons())
            return  

        markup = types.ReplyKeyboardRemove(selective = False)

        bot.send_message(message.chat.id, "Останавливаю генерацию...")

        stopCreate()

    elif message.text == "Десятка скриншотов":
        uploadScreenshot(message)

    elif message.text == "🗑":
        clearScrFolder()
        bot.send_message(message.chat.id, "Папка со скриншотами очищена. Что делаем дальше?", reply_markup = botButtons())

    else:
        bot.send_message(message.chat.id, "Чо", reply_markup = markup)

def setPatternFromBot(message):

    if message.text == "/start":
        bot.send_message(message.chat.id, "Что делаем дальше?", reply_markup = botButtons())
        return

    pattern = message.text
    patternDomain = ""

    if max(map(message.text.rfind, "(")) > -1:
        pattern = message.text[:max(map(message.text.rfind, "("))] 
        patternDomain = message.text[max(map(message.text.rfind, "(")) + 1:max(map(message.text.rfind, ")"))]

    ui.Pattern.setPlainText(str(pattern)) 
    ui.Pattern_domain.setPlainText(str(patternDomain))

    markup = types.ReplyKeyboardMarkup(resize_keyboard = True)
    item1 = types.KeyboardButton("Остановить генерацию")
    markup.add(item1)

    bot.send_message(message.chat.id, "Генерирую ссылки по паттерну " + str(ui.Pattern.toPlainText()) + "" + str(ui.Pattern_domain.toPlainText()), reply_markup = markup) 
    time.sleep(0.5)
    startcreatePattern(message, True) 

def botButtons():

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Создать паттерн")
    item2 = types.KeyboardButton("Сканировать")
    item3 = types.KeyboardButton("Скриншотить")
    item4 = types.KeyboardButton("Десятка скриншотов")
    item5 = types.KeyboardButton("🗑")

    markup.add(item1, item2)
    markup.add(item3, item4, item5)

    return markup

def tryConnectBot():
    
    global botActive
    global username
    global token

    createBotSettings()

    if botActive == True:
        return

    token = ui.Token.toPlainText()
    username = ui.Owner.toPlainText()

    if token != "":
        activateBot()

def createBotSettings():

    file = open("cache/botsettings.txt","w+")

    file.write("TOKEN:" + str(ui.Token.toPlainText()) + "\n")    
    file.write("USERNAME:" + str(ui.Owner.toPlainText()) + "\n") 

    file.close() 

def uploadScreenshot(message):

    global activeThreads

    folder = "scr"

    counter = 0

    activeThreads += 1

    for filename in os.listdir(folder):
        counter += 1

        if counter > 10:
            break

        file_path = os.path.join(folder, filename)

        photo = open(file_path, 'rb')

        bot.send_photo(message.chat.id, photo, filename[:-4])

        photo.close()

        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)

            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

        time.sleep(1)   

    activeThreads -= 1

# button connect
ui.createPattern.clicked.connect(startcreatePattern)
ui.addMask.clicked.connect(addMask)
ui.startScan.clicked.connect(startBreadwinners)
ui.stop.clicked.connect(stopThreads)
ui.stopScreenshot.clicked.connect(stopThreads)
ui.startScreenshot.clicked.connect(startLooker)#startScreenshot)
ui.openSettings.clicked.connect(settingsOpenClose)
ui.clearLOG.clicked.connect(clearLog)
ui.saveIgnore.clicked.connect(saveIgnore)
ui.startBot.clicked.connect(tryConnectBot)
ui.saveBotSettings.clicked.connect(createBotSettings)
ui.saveAlphabet.clicked.connect(saveAlphabet)
ui.saveSettings.clicked.connect(createSettings)
ui.stopCreate.clicked.connect(stopCreate)
ui.clearScreenFolder.clicked.connect(clearScrFolder)

# afterload scripts
setPlaseholders()
loadSettings()
activateBot()

# exit
sys.exit(app.exec_())