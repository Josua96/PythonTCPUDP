import sys
import socket
import argparse
import os
import select
import base64
import pickle
import json

from mimetypes import guess_type, guess_extension



class TCPClientSocketManager:

    def __init__(self,hostAdress,port,action,sendBufferSize,receiveBufferSize,args):

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

        if args.command == "-u":
            if args.file:
                self.sendFile(args.file)
                print("el archivo ha sido enviado satisfactoriamente")

    def sendFile(self, fileName):


        try:

            fileSize= os.path.getsize(fileName)

            dataSegment= fileSize//8
            url, extension  = os.path.splitext(fileName)
            finishFileTransmission= False
            startTransmission=False
            isBinary=False
            fileType="0"

            print("size archivo: " + str(fileSize))
            print("extension del archivo "+ extension)

            openMode="r"
            if extension in binaryFilesExtensions:
                openMode+="b"
                isBinary=True
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
                    self.socket.send("1 2048 "+ str(dataSegment)+" "+ fileName+" "+"0 "+"0 "+str(fileSize))

                    data=self.socket.recv(self.receiveBufferSize)
                    if data =="True":
                        startTransmission=True
                        print("Va a iniciar la transmision del archivo")
                    else:
                        print("El servidor no esta disponible para recibir archivos intente en otro momento");
                        break
                else:
                    #esperar una respuesta por parte del servidor solo durante un tiempo determinado
                    ready = select.select([self.socket], [], [], 1)

                    # si el servidor envio datos llamar a receive
                    if ready[0]:
                        data = self.socket.recv(self.receiveBufferSize)
                       # data= pickle.loads(data)
                        print("el servidor dice que va por esto")
                        print(data)
                        #posicionar el archivo en el byte que indica el ack
                        file.seek(int(data))

                    fileData =base64.b64encode(file.read(8))
                    print("datos en el archivo")
                    print(fileData)
                    print("decodificando")
                    print(fileData)
                    if len(fileData)==0:
                        #informar que se finalizo de transmitir el archivo
                      #  self.socket.send(pickle.dumps({"status":1}))
                        self.socket.send("1 "+ fileType +" "+fileData)
                        finishFileTransmission=True


                    else:
                        self.socket.send("0 "+ fileType +" " + fileData)
                        #el envio continua
                       # self.socket.send(pickle.dumps({"status":0,"data":fileData}))

            file.close()

        except IOError as e:
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)

        except OSError as e:
            print(
                "Ocurrio un error al intentar abrir el archivo puede que este no exista o simplemente se trata de un error de sistema")
            print(e)










""""""""""
    def dataExchangeManager(self):
        while True:
            data = self.socket.recv(self.receiveBufferSize)
            print("datos recibidos")
            print(str(data))
            if (self.disconnetMe == False):
                break

        self.socket.close()
        
        """""""""

SEND_BUF_SIZE = 4096
RECV_BUF_SIZE = 4096

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

    print("Param input " + str(given_args))
    clientSocket = TCPClientSocketManager(given_args.host,int(given_args.port),"",SEND_BUF_SIZE,RECV_BUF_SIZE,
                                          given_args)
   # list = os.listdir("files") # returns list
   # print(list)


if __name__ == '__main__':
    main()