# Domoticz Snapcasdt pluging
#
# Author: akamming
#
"""
<plugin key="snapcast" name="Snapcast" author="akamming" version="0.0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/badaix/snapcast">
    <description>
        <h2>Snapcast plugin</h2><br/>
        Domoticz Snapcast integration
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Shows the volume of all snapclients as dimmerswitches in Domoticz </li>
            <li>Controls the volume of snapclients</li>
            <li>Mute or Unmute the snapclients</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Currently only clients supported</li>
            <li>TBD: Group Volume levels</li>
        </ul>
        <h3>Configuration</h3>
        Configuration options...
        <ul style="list-style-type:square">
            <li>IP adress of your SnapServer instance</li>
            <li>JSON Port of your snapserver instance (1780 on default snapcast installations)</li>
        </ul>
    </description>
    <params>
        <param field="Address" label="Snapcast IP Address" width="200px" required="true" default="localhost"/>
        <param field="Port" label="Snapcast JSON Port" width="40px" required="true" default="1780"/>
    </params>
</plugin>
"""
import Domoticz
import websocket
import json
from threading import Thread
import time
import signal

StopNow=False
Connected=False
Debugging=True
Groups={}
Clients={}

def Debug(txt):
    global Debugging
    if Debugging:
        Domoticz.Log("DEBUG: "+str(txt))

def Log(txt):
    Domoticz.Log(txt)

def RequestStatus():
    ws.send('{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}') 

def UpdateDimmer(SensorName,UnitID,muted,percent):
    #Creating devices in case they aren't there...
    Debug("UpdateDimmer("+SensorName+","+str(UnitID)+","+str(muted)+","+str(percent)+")")
    numValue=1
    if (muted):
        numValue=0
    if not (UnitID in Devices):
        Debug("Creating device "+SensorName)
        Domoticz.Device(Name=SensorName, Unit=UnitID, Type=244,Subtype=62,Switchtype=7,Used=1).Create()
    Devices[UnitID].Update(nValue=numValue,sValue=str(percent),Type=244,Subtype=62,Switchtype=7,Name=SensorName)
    Domoticz.Log("Dimmer ("+Devices[UnitID].Name+")")


def LowestFreeUnitID(Clients):
    if len(Clients)>0:
        Debug("more than 1 client")
        LowestIDFound=False
        CurrentID=1
        while LowestIDFound==False:
            LowestIDFound=True
            for key in Clients.keys():
                if Clients[key]["UnitID"]==CurrentID:
                    LowestIDFound=False
            if not LowestIDFound:
                CurrentID+=1
        return CurrentID
    else:
        Debug("One client")
        return 1


def OnServerUpdate(data):
    #converts the content of the server tag on the json
    global Clients

    Debug("ProcessStatus("+json.dumps(data)+")")
    NewClients={}
    try:
        Debug("CLients is ["+json.dumps(Clients)+"]")
        for group in data["groups"]:
            Debug("Group ["+group["id"]+"], name = "+group["name"])
            for client in group["clients"]:
                Debug ("Client ["+client["id"]+"], name="+client["host"]["name"]+", connected="+str(client["connected"])+", muted="+
                        str(client["config"]["volume"]["muted"])+", volume="+str(client["config"]["volume"]["percent"]))
                #determine UnitID: either an existing one or the lowest possible
                if client["id"] in Clients.keys():
                   UnitID=Clients[client["id"]]["UnitID"]
                else:
                   UnitID=0 
                NewClients[client["id"]]= {
                        "name": client["host"]["name"],
                        "connected": client["connected"],
                        "muted": client["config"]["volume"]["muted"],
                        "percent": client["config"]["volume"]["percent"],
                        "UnitID": UnitID
                }
            #assign id's to the zero's
            for key in NewClients.keys():
                if NewClients[key]["UnitID"]==0:
                    NewClients[key]["UnitID"]=LowestFreeUnitID(NewClients)
                    Debug("Change UnitID of "+key+" to "+str(NewClients[key]["UnitID"]))
        Clients=NewClients #copy the new list to the old one
        Debug("CLients is ["+json.dumps(Clients)+"]")
        #start updating the switchs
        for key in Clients.keys():
            client=Clients[key]
            if client["connected"]:
                UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])
            else:
                Debug(client["name"]+" is diconnected, ignoring updated")
    except Exception as err:
        Log("ERROR error processing status")
        Log(err)

def on_message(ws, message):
    try:
        Debug("received message as {}".format(message))
        data=json.loads(message)
        if "method" in data.keys():
            Debug("We have a method, let's see which one")
            if data["method"]=="Server.OnUpdate":
                OnServerUpdate(data["params"]["server"])
            elif data["method"]=="Client.OnConnect" or data["method"]=="Client.OnDisconnect":
                Debug("repopulate the config by requesting full server status")
                RequestStatus()
            #elif data["method"]=="Client.OnVolumeChanged":
            #    OnVolumeChanged(data["params"])
            else:
                Debug("unknown method")
        elif "result" in data.keys():
            Debug("We only have a result, so probably a status, try to process")
            OnServerUpdate(data["result"]["server"])
        else:
            Debug("Unable to decode message")

    except Exception as err:
        Log("ERROR decoding message")
        Log(err)

def on_error(ws, error):
    '''
        This method is invoked when there is an error in connectivity
    '''
    Log("ERROR: received error as {}".format(error))

def on_close(ws):
    '''
        This method is invoked when the connection between the
        client and server is closed
    '''
    global Connected

    Debug("Connection closed")
    Connected=False

def on_open(ws):
    global Connected

    Debug("Connection is open")
    Connected=True
    RequestStatus()

def connect_websocket():
    global ws
    global wst

    url ="ws://"+Parameters["Address"]+":"+str(Parameters["Port"])+"/jsonrpc"
    Debug("Setting up connection with ["+url+"]")
    ws = websocket.WebSocketApp(url, on_message = on_message, on_error = on_error, on_close = on_close, on_open = on_open)

    Debug("Starting thread")
    wst=Thread(target=ws.run_forever)
    wst.start()

def heartbeat():
    if not Connected:
        try:
            if not StopNow:
                Debug("Trying to establish connection..")
                connect_websocket()
        except Exception as err:
            Log("Connect Failed")
            Log(err)
    else:
        Debug("still running..")

class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        Debug("onStart called")
        heartbeat()

    def onStop(self):
        global ws

        Debug("onStop called")
        ws.close() #stop the websocketapp

    def onConnect(self, Connection, Status, Description):
        Debug("onConnect called")

    def onMessage(self, Connection, Data):
        Debug("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Debug("onDisconnect called")

    def onHeartbeat(self):
        Debug("onHeartbeat called")
        heartbeat()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Debug("Device Name:     '" + Devices[x].Name + "'")
        Debug("Device nValue:    " + str(Devices[x].nValue))
        Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
