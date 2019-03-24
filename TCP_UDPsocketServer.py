import socket
import select
from threading import Thread
import os
import base64
import pickle


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
        print("socket listen at "+  socket.gethostbyname(socket.gethostname()) +" port "+ str(port))
        self.handleClientConnections()

    def typeOfFile(self,isBinary):

        if isBinary == 0:
            return "wb"

        return "w"

    def receiveFile(self,client,initialData):

        try:

            print("datos iniciales recibidos")
            print(initialData)

            fileSize= int(initialData[6])
            mss= int(initialData[1])
            windowSize= int(initialData[2])
            ack=0
            newFile= open("files/"+initialData[3],self.typeOfFile(int(initialData[5])))

            bytesTransfered=0;
            fileTransfered=False
            data={}
            print("enviar al cliente una notifiacion de archivo")
            client.send("True")

            while fileTransfered==False:

                # esperar una respuesta por parte del servidor solo durante un tiempo determinado
                ready = select.select([client], [], [], 1)

                # si el servidor envio datos llamar a receive
                if ready[0]:
                    data = client.recv(self.receiveBufferSize).split(" ")
                    print("datos del archivo recibidos")
                  #  data= pickle.loads(data)

                    if (int(data[0]) == 1):
                        print("El archivo ha sido recibido")
                        break

                    #archivos de texto
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



                                                  #  client.send(pickle.dumps({"ack":ack}))



            newFile.close()
            client.close()

        except IOError as e:
            client.send({"send":False})
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
                data= client.recv(self.receiveBufferSize).split(" ")
                print(data)
                print("El cliente solicita ejecutar una operacion")
                if int(data[0])==0:
                    print("cliente desea descargar un archivo")

                elif int(data[0])==1:
                    print("cliente desea subir un archivo")
                    self.receiveFile(client,data)
                    print("se finalizo de recibir el archivo")
                    break
                else:
                    print("cliente desea visualizar la lista de archivos")



    def handleClientConnections(self):

        while self.closeSocket == False:
            # accept connections from outside
            (clientSocket, address) = self.serversocket.accept()

            Thread(target=self.handleClient, args=(clientSocket,)).start()

        self.serversocket.close()




SEND_BUF_SIZE = 4096
RECV_BUF_SIZE = 4096

serverSocket= TCPSocketServerManager(RECV_BUF_SIZE,SEND_BUF_SIZE,8083)