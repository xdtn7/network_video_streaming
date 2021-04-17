from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT
    
    SETUP = 0
    PLAY = 1
    PAUSE = 2 
    FORWARD = 3
    BACKWARD = 4
    DESCRIBE = 5
    SWITCH = 6
    TEARDOWN = 7
    STOP = 8
    REC = 9
    PLAYREC = 10

    recflag = 0
    
    lossCounter = 0
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        
        # Count Down Timer
        self.remainingTime = StringVar()
        self.remainingTime.set('00')
        
        # SWITCH GUI SUPPORT
        self.filenames = []
        self.fileNameVar = StringVar(master)
        self.fileNameVar.set('video.mjpeg')
        self.ChangedFileName = filename

        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.prevFrameTime = 0
        self.lastFrameTime = 0
        self.recFrameNbr = -1
        self.endframeNbr = 0
        #EXTEND 2
        self.setupMovie()

        
    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
    def createWidgets(self):
        """Build GUI."""
        # Create a label to display
        self.background = ImageTk.PhotoImage(Image.open('background.jpg'))
        self.videoFrame = Frame(self.master)
        self.statsLabel = Label(self.master, text = "Statistics Information", font = 'Helvetica 10 bold', width = 30)
        self.statsLabel.pack(side=RIGHT)
        self.videoFrame.pack()
        self.buttonFrame = Frame(self.master)
        self.buttonFrame.pack()

        # Create Play Pause button		
        self.start = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.start["text"] = "\u23EF"
        self.start["command"] = self.playpauseMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        # Create Fordward button
        self.forward = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.forward["text"] = "\u23E9"
        self.forward["command"] = self.forwardMovie
        self.forward.grid(row=1, column=2, padx=2, pady=2)

        # Create Backward button
        self.backward = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.backward["text"] = "\u23EA"
        self.backward["command"] = self.backwardMovie
        self.backward.grid(row=1, column=0, padx=2, pady=2)

        # Create Stop button
        self.teardown = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.teardown["text"] = "\u23F9"
        self.teardown["command"] =  self.stopMovie
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create Describe button
        self.describe = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.describe["text"] = "\u2139"
        self.describe["command"] =  self.describeMovie
        self.describe.grid(row=2, column=0, padx=2, pady=2)

        # Create Switchbutton
        self.switch = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.switch["text"] = "\u21CC"
        self.switch["command"] = self.switchMovie
        self.switch.grid(row=3, column=0, padx=2, pady=2)

        # Create a Menu Option
        self.dropbar = OptionMenu(self.buttonFrame, self.fileNameVar, ['video.mjpeg'])
        self.dropbar.grid(row=3, column=1, padx=2, pady=2)
        self.dropbar.config(width=15, padx=3, pady=3)

        # Create a place to display remaining time
        self.timer = Entry(self.buttonFrame, width=20, justify='center', textvariable=self.remainingTime)
        self.timer.grid(row=2, column=2, padx=3, pady=3)
        
        # Create REC button
        self.rec = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.rec["text"] = "\u23FA"
        self.rec["command"] = self.recMovie
        self.rec.grid(row=3, column=2, padx=2, pady=2)

        # Create Play REC button
        self.playrec = Button(self.buttonFrame, width=10, padx=3, pady=3, font = 'Helvetica 12 bold')
        self.playrec["text"] = "\u23CF"
        self.playrec["command"] = self.playrecMovie
        self.playrec.grid(row=3, column=3, padx=2, pady=2)
        
        self.videoLabel = Label(self.videoFrame, image=self.background)
        self.videoLabel.pack()

    
    def setupMovie(self):
        """Setup button handler."""
        print("Setup Movie.")
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def playpauseMovie(self):
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            print ("Playing Movie.")
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

        elif self.state == self.PLAYING:
            print ("Pause Movie.")
            self.sendRtspRequest(self.PAUSE)

    def stopMovie(self):
        """Stop button handler"""
        if self.state == self.PLAYING or self.state == self.READY:
            self.sendRtspRequest(self.STOP)
        
    def setplayMovie(self):
        """Set up and play movie"""
        self.playMovie()

    def exitClient(self):
        """Teardown button handler."""
        if self.state == self.INIT:	
            messagebox.showwarning('Warning', 'No video streaming to teardown')
            sys.exit(0)
        elif self.state == self.PLAYING or self.state == self.READY:
            # Close the gui window
            self.master.destroy() 

            # Delete the cache image from video
            cacheFile = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
            if os.path.isfile(cacheFile):
                os.remove(cacheFile) 

            self.sendRtspRequest(self.TEARDOWN)
            sys.exit(0)

    def pauseMovie(self):
        """Pause button handler."""
        print ("Pause Movie.")
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def forwardMovie(self):
        """Forward button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.FORWARD)

    def backwardMovie(self):
        """Backward button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.BACKWARD)
    
    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            print ("Playing Movie.")
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

        elif self.state == self.PLAYING:
            messagebox.showwarning('Warning', 'The video streaming is running...')

    def describeMovie(self):
        """Describe button handler."""
        print ("Describe Movie.")
        if not self.state == self.INIT:
            self.sendRtspRequest(self.DESCRIBE)
        else:
            messagebox.showwarning('Warning','Unable to retrieve information about movie.')
    
    def switchMovie(self):
        """Backward button handler."""
        self.fileName = self.ChangedFileName
        self.sendRtspRequest(self.SWITCH)

    def updateCountDownTimer(self):
        remainingTime = (self.noFrames - self.frameNbr) / self.fps
        self.remainingTime.set("Remaining time: " + str(remainingTime))
        self.buttonFrame.update()

    def recMovie(self):
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.REC)

    def playrecMovie(self):
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PLAYREC)

    def listenRtp(self):		
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()
                    try:
                        if self.frameNbr + 1 != currFrameNbr:
                            self.lossCounter += 1
                            print ('!'*30 + "\nPACKET LOSS: No." + str(currFrameNbr) + "\n" + '!'*30)
                        
                    except:
                        print ("seqNum() error")

                    if int(self.frameNbr) % int(self.fps) == 0 or self.frameNbr == self.noFrames:
                            self.updateCountDownTimer()

                    #EXTEND 1: Calculate the statistics
                    current = time.time()
                    duration = current - self.prevFrameTime
                    self.prevFrameTime = current
                    speed = len(rtpPacket.getPayload()) / duration
                    fps = 1 / duration
                    lossRate = float(self.lossCounter/self.frameNbr) * 100 if self.frameNbr != 0 else 0

                    # Display info to the label
                    self.displayText = StringVar()

                    statsInfo = self.displayText.get()
                    statsInfo += 'RTP current packet number: ' + str(currFrameNbr) + '\n'
                    statsInfo += 'RTP packet loss: ' + str(self.lossCounter) + ' packet(s)\n'
                    statsInfo += 'RTP packet loss rate: {:.2f} %\n'.format(lossRate)
                    statsInfo += 'Frames per second: {:.2f} FPS\n'.format(fps)
                    statsInfo += 'Frame duration: {:.0f} ms\n'.format(duration * 1000)
                    statsInfo += 'Video data rate: {:.2f}'.format(speed/1e+6) + ' Mbps\n'
                    statsInfo += '-' * 40 + '\n'
                    self.displayText.set(statsInfo)

                    self.statsLabel.configure(textvariable = self.displayText, font = 'Helvetica 10 bold', justify=LEFT)

                    # Update the current frame to the latest frame
                    if currFrameNbr > self.frameNbr: 
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

            except:
                # Stop listening upon requesting PAUSE or TEARDOWN or STOP
                print( "Didn`t receive data!")
                if self.playEvent.isSet():
                    break

                if self.frameNbr >= self.noFrames - 1: 
                    self.stopMovie()

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break
                    
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        try:
            file = open(cachename, "wb")
        except:
            print ("file open error")
        try:
            file.write(data)
        except:
            print ("file write error")
        file.close()
        return cachename
    
    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile)) 
        except:
            print ("photo error")

        self.videoLabel.configure(image = photo, width = 600, height = 400)
        self.videoLabel.image = photo
        
    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print ("Server Connection succeeded")
        except:
            messagebox.showwarning('Connection Failed', 'Connection to {} failed.'.format(self.serverAddr))
    
    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""	
        #-------------
        # TO COMPLETE
        #-------------
        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # RTSP request and send to the server.
            request = "SETUP " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Transport: RTP/UDP; client_port= " + str(self.rtpPort)
            
            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # RTSP request and send to the server.
            request = "PLAY " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)
            
            self.rtspSocket.send(request.encode())	
            print(request)		
            # Keep track of the sent request.
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # RTSP request and send to the server.
            request = "PAUSE " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)
            
            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.PAUSE

        # Stop request
        elif requestCode == self.STOP and (self.state == self.PLAYING or self.READY):
            self.rtspSeq = self.rtspSeq + 1
            request = "STOP " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.STOP

        # Forward request
        elif requestCode == self.FORWARD:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "FORWARD " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            self.rtspSocket.send(request.encode())
            print(request)        
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.FORWARD
            if self.frameNbr < self.noFrames:
                if self.noFrames - self.frameNbr >= self.fps:
                    self.frameNbr += self.fps
                else:
                    self.frameNbr = self.noFrames - 1

        # Backward request
        elif requestCode == self.BACKWARD:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "BACKWARD " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.rtspSocket.send(request.encode())
            print(request)
            self.requestSent = self.BACKWARD
            if self.frameNbr > 0:
                self.frameNbr -= self.fps

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1
            # RTSP request and send to the server.
            request = "TEARDOWN " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)
            
            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.TEARDOWN

        # Describe request
        elif requestCode == self.DESCRIBE and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # RTSP request and send to the server.
            request = "DESCRIBE " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE

        # Switch request
        elif requestCode == self.SWITCH:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # RTSP request and send to the server.
            request = "SWITCH " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            self.rtspSocket.send(request.encode())
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.SWITCH
            self.frameNbr = 0

        # REC request
        elif requestCode == self.REC:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "REC " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.rtspSocket.send(request.encode())
            print(request)
            self.requestSent = self.REC
            if self.frameNbr > 0:
                self.recFrameNbr = self.frameNbr
                self.recflag = 1
                
        # Play REC request
        elif requestCode == self.PLAYREC:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PLAYREC " + str(self.fileName) + " RTSP/1.0\n" + \
                      "CSeq: " + str(self.rtspSeq) + "\n" + \
                      "Session: " + str(self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.rtspSocket.send(request.encode())
            print(request)
            self.requestSent = self.PLAYREC
            if self.recflag != 0:
                self.frameNbr = self.recFrameNbr 
                print("recFrameNbr: ")
                print(self.frameNbr)

        else:
            return
    
    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break
    
    def fileNameCallBack(self, *args):
        self.ChangedFileName = str(self.fileNameVar.get())

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Parse Total time, FPS, frames
        self.totalTime = float(lines[3].split(' ')[2])
        self.fps = int(lines[4].split(' ')[2])
        self.noFrames = int(lines[5].split(' ')[2])

        # Parse file names
        if len(lines[6].split(' ')) - 1 > len(self.filenames):
            for i in lines[6].split(' '):
                if i == 'Media:':
                    continue
                self.filenames.append(i)
            self.updateOptionMenu()
        # Sort out duplicates
        self.filenames = sorted(set(self.filenames))

    # Create a slot to display time
        if self.requestSent == self.SETUP or self.requestSent == self.SWITCH:
            self.total = Button(self.buttonFrame, width=17, padx=3, pady=3)
            self.total["text"] = "Total time: " + str(self.totalTime) + "s"
            self.total.grid(row=2, column=1, padx=3, pady=3)

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same and the code is 200
            if self.sessionId == session and int(lines[0].split(' ')[1]) == 200:
                if self.requestSent == self.SETUP:
                    self.state = self.READY
                    self.openRtpPort()

                    # Get total time of video to remaining time
                    self.remainingTime.set("Remaining time: " + str(self.totalTime))
                    self.buttonFrame.update()

                elif self.requestSent == self.PLAY:
                    self.state = self.PLAYING

                elif self.requestSent == self.DESCRIBE:
                    lines = data.split('\n')[3:]
                    info = '\n'.join(lines)
                    messagebox.showinfo('VIDEO SOURCE INFORMATION', info)
                    
                elif self.requestSent == self.PAUSE:
                    self.state = self.READY
                    # The play thread exits. A new thread is created on resume.
                    self.playEvent.set()
                
                elif self.requestSent == self.STOP:
                        self.frameNbr = 0
                        self.state = self.READY
                        self.playEvent.set()

                        # Reset the remaining time back to the total time after pressing STOP.
                        self.remainingTime.set("Remaining time: " + str(self.totalTime))
                        self.buttonFrame.update()

                elif self.requestSent == self.TEARDOWN:
                    # Set the teardownAcked to close the socket.
                    self.teardownAcked = 1

                elif self.requestSent == self.SWITCH:
                        self.state = self.READY

                        # Get total time of video to remaining time after SWITCHING video
                        self.remainingTime.set("Remaining time: " + str(self.totalTime))
                        self.buttonFrame.update()
    
    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        #-------------
        # TO COMPLETE
        #-------------
        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)
        
        # Create a new datagram socket to receive RTP packets from the server
        try:
            """ setup RTP/UDP socket """          
            self.state = self.READY
            self.rtpSocket.bind(('',self.rtpPort)) 
            print ("Bind RtpPort Success")
        except:
            messagebox.showwarning('Connection Failed', 'Connection to rtpServer failed...')
        
# Utils Functions
    def handler(self):
        """Handler on explicitly closing the GUI window."""
        previousState = self.state
        self.pauseMovie()
        if messagebox.askokcancel("Exit?", "Are you sure you want to exit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            if previousState == self.PLAYING:
                self.playMovie()

    """
    def showDescribe(self, data):
        self.displayCon = StringVar() 
        description_info = self.displayCon.get()
        description_info += 'VIDEO SOURCE INFORMATION: \n'
        description_info += data + '\n'
        description_info += '-' * 40 + '\n'
        self.displayCon.set(description_info)
        self.statsLabel.configure(textvariable = self.displayCon, font = 'Helvetica 10 bold', justify=LEFT)  
    """

    # Create a drop bar
    def updateOptionMenu(self):
        OPTIONS = self.filenames
        if len(self.filenames) == 0:
            OPTIONS = ['']
        self.dropbar = OptionMenu(self.buttonFrame, self.fileNameVar, *OPTIONS)
        self.dropbar.grid(row=3, column=1, padx=2, pady=2)
        self.dropbar.config(width=15, padx=3, pady=3)
        self.fileNameVar.trace("w", self.fileNameCallBack)