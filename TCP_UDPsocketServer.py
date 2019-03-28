import socket
import select
from threading import Thread
from datetime import datetime
import os
import base64
import pickle
import time



class TCPSocketServerManager:

    def __init__(self,receiveBufferSize,sendBufferSize,port):

        self.closeSocket=False
        self.receiveBufferSize = receiveBufferSize
        self.sendBufferSize = sendBufferSize

        # create an INET, STREAMing socket
        self.serversocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)

        # bind the socket to a public host, and a well-known port
        self.serversocket.bind((socket.gethostbyname(socket.gethostname()),port))
        # maximun socket server connections
        self.serversocket.listen(20)
        print(" TCP socket listen at "+  socket.gethostbyname(socket.gethostname()) +" port "+ str(port))
        print("")
        self.handleClientConnections()

    def sendMesssage(self,socketConnection,message):

        socketConnection.send(message)

    def receiveMessage(self,socketConnection,split):

        data = ""
        if split == True:
            data = socketConnection.recv(self.receiveBufferSize).split(" ")
        else:
            data = socketConnection.recv(self.receiveBufferSize)
        print(data)
        return data

    def typeOfFile(self,isBinary):

        if isBinary == 1:
            return "wb"

        return "w"

    def seeFilesInFolder(self,client):

        try:

            folderFiles = os.listdir("files")
            filesAmount= len(folderFiles)
            windowSize=5

            print("archivos en carpeta.. ")
            print(folderFiles)

            self.sendMesssage(client,str(filesAmount)+" "+str(windowSize))

            data= self.receiveMessage(client,False)

            if data=="F":
                print("El cliente ha cancelado la operacion")
                return

            fileTransmitted=0

            while fileTransmitted < filesAmount:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([client], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data = self.receiveMessage(client, False)
                    data = int(data)
                    print("El cliente dice que ha recibido hasta el indice "+ str(data))
                    #seguir enviando nombres de archivos de la lista a partir de esta posicion

                    fileTransmitted=data

                self.sendMesssage(client,str(fileTransmitted)+" "+folderFiles[fileTransmitted])
                fileTransmitted+=1


            self.sendMesssage(client,"E")

        except IOError as e:
            self.sendMesssage(client,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            self.sendMesssage(client,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def sendFile(self, client,fileName):

        try:

            fileSize= os.path.getsize("files/"+fileName)

            dataSegment= fileSize//8
            url, extension  = os.path.splitext(fileName)
            finishFileTransmission= False
            startTransmission=False
            segmentNumber=0
            mss= 1800
          #  isBinary=False
            fileType="0"

            print("size archivo: " + str(fileSize))
            print("extension del archivo "+ extension)

            openMode="r"
            if extension in binaryFilesExtensions:
                openMode+="b"
              #  isBinary=True
                fileType="1"

            file = open("files/"+fileName, openMode)
            fileData=""
            while finishFileTransmission == False:

                if(startTransmission==False):

                    print("Intercambio inicial entre servidor-cliente")

                    self.sendMesssage(client,"1 "+str(mss) +" "+ str(dataSegment)+" "+ fileName+" "+"0 "+ fileType +" "+str(fileSize))
                  #  self.socket.send("1 1800 "+ str(dataSegment)+" "+ fileName+" "+"0 "+"0 "+str(fileSize))

                    data= self.receiveMessage(client,False)
                    if data =="T":
                        startTransmission=True
                        print("Va a iniciar la transmision del archivo")
                    else:
                        print("El cliente ha cancelado la solicitud del archivo")
                        break
                else:
                    #esperar una respuesta por parte del servidor solo durante un tiempo determinado
                    ready = select.select([client], [], [], 1)

                    # si el servidor envio datos llamar a receive
                    if ready[0]:
                        data= self.receiveMessage(client,False)
                       # data= pickle.loads(data)
                        print("el servidor dice que va por esto")
                        print(data)
                        segmentNumber= int(data) // mss
                        #correccion del numero de segmento
                     #   if (segmentNumber > 0):
                      #      segmentNumber = segmentNumber -1
                        #posicionar el archivo en el byte que indica el ack
                        file.seek(int(data))

                    fileData =base64.b64encode(file.read(mss))
                    print("datos en el archivo")
                    print(fileData)
                    print("decodificando")
                    print(fileData)
                    if len(fileData)==0:
                        #informar que se finalizo de transmitir el archivo
                      #  self.socket.send(pickle.dumps({"status":1}))
                        print("segment number to server : "+ str(segmentNumber))
                        self.sendMesssage(client,"1 "+ fileType +" "+fileData+" " + str(segmentNumber))
                     #   self.socket.send("1 "+ fileType +" "+fileData)
                        finishFileTransmission=True


                    else:
                        segmentNumber += 1
                        self.sendMesssage(client,"0 "+ fileType +" " + fileData+ " " + str(segmentNumber))
                      #  self.socket.send("0 "+ fileType +" " + fileData)
                        #el envio continua
                       # self.socket.send(pickle.dumps({"status":0,"data":fileData}))

            file.close()
           # client.close()

        except IOError as e:
            self.sendMesssage(client,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            self.sendMesssage(client, "F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def receiveFile(self,client,initialData):

        try:

            print("datos iniciales recibidos")
            print(initialData)

            fileSize= int(initialData[6])
            mss= int(initialData[1])
            windowSize= int(initialData[2])
            ack=0
            newFile= open("files/"+initialData[3],self.typeOfFile(int(initialData[5])))

            bytesTransfered=0
            fileTransfered=False
            data={}
            print("enviar al cliente una notifiacion de archivo")
            self.sendMesssage(client,"T")

            while fileTransfered==False:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([client], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data= self.receiveMessage(client,True)
                   # data = client.recv(self.receiveBufferSize).split(" ")

                  #  data= pickle.loads(data)

                    if (int(data[0]) == 1):
                        print("El archivo ha sido recibido")
                        break
                    #verificar si los bytes enviados corresponden a los siguientes bytes que yo estoy esperando, si no de igual manera aumenta el ack, pero no el byte transfered
                    #archivos de texto

                    print("numero segmento " + data[3])
                    print("esperado " + str(bytesTransfered))
                    print("primera condicion "+ str(int(data[3])*mss))
                    print ("segunda condicion" + str(bytesTransfered+mss))

                    if (int(data[3])*mss == (bytesTransfered+mss)):



                        if int(data[1])==0:
                           lines= base64.b64decode(data[2]).split("\n")
                           largo = len(lines)-1
                           for line in lines:
                               if line==lines[largo]:
                                   newFile.write(line)
                               else:
                                   newFile.write(line+ os.linesep)

                        else:
                            newFile.write(base64.b64decode(data[2]))

                        bytesTransfered += mss

                    ack += mss

                    if (ack >= windowSize):
                        if bytesTransfered < fileSize:
                            self.sendMesssage(client,str(bytesTransfered))
                          #  client.send(str(bytesTransfered))
                            ack=0





                                                  #  client.send(pickle.dumps({"ack":ack}))



            newFile.close()
            client.close()

        except IOError as e:
            self.sendMesssage(client,"F")
            print(
                "Ocurrio un error generando el archivo")
            print(e)


    def handleClient(self,client):
        print("administrando cliente")

        while True:
            # esperar una respuesta por parte del cliente solo durante un tiempo determinado

            ready = select.select([client], [], [], 1)
            print("esperando mensaje del cliente")
            print("valor de ready")
            print(str(ready))
            # si el servidor envio datso llamar a receive
            if ready[0]:
                print("Mensaje Recibido")
                data = self.receiveMessage(client,True)
                print(data)
                if len(data[0]) == 0:
                    continue
                print("El cliente solicita ejecutar una operacion")
                if int(data[0])==0:
                    print("cliente desea descargar un archivo")
                    self.sendFile(client,data[1])
                    print("El archivo ha sido enviado al cliente")
                    break

                elif int(data[0])==1:
                    print("cliente desea subir un archivo")
                    self.receiveFile(client,data)
                    print("se finalizo de recibir el archivo")
                    break
                elif int(data[0])==2:
                    print("cliente desea visualizar la lista de archivos")
                    self.seeFilesInFolder(client)
                    break

        client.close()

    def handleClientConnections(self):

        while self.closeSocket == False:
            # accept connections from outside
            (clientSocket, address) = self.serversocket.accept()

            Thread(target=self.handleClient, args=(clientSocket,)).start()

        self.serversocket.close()

"""""""""" UDP socket server class """""""" """

class ClientMessage:

    def __init__(self,data,clientAddress):

        self.data=data
        self.clientData= clientAddress

    def getData(self):

        return self.data

    def getClientData(self):

        return self.clientData


class UDPSocketServerManager:

    def __init__(self,receiveBufferSize,sendBufferSize,port):

        self.closeSocket=False
        self.receiveBufferSize = receiveBufferSize
        self.sendBufferSize = sendBufferSize
        self.messageList=[]
        self.filesUploading={}

        # create an INET, STREAMing socket
        self.serversocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)

        # bind the socket to a public host, and a well-known port
        self.serversocket.bind((socket.gethostbyname(socket.gethostname()),port))
        # maximun socket server connections
       # self.serversocket.listen(20)
        print(" UDP socket listen at "+  socket.gethostbyname(socket.gethostname()) +" port "+ str(port))
        print("")
        self.initOperation()

    def sendMesssage(self, socketConnection,destiny, message):

        socketConnection.sendto(message,destiny)

    def receiveMessage(self, socketConnection, split):

        data = ""
        address = ""
        if split == True:
            data, address = socketConnection.recvfrom(self.receiveBufferSize)
            data = data.split(" ")

        else:
            data, address = socketConnection.recvfrom(self.receiveBufferSize)
        return data, address

    def typeOfFile(self,isBinary):

        if isBinary == 1:
            return "wb"

        return "w"

    def seeFilesInFolder(self,client,clientAddress):


        print("desea ver los archivos del servidor")
        folderFiles = os.listdir("files")


        print("archivos en carpeta.. ")
        print(folderFiles)

        try:

            for file in folderFiles:

                self.sendMesssage(client,clientAddress,file)


        except OSError as e:
            self.sendMesssage(client,clientAddress,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def sendFile(self, client,clientAddress,fileName):

        try:

            fileSize= os.path.getsize("files/"+fileName)

            url, extension  = os.path.splitext(fileName)
            mss=1800
          #  isBinary=False
            fileType="0"
            openMode="r"
            if extension in binaryFilesExtensions:
                openMode+="b"
              #  isBinary=True
                fileType="1"

            file = open("files/"+fileName, openMode)


            self.sendMesssage(client, clientAddress, fileType+" "+str(fileSize)+" "+str(mss))

            fileData="contenidoInicial"
            while len(fileData) > 0:

                fileData =base64.b64encode(file.read(mss))
                self.sendMesssage(client,clientAddress,fileData)
                time.sleep(1.2)


            file.close()


        except IOError as e:
            self.sendMesssage(client,clientAddress,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


        except OSError as e:
            self.sendMesssage(client,clientAddress,"F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def generateFile(self,fileData):

        try:

            fileType=int(fileData[0]["fileType"])
            fileSize= int(fileData[0]["fileSize"])

            print("size archivo "+ str(fileSize))
            print("bytes recibido "+ str((len(fileData)-1)* int(fileData[0]["fileSegment"])))

            if ((len(fileData)-1)* int(fileData[0]["fileSegment"])) >= fileSize:

                newFile = open("files/" + fileData[0]["fileName"], self.typeOfFile(fileType))

                for index in range(1,len(fileData),1):

                    time.sleep(0.2)
                    if fileType == 0:
                        lines = base64.b64decode(fileData[index]["data"]).split("\n")
                        largo = len(lines) - 1
                        for line in lines:
                            if line == lines[largo]:
                                newFile.write(line)
                            else:
                                newFile.write(line + os.linesep)

                    else:
                        newFile.write(base64.b64decode(fileData[index]["data"]))
                print("El archivo con nombre "+ fileData[0]["fileName"] +" ha sido recibido")
                newFile.close()
                return


            else:
                print("Error !!!. Parece que no fue posible recibir el archivo completo desde el cliente")



        except IOError as e:
            print("ocurrio un error al generar el archivo subido por el cliente")
            print(e)

    def checkFilesUploading(self,filesDic):

        while self.closeSocket == False:


            for fileUpload in filesDic.keys():

                if (len(filesDic[fileUpload]) == 1):
                    continue

                currentTime = datetime.now()

                lastPacket= filesDic[fileUpload][len(filesDic[fileUpload])-1]
                timeDifference= currentTime - lastPacket["receiveAt"]

                if timeDifference.total_seconds() >= 10:
                    print("El archivo lleva en cola mas o diez segundos")
                    tempElement = filesDic[fileUpload]
                    Thread(target=self.generateFile, args=(tempElement,)).start()
                    del filesDic[fileUpload]



       # datetime.datetime.now()

    def addToFileUploading(self,dic,key,value):
        dic[key]= value

    def addFileSegment(self,dic,key,newSegment):

        dic[key].append(newSegment)

    def isInFilesUploading(self,dic,key):

        return key in dic.keys()

    def manageFileUpload(self,clientMessage):

        data= clientMessage.getData()
        if  len(data) ==2 and data[1] == "F":
            print("Cliente con IP "+ clientMessage.getClientData()[0]+" ha cancelado la transmision del archivo")

        # "Es el inicio de la transmision de un archivo"
        elif len(data) > 3:

            self.addToFileUploading(self.filesUploading,clientMessage.getClientData()[0]+data[1],
                                    [{"fileType": data[2],"fileSize":int(data[3]),"fileName":data[1],"fileSegment":int(data[4])}])

        else:

            self.addFileSegment(self.filesUploading,clientMessage.getClientData()[0]+data[1],
                                {"receiveAt":datetime.now(),"data":data[2]})



    def addMessage(self,message):

        self.messageList.append(message)

    def handleClientMessage(self, clientMessage):

        print("administrando mensaje de cliente UDP")

        data = clientMessage.getData()
        if int(data[0]) == 0:
            print("mensaje de descarga de un archivo")
            self.sendFile(self.serversocket, clientMessage.getClientData(), data[1])

            print("El archivo ha sido enviado al cliente")
            return

        elif int(data[0]) == 1:
            print("cliente desea subir un archivo")

            self.manageFileUpload(clientMessage)
            return

        elif int(data[0]) == 2:
            print("cliente desea visualizar la lista de archivos")
            self.seeFilesInFolder(self.serversocket, clientMessage.getClientData())
            return

    def readClientMessages(self):

        while self.closeSocket == False:

            if (len(self.messageList) > 0):

                message= self.messageList[0]
                self.messageList.pop(0)
                Thread(target=self.handleClientMessage, args=(message,)).start()



    def listenClientMessages(self):

        while self.closeSocket == False:

            ready = select.select([self.serversocket], [], [], 1)

            # si el servidor envio datos llamar a receive
            if ready[0]:

                data, addr = self.receiveMessage(self.serversocket, True)
                # accept connections from outside
                #  (clientSocket, address) = self.serversocket.accept()
                print("Mensaje del cliente")
                self.addMessage(ClientMessage(data,addr))
                #Thread(target=self.handleClient, args=(data, addr,)).start()

    def initOperation(self):

        Thread(target= self.listenClientMessages, args=()).start()
        Thread(target= self.readClientMessages, args=()).start()
        Thread(target=self.checkFilesUploading, args=(self.filesUploading,)).start()

    """"""""""""""""
        
    

    def handleClientConnections(self):

        while self.closeSocket == False:

            ready = select.select([self.serversocket], [], [], 1)

            # si el servidor envio datos llamar a receive
            if ready[0]:

                data, addr = self.receiveMessage(self.serversocket, True)
                # accept connections from outside
                #  (clientSocket, address) = self.serversocket.accept()
                print("conexion con cliente")
                Thread(target=self.handleClient, args=(data, addr,)).start()
"""""""""""""""


binaryFilesExtensions=[".jpg",".png",".gif",".bmp",".mp4",".avi",".mp3",".wav",".pdf",".doc",".xls",".xlsx",".ppt",".docx",".odt",
                       ".zip", ".rar", ".7z", ".tar", ".iso",".exe",".dll"]
textFilesExtensions=[".txt",".html",".xml",".css",".svg",".json"]

SEND_BUF_SIZE = 4096
RECV_BUF_SIZE = 4096


def runTCPSocket():
    tcpServerSocket = TCPSocketServerManager(RECV_BUF_SIZE, SEND_BUF_SIZE, 8083)

def runUDPSocket():
    udpServerSocket = UDPSocketServerManager(RECV_BUF_SIZE, SEND_BUF_SIZE, 8084)

Thread(target=runTCPSocket, args=()).start()
Thread(target=runUDPSocket(), args=()).start()