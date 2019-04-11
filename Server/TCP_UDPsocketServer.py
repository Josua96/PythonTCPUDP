import socket
import select
from threading import Thread
from datetime import datetime
import os
import base64

import time
from cryptography.fernet import Fernet


class TCPSocketServerManager:

    def __init__(self,receiveBufferSize,sendBufferSize,port):

        self.closeSocket=False
        self.receiveBufferSize = receiveBufferSize
        self.sendBufferSize = sendBufferSize

        # create an INET, STREAMing socket
        self.serversocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)

        self.defaultKey = b'BHY_aiMMELU-lK7fP__Gs14T1XWqV8rV2fusTcZq2Os='
        self.decryptor= Fernet(self.defaultKey)

        # bind the socket to a public host, and a well-known port
        self.serversocket.bind((socket.gethostbyname(socket.gethostname()),port))
        # maximun socket server connections
        self.serversocket.listen(20)
        print(" TCP socket listen at "+  socket.gethostbyname(socket.gethostname()) +" port "+ str(port))
        print("")
        self.handleClientConnections()

    def decryptMessage(self, decryptor, message,decode):

        decryptedMessage = message

        msg = decryptor.decrypt(decryptedMessage)

        if decode:
            msg = msg.decode()

        return msg


    def encryptMessage(self,encryptor, message,encode):

        if encode==True:
            message = message.encode()


        encryptedMessage = encryptor.encrypt(message)


        return encryptedMessage

    def sendMesssage(self,socketConnection,encryptor,message,encode):

        realMessage = self.encryptMessage(encryptor,message,encode)
        print("mensaje enviado ----")
        print(realMessage)
        socketConnection.send(realMessage)

    def receiveMessage(self,socketConnection,enc,split,decode):

        data = ""

        data = socketConnection.recv(self.receiveBufferSize)
        data = self.decryptMessage(enc, data,decode)
        if split == True:

            data = data.split(" ")


        return data

    def typeOfFile(self,isBinary):

        if isBinary == 1:
            return "wb"

        return "w"

    def seeFilesInFolder(self,client,clientEncryptor):

        try:

            folderFiles = os.listdir()
            filesAmount= len(folderFiles)
            windowSize=5

            print("archivos en carpeta.. ")
            print(folderFiles)

            self.sendMesssage(client,clientEncryptor,str(filesAmount)+" "+str(windowSize),True)

            data= self.receiveMessage(client,clientEncryptor,False,True)

            if data=="F":
                print("El cliente ha cancelado la operacion")
                return

            fileTransmitted=0

            while fileTransmitted < filesAmount:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([client], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data = self.receiveMessage(client,clientEncryptor,False,True)
                    data = int(data)
                    print("El cliente dice que ha recibido hasta el indice "+ str(data))
                    #seguir enviando nombres de archivos de la lista a partir de esta posicion

                    fileTransmitted=data

                self.sendMesssage(client,clientEncryptor,str(fileTransmitted)+" "+folderFiles[fileTransmitted],True)
                fileTransmitted+=1
                
            self.sendMesssage(client,clientEncryptor,"E",True)

        except IOError as e:
            self.sendMesssage(client,clientEncryptor,"F",True)
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            self.sendMesssage(client,clientEncryptor,"F",True)
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def sendFile(self,client,fileName,clientEncryptor):

        try:

            fileSize= os.path.getsize(fileName)

            dataSegment= fileSize//8
            url, extension  = os.path.splitext(fileName)
            finishFileTransmission= False
            startTransmission=False
            segmentNumber=0
            mss= 1800
            fileType="0"

            print("size archivo: " + str(fileSize))
            print("extension del archivo "+ extension)

            openMode="rb"

            file = open(fileName, openMode)
            fileData=""
            while finishFileTransmission == False:

                if(startTransmission==False):

                    print("Intercambio inicial entre servidor-cliente")

                    self.sendMesssage(client,clientEncryptor,"1 "+str(mss) +" "+ str(dataSegment)+" "+ fileName+" "+"0 "+str(fileSize),True)
                  #  self.socket.send("1 1800 "+ str(dataSegment)+" "+ fileName+" "+"0 "+"0 "+str(fileSize))

                    data= self.receiveMessage(client,clientEncryptor,False,True)
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
                        data= self.receiveMessage(client,clientEncryptor,False,True)
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
                        print("segment number to server : "+ str(segmentNumber))
                        self.sendMesssage(client,clientEncryptor,"1 ".encode()+ fileType.encode() +" ".encode()+fileData+" ".encode() + str(segmentNumber).encode(),False)

                        finishFileTransmission=True


                    else:
                        segmentNumber += 1
                        self.sendMesssage(client,clientEncryptor,"0 ".encode()+ fileType.encode() +" ".encode()+fileData+" ".encode() + str(segmentNumber).encode(),False)


            file.close()

        except IOError as e:
            self.sendMesssage(client,clientEncryptor,"F",True)
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            self.sendMesssage(client, clientEncryptor,"F",True)
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def receiveFile(self,client,initialData,clientEncryptor):

        try:

            print("datos iniciales recibidos")
            print(initialData)

            fileSize= int(initialData[5])
            mss= int(initialData[1])
            windowSize= int(initialData[2])
            ack=0

            newFile = open(initialData[3], "wb")

            bytesTransfered=0
            fileTransfered=False
            data={}
            print("enviar al cliente una notifiacion de archivo")
            self.sendMesssage(client,clientEncryptor,"T",True)

            while fileTransfered==False:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([client], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data= self.receiveMessage(client,clientEncryptor,True,True)
                   # data = client.recv(self.receiveBufferSize).split(" ")

                  #  data= pickle.loads(data)

                    if (int(data[0]) == 1):
                        print("El archivo ha sido recibido")
                        break

                    #verificar si los bytes enviados corresponden a los siguientes bytes que yo estoy esperando, si no de igual manera aumenta el ack, pero no el byte transfered
                    #archivos de texto

                    if (int(data[3])*mss == (bytesTransfered+mss)):


                        newFile.write(base64.b64decode(data[2]))
                        bytesTransfered += mss

                    ack += mss

                    if (ack >= windowSize):
                        if bytesTransfered < fileSize:
                            self.sendMesssage(client,clientEncryptor,str(bytesTransfered),True)
                          #  client.send(str(bytesTransfered))
                            ack=0

            newFile.close()
            client.close()

        except IOError as e:
            self.sendMesssage(client,clientEncryptor,"F",True)
            print(
                "Ocurrio un error generando el archivo")
            print(e)


    def handleClient(self,client):
        print("administrando cliente")
        clientKey=""
        data= self.receiveMessage(client,self.decryptor,False,False)

        print("client key")
        print(data)
        clientKey=data
        clientEncryptor = Fernet(data)

        self.sendMesssage(client,clientEncryptor,"OK",True)

        while True:
            # esperar una respuesta por parte del cliente solo durante un tiempo determinado

            ready = select.select([client], [], [], 1)


            # si el servidor envio datso llamar a receive
            if ready[0]:
                print("Mensaje Recibido")
                data = self.receiveMessage(client,clientEncryptor,True,True)
                print(data)
                if len(data[0]) == 0:
                    continue
                print("El cliente solicita ejecutar una operacion")
                if int(data[0])==0:
                    print("cliente desea descargar un archivo")
                    self.sendFile(client,data[1],clientEncryptor)
                    print("El archivo ha sido enviado al cliente")
                    break

                elif int(data[0])==1:
                    print("cliente desea subir un archivo")
                    self.receiveFile(client,data,clientEncryptor)
                    print("se finalizo de recibir el archivo")
                    break
                elif int(data[0])==2:
                    print("cliente desea visualizar la lista de archivos")
                    self.seeFilesInFolder(client,clientEncryptor)
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
        self.defaultKey = b'BHY_aiMMELU-lK7fP__Gs14T1XWqV8rV2fusTcZq2Os='
        self.decryptor = Fernet(self.defaultKey)

        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)

        # bind the socket to a public host, and a well-known port
        self.serversocket.bind((socket.gethostbyname(socket.gethostname()),port))
        # maximun socket server connections
       # self.serversocket.listen(20)
        print(" UDP socket listen at "+  socket.gethostbyname(socket.gethostname()) +" port "+ str(port))
        print("")
        self.initOperation()

    def decryptMessage(self,message, decode):

        decryptedMessage = message

        msg = self.decryptor.decrypt(decryptedMessage)

        if decode:
            msg = msg.decode()

        return msg

    def encryptMessage(self, message, encode):

        if encode == True:
            message = message.encode()

        encryptedMessage = self.decryptor.encrypt(message)

        return encryptedMessage


    def sendMesssage(self, socketConnection,destiny, message,encode):

        realMessage = self.encryptMessage(message, encode)

        socketConnection.sendto(realMessage,destiny)

    def receiveMessage(self, socketConnection, split,decode):

        data = ""
        address = ""

        data, address = socketConnection.recvfrom(self.receiveBufferSize)
        data = self.decryptMessage(data,decode)
        if split == True:
            data = data.split(" ")

        return data, address

    def typeOfFile(self,isBinary):

        if isBinary == 1:
            return "wb"

        return "w"

    def seeFilesInFolder(self,client,clientAddress):


        print("desea ver los archivos del servidor")
        folderFiles = os.listdir()


        print("archivos en carpeta.. ")
        print(folderFiles)

        try:

            for file in folderFiles:

                self.sendMesssage(client,clientAddress,file,True)


        except OSError as e:
            self.sendMesssage(client,clientAddress,"F",True)
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


    def sendFile(self, client,clientAddress,fileName):

        try:

            fileSize= os.path.getsize(fileName)

            url, extension  = os.path.splitext(fileName)
            mss=1800
          #  isBinary=False
            fileType="0"
            openMode="rb"

            file = open(fileName, openMode)


            self.sendMesssage(client, clientAddress, fileType+" "+str(fileSize)+" "+str(mss),True)

            fileData="contenidoInicial"
            while len(fileData) > 0:

                fileData =base64.b64encode(file.read(mss))
                self.sendMesssage(client,clientAddress,fileData,False)
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
            print("bytes recibidos "+ str((len(fileData)-1)* int(fileData[0]["fileSegment"])))

            if ((len(fileData)-1)* int(fileData[0]["fileSegment"])) >= fileSize:

                newFile = open(fileData[0]["fileName"],"wb")

                for index in range(1,len(fileData),1):

                    time.sleep(0.2)
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

            dictKeysUsed=[]

           # for i in list(d):
            for fileUpload in list(filesDic.keys()):

                if (len(filesDic[fileUpload]) == 1):
                    continue

                currentTime = datetime.now()

                lastPacket= filesDic[fileUpload][len(filesDic[fileUpload])-1]
                timeDifference= currentTime - lastPacket["receiveAt"]

                if timeDifference.total_seconds() >= 10:
                    print("El archivo lleva en cola mas o diez segundos")
                    tempElement = filesDic[fileUpload]
                    Thread(target=self.generateFile, args=(tempElement,)).start()
                    dictKeysUsed.append(fileUpload)


            for key in dictKeysUsed:

                del filesDic[key]

    

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

                data, addr = self.receiveMessage(self.serversocket,True,True)
                # accept connections from outside
                #  (clientSocket, address) = self.serversocket.accept()
                print("Mensaje del cliente")
                self.addMessage(ClientMessage(data,addr))
                #Thread(target=self.handleClient, args=(data, addr,)).start()

    def initOperation(self):

        Thread(target= self.listenClientMessages, args=()).start()
        Thread(target= self.readClientMessages, args=()).start()
        Thread(target=self.checkFilesUploading, args=(self.filesUploading,)).start()





SEND_BUF_SIZE = 4096
RECV_BUF_SIZE = 4096

if not os.path.exists("files"):
    os.makedirs("files")



def runTCPSocket():
    tcpServerSocket = TCPSocketServerManager(RECV_BUF_SIZE, SEND_BUF_SIZE, 8083)

def runUDPSocket():
    udpServerSocket = UDPSocketServerManager(RECV_BUF_SIZE, SEND_BUF_SIZE, 8084)

Thread(target=runTCPSocket, args=()).start()
Thread(target=runUDPSocket(), args=()).start()
