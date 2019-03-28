import sys
import socket
import argparse
import os
import select
import base64
import time
import pickle
import json

""""""""""""""""" 
Clase para implementacion de socket tcp
"""""""""""""""""""""""""""""""""""

class TCPClientSocketManager:

    def __init__(self,hostAdress,port,sendBufferSize,receiveBufferSize,args):

        self.socket=""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.receiveBufferSize= receiveBufferSize
            self.sendBufferSize = sendBufferSize
            self.disconnetMe=False
          #  self.socket.setblocking(0)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)
            self.socket.connect(( hostAdress , port))
           # self.socket.setblocking(0)
            print("conexion con el servidor exitosa")
            self.evaluateCommand(args)


        except socket.error as e:
            print("Error generando el socket")
            print(e)
            sys.exit(1)

        except socket.gaierror as e:
            print("Error relacionado con la direccion especificada")
            print(e)
            sys.exit(1)

        except socket.error as e:
            print("Error estableciendo la conexion con el servidor")
            print(e)
            sys.exit(1)

    def evaluateCommand(self,args):

        print("evaluando comandos")

        if str(args.command).lower() == "-u":
            if args.file:
                print("Subir archivo")
                self.sendFile(args.file)

        elif str(args.command).lower() == "-d":
            if args.file:
                print("Descargar")
                self.downloadFile(args.file)

        elif str(args.command).lower() == "-l":
            print("Ver archivos en servidor")
            self.seeFiles()


        else:
            print("El comando ingresado no corresponde a ninguno que conozca el sistema")

        sys.exit(1)

    def sendMesssage(self, socketConnection, message):

        socketConnection.send(message)

    def receiveMessage(self, socketConnection,split):
        data=""
        if split == True:
            data = socketConnection.recv(self.receiveBufferSize).split(" ")
        else:
            data = socketConnection.recv(self.receiveBufferSize)
        return data

    def typeOfFile(self,isBinary):

        if isBinary == 1:
            return "wb"

        return "w"

    def seeFiles(self):

        self.sendMesssage(self.socket,"2")
        data= self.receiveMessage(self.socket,True)

        if data[0]=="F":
            self.sendMesssage(self.socket, "F")
            print("El servidor tuvo problemas para acceder a el directorio de archivos")
            return

        amountofFiles= int(data[0])

        if amountofFiles == 0:
            #no los envie
            self.sendMesssage(self.socket,"F")
            print("El servidor no cuenta con ningun archivo actualmente")
            return

        else:
            self.sendMesssage(self.socket, "T")

        windowSize= int(data[1])
        filesNamesReceived=0
        forAck=0

        print("Archivos contenidos en el servidor")
        print("")
        finDeLista= False
        #en cada mensaje vendra el numero del elemento de la lista transmitido y el texto correspondiente
        while True:

            data= self.receiveMessage(self.socket,True)

            if data[0]=="E":
                print("")
                print("Se han recuperado todos los nombres de los archivos alojados en el servidor")
                break

            if int(data[0]) == filesNamesReceived:
                print(str(filesNamesReceived+1)+" -- "+ data[1])
                filesNamesReceived += 1

            forAck+=1
            if forAck == windowSize and filesNamesReceived < (amountofFiles-1):

                self.sendMesssage(self.socket,str(filesNamesReceived))
                forAck=0


    def downloadFile(self,fileName):

        try:
            print("se envio mensaje al socket... "+ "0 "+ fileName)
            self.sendMesssage(self.socket,"0 "+ fileName)

            res= self.receiveMessage(self.socket,True)
            print("se recibieron datos del socket")
            print(res)

            if res[0] == "F":
                print("No fue posible obtener el archivo del servidor")
                return
            fileSize = int(res[6])
            mss = int(res[1])
            windowSize = int(res[2])
            ack = 0
            newFile = open(res[3], self.typeOfFile(int(res[5])))

            bytesTransfered = 0
            fileTransfered = False
            data = {}
            print("Notificar al servidor de que ya puede enviar el archivo")
            self.sendMesssage(self.socket, "T")

            while fileTransfered == False:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([self.socket], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data = self.receiveMessage(self.socket, True)
                    # data = client.recv(self.receiveBufferSize).split(" ")
                    print("datos del archivo recibidos")
                    #  data= pickle.loads(data)

                    if (int(data[0]) == 1):
                        print("El archivo ha sido recibido")
                        break
                    # verificar si los bytes enviados corresponden a los siguientes bytes que yo estoy esperando, si no de igual manera aumenta el ack, pero no el byte transfered
                    # archivos de texto

                    print("numero segmento " + data[3])
                    print("esperado " + str(bytesTransfered))
                    print("primera condicion " + str(int(data[3]) * mss))
                    print("segunda condicion" + str(bytesTransfered + mss))

                    if (int(data[3]) * mss == (bytesTransfered + mss)):

                        if int(data[1]) == 0:
                            lines = base64.b64decode(data[2]).split("\n")
                            largo = len(lines) - 1
                            for line in lines:
                                if line == lines[largo]:
                                    newFile.write(line)
                                else:
                                    newFile.write(line + os.linesep)

                        else:
                            newFile.write(base64.b64decode(data[2]))

                        bytesTransfered += mss

                    ack += mss

                    if (ack >= windowSize):
                        if bytesTransfered < fileSize:
                            self.sendMesssage(self.socket, str(bytesTransfered))
                            #  client.send(str(bytesTransfered))
                            ack = 0

                            #  client.send(pickle.dumps({"ack":ack}))

            newFile.close()

        except IOError as e:
            self.sendMesssage(self.socket,"F")
            print(
                "Ocurrio un error generando el archivo")
            print(e)

    def sendFile(self, fileName):

        try:

            fileSize= os.path.getsize(fileName)

            dataSegment= fileSize//8
            url, extension  = os.path.splitext(fileName)
            finishFileTransmission= False
            startTransmission=False
            segmentNumber=0
            mss=1800
          #  isBinary=False
            fileType="0"

            print("size archivo: " + str(fileSize))
            print("extension del archivo "+ extension)

            openMode="r"
            if extension in binaryFilesExtensions:
                openMode+="b"
              #  isBinary=True
                fileType="1"

            file = open(fileName, openMode)
            fileData=""
            while finishFileTransmission == False:

                if(startTransmission==False):

                    print("Solicitando al servidor el servicio de subir archivo")
                    """""""""""
                    self.socket.send(pickle.dumps({"action":1, "mss":800,"windowSize":int(dataSegment),
                                      "fileName":fileName,"status":0,"isBinary":isBinary,
                                      "fileSize":int(fileSize)}))
                    """""""""
                    self.sendMesssage(self.socket,"1 "+ str(mss) + " "+ str(dataSegment)+" "+ fileName+" "+"0 "+ fileType +" " +str(fileSize))
                  #  self.socket.send("1 1800 "+ str(dataSegment)+" "+ fileName+" "+"0 "+"0 "+str(fileSize))

                    data= self.receiveMessage(self.socket,False)
                    if data =="T":
                        startTransmission=True
                        print("Va a iniciar la transmision del archivo")
                    else:
                        print("El servidor no esta disponible para recibir archivos intente en otro momento")
                        break
                else:
                    #esperar una respuesta por parte del servidor solo durante un tiempo determinado
                    ready = select.select([self.socket], [], [], 1)

                    # si el servidor envio datos llamar a receive
                    if ready[0]:
                        data= self.receiveMessage(self.socket,False)
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
                        self.sendMesssage(self.socket,"1 "+ fileType +" "+fileData+" " + str(segmentNumber))
                     #   self.socket.send("1 "+ fileType +" "+fileData)
                        finishFileTransmission=True


                    else:
                        segmentNumber += 1
                        self.sendMesssage(self.socket,"0 "+ fileType +" " + fileData+ " " + str(segmentNumber))
                      #  self.socket.send("0 "+ fileType +" " + fileData)
                        #el envio continua
                       # self.socket.send(pickle.dumps({"status":0,"data":fileData}))

            file.close()

        except IOError as e:
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            print("Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


""""""""""""""""" 
Clase para implementacion de socket udp
"""""""""""""""""""""""""""""""""""

class UDPClientSocketManager:

    def __init__(self, hostAdress, port, sendBufferSize, receiveBufferSize, args):

        self.socket = ""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.receiveBufferSize = receiveBufferSize
            self.sendBufferSize = sendBufferSize
            self.disconnetMe = False
            self.hostAddress= hostAdress
            self.port= port
            #  self.socket.setblocking(0)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendBufferSize)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiveBufferSize)
          #  self.socket.connect((hostAdress, port))
            # self.socket.setblocking(0)
            print("No hay conexion directa con el socket, solo se envian paquetes")
            self.evaluateCommand(args)


        except socket.error as e:
            print("Error generando el socket")
            print(e)
            sys.exit(1)

        except socket.gaierror as e:
            print("Error relacionado con la direccion especificada")
            print(e)
            sys.exit(1)

        except socket.error as e:
            print("Error estableciendo la conexion con el servidor")
            print(e)
            sys.exit(1)

    def evaluateCommand(self, args):

        print("evaluando comandos")

        if str(args.command).lower() == "-u":
            if args.file:
                print("Subir archivo")
                self.sendFile(args.file)

        elif str(args.command).lower() == "-d":
            if args.file:
                print("Descargar")
                self.downloadFile(args.file)

        elif str(args.command).lower() == "-l":
            print("Ver archivos en servidor")
            self.seeFiles()


        else:
            print("El comando ingresado no corresponde a ninguno que conozca el sistema")

        sys.exit(1)

    def sendMesssage(self, socketConnection, message):

        socketConnection.sendto(message,(self.hostAddress,self.port))

    def receiveMessage(self, socketConnection, split):

        data=""
        address=""

        if split == True:
            data,address= socketConnection.recvfrom(self.receiveBufferSize)
            data= data.split(" ")

        else:
            data,address= socketConnection.recvfrom(self.receiveBufferSize)
        return data,address


    def typeOfFile(self, isBinary):

        if isBinary == 1:
            return "wb"

        return "w"



    def seeFiles(self):

        self.sendMesssage(self.socket, "2")

        fileNamesReceived=0

        print("Archivos contenidos en el servidor")
        print("")
        try:

            while True:
                self.socket.settimeout(5)
                data,clientAddress = self.receiveMessage(self.socket, False)

                if data=="F":
                    print("El servidor tuvo problemas para acceder al directorio de archivos")
                    break

                print(str(fileNamesReceived+1)+" -- "+ data)
                fileNamesReceived+=1

        except socket.timeout as e:
            print("Se han recuperado todos los nombres de los archivos alojados en el servidor")
            print("NOTA: Pueden faltar archivos debido al uso del protocolo UDP o el tiempo de espera se ha agotado")


    def downloadFile(self, fileName):

        try:

            self.socket.settimeout(5)
            print("se envio mensaje al socket... " + "0 " + fileName)
            self.sendMesssage(self.socket, "0 " + fileName)

            res,address = self.receiveMessage(self.socket, True)

            if res[0] == "F":
                print("No fue posible obtener el archivo del servidor")
                return

            print("respuesta del servidor")
            print(res)
            fileSize= int(res[1])
            mss=int(res[2])
            receivedBytes = 0
            print("tipo de lectura: "+ self.typeOfFile(int(res[0])))
            newFile = open(fileName, self.typeOfFile(int(res[0])))

            while True:



                data,address = self.receiveMessage(self.socket, False)

                if int(res[0]) == 0:
                    lines = base64.b64decode(data).split("\n")
                    largo = len(lines) - 1
                    for line in lines:
                        if line == lines[largo]:
                            newFile.write(line)
                        else:
                            newFile.write(line + os.linesep)

                else:
                    newFile.write(base64.b64decode(data))


                receivedBytes+=mss


            newFile.close()


        except socket.timeout as e:
            if (receivedBytes > fileSize):
                print("El archivo ha sido descargado")

            print("NOTA: El archivo puede no haberse construido bien debido al uso del protocolo UDP o el tiempo de espera se ha agotado")

    def sendFile(self,fileName):

        try:



            fileSize = os.path.getsize(fileName)

            url, extension = os.path.splitext(fileName)
            mss = 1800
            #  isBinary=False
            fileType = "0"
            openMode = "r"
            if extension in binaryFilesExtensions:
                openMode += "b"
                #  isBinary=True
                fileType = "1"

            file = open(fileName, openMode)

           #self.sendMesssage(self.socket, "1 " + fileName)

            self.sendMesssage(self.socket,"1 "+fileName +" " +fileType + " " + str(fileSize) + " " + str(mss))

            fileData = "contenidoInicial"
            while len(fileData) > 0:

                fileData = base64.b64encode(file.read(mss))
                self.sendMesssage(self.socket, "1 " + fileName +" "+fileData)
                time.sleep(1)

            print("")
            print("El archivo se ha enviado al servidor")
            print("")
            file.close()


        except IOError as e:
            self.sendMesssage(self.socket,"1 F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


        except OSError as e:
            self.sendMesssage(self.socket,"1 F")
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)


SEND_BUF_SIZE = 4096
RECV_BUF_SIZE = 4096


TCPPort=8083
UDPPort=8084

binaryFilesExtensions=[".jpg",".png",".gif",".bmp",".mp4",".avi",".mp3",".wav",".pdf",".doc",".xls",".ppt",".docx",".odt",
                       ".zip", ".rar", ".7z", ".tar", ".iso",".exe",".dll"]
textFilesExtensions=[".txt",".html",".xml",".css",".svg",".json"]

def main():
    parser = argparse.ArgumentParser(description='Manage params')
    parser.add_argument('--host', action="store", dest="host", required=True)
    parser.add_argument('--port', action="store", dest="port", required=True)
    parser.add_argument('--command', action="store", dest="command", required=True)
    parser.add_argument('--file', action="store", dest="file", required=False)
    given_args = parser.parse_args()

    if(int(given_args.port)== 8083):
        clientSocket = TCPClientSocketManager(given_args.host, int(given_args.port), SEND_BUF_SIZE, RECV_BUF_SIZE,
                                              given_args)

    elif (int(given_args.port)== 8084):
        clientSocket = UDPClientSocketManager(given_args.host, int(given_args.port), SEND_BUF_SIZE, RECV_BUF_SIZE,
                                              given_args)
   # list = os.listdir("files") # returns list
   # print(list)

if __name__ == '__main__':
    main()