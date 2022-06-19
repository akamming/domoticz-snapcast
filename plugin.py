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
            <li>Debugging enabled yes/no</li>
        </ul>
    </description>
    <params>
        <param field="Address" label="Snapcast IP Address" width="200px" required="true" default="localhost"/>
        <param field="Port" label="Snapcast JSON Port" width="40px" required="true" default="1780"/>
         <param field="Mode1" label="Debugging" width="50px">
         <options>
            <option label="True" value="true"/>
            <option label="False" value="false" default="true"/>
         </options>
         </param>
    </params>
</plugin>
"""
import Domoticz
import websocket
import json
from threading import Thread
import os
import traceback

StopNow=False
Connected=False
Debugging=False
Groups={}
Clients={}
ConfigFile="SnapConfig.json"

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
    if float(percent)<1:
        percent=1 #prevent division by zero's..

    Debug("UpdateDimmer("+SensorName+","+str(UnitID)+","+str(muted)+","+str(percent)+")")
    numValue=1
    if (muted):
        numValue=0
    if not (UnitID in Devices):
        Debug("Creating device "+SensorName)
        Domoticz.Device(Name=SensorName, Unit=UnitID, Type=244,Subtype=62,Switchtype=7,Used=1).Create()
    Devices[UnitID].Update(nValue=numValue,sValue=str(percent),Type=244,Subtype=62,Switchtype=7,Name=SensorName)
    Domoticz.Log("Dimmer ("+Devices[UnitID].Name+")")

def LowestFreeUnitID(Clients,Groups):
    if len(Clients)>0:
        LowestIDFound=False
        CurrentID=1
        while LowestIDFound==False:
            LowestIDFound=True #set for true, but override if found in either groups or clients
            #check clients
            for key in Clients.keys():
                if Clients[key]["UnitID"]==CurrentID:
                    LowestIDFound=False

            #check groups
            for key in Groups.keys():
                if Groups[key]["UnitID"]==CurrentID:
                    LowestIDFound=False

            if not LowestIDFound:
                CurrentID+=1
        return CurrentID
    else:
        Domoticz.Log("ERROR: The list is empty")
        return 1

def UpdateGroupVolume(GroupID):
    #Calculate average group volume
    noofclients=0
    sumofclientvolumes=0
    for key in Clients.keys():
        if Clients[key]["GroupID"]==GroupID:
            noofclients+=1
            sumofclientvolumes+=Clients[key]["percent"]
    #update the dimmer
    UpdateDimmer(Groups[GroupID]["name"],Groups[GroupID]["UnitID"],False,str(sumofclientvolumes/noofclients))

def OnServerUpdate(data):
    #converts the content of the server tag on the json
    global Clients, Groups

    NewClients={}
    NewGroups={}
    try:
        for group in data["groups"]:
            #determine UnitID (if present)
            if group["id"] in Groups.keys():
               UnitID=Groups[group["id"]]["UnitID"]
            else:
               UnitID=0  # determine later, we need to now all used id's before we can generate a new one

            #devicename is ID, unless name is configured in Snap Config
            Name=group["name"]
            if Name=="":
                Name=group["id"]
            
            #add client to new client dict
            NewGroups[group["id"]]= {
                    "name": Name,
                    "UnitID": UnitID
            }

            # Process clients in group
            for client in group["clients"]:
                #determine UnitID (if present)
                if client["id"] in Clients.keys():
                   UnitID=Clients[client["id"]]["UnitID"]
                else:
                   UnitID=0  # determine later, we need to now all used id's before we can generate a new one

                #devicename is hostname, unless name is configured in Snap Config
                Name=client["config"]["name"]
                if Name=="":
                    Name=client["host"]["name"]

                #add client to new client dict
                NewClients[client["id"]]= {
                        "name": Name,
                        "connected": client["connected"],
                        "muted": client["config"]["volume"]["muted"],
                        "percent": client["config"]["volume"]["percent"],
                        "UnitID": UnitID,
                        "GroupID": group["id"]
                }

        #assign id's to the zero's in clients
        for key in NewClients.keys():
            if NewClients[key]["UnitID"]==0:
                NewClients[key]["UnitID"]=LowestFreeUnitID(NewClients,NewGroups)
        
        #assign id's to the zero's in groups
        for key in NewGroups.keys():
            if NewGroups[key]["UnitID"]==0:
                NewGroups[key]["UnitID"]=LowestFreeUnitID(NewClients,NewGroups)

        #copy the new lists to the old one
        Clients=NewClients 
        Groups=NewGroups
        
        #Save Config
        WriteConfig()

        #update the client dimmers
        for key in Clients.keys():
            client=Clients[key]
            if client["connected"]:
                UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])

        #update the group dimmers
        for key in Groups.keys():
            UpdateGroupVolume(key)

    except Exception as err:
        Log("ERROR error processing status")
        Log(err)
        Domoticz.Log(traceback.format_exc())

def OnNameChanged(data):
    global Clients
    if Clients[data["id"]]["connected"]:
        Clients[data["id"]]["name"]=data["name"]
        client=Clients[data["id"]]
        UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])

def OnClientConnectionChange(data):
    global Clients
    Clients[data["id"]]["connected"]=data["client"]["connected"]
    Clients[data["id"]]["percent"]=data["client"]["config"]["volume"]["percent"]
    Clients[data["id"]]["muted"]=data["client"]["config"]["volume"]["muted"]
    client=Clients[data["id"]]
    UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])

def UpdateVolume(UnitID,Command,Level):
    #1st: Get snapcastID
    ID=""
    for key in Clients.keys():
        if Clients[key]["UnitID"]==UnitID:
            ID=key
    if ID!="": #it was a client
        if Command=='Set Level' or Command=='On': 
            jsoncommand='{"id":"'+ID+'","jsonrpc":"2.0","method":"Client.SetVolume","params":{"id":"'+ID+'","volume":{"muted":false,"percent":'+str(Level)+'}}}'
            ws.send(jsoncommand)
        elif Command=='Off':
            jsoncommand='{"id":"'+ID+'","jsonrpc":"2.0","method":"Client.SetVolume","params":{"id":"'+ID+'","volume":{"muted":true,"percent":'+str(Level)+'}}}'
            ws.send(jsoncommand)
        else:
            Log("ERROR: Unsupported command")
    else:
        for key in Groups.keys():
            if Groups[key]["UnitID"]==UnitID:
                ID=key
        if key!="":
            #Calculate ratio
            ratio=float(Level)/float(Devices[UnitID].sValue)
            Debug ("Updating with ratio "+str(ratio))
            for key in Clients.keys():
                if Clients[key]["GroupID"]==ID:
                    #client is part of the group, so let's update
                    Volume=(Clients[key]["percent"]*ratio)
                    if Volume>100:
                        Volume=100
                    Muted=Clients[key]["muted"]
                    jsoncommand='{"id":"'+key+'","jsonrpc":"2.0","method":"Client.SetVolume","params":{"id":"'+key+'","volume":{"muted":'+str(Clients[key]["muted"]).lower()+',"percent":'+str(Volume)+'}}}'
                    ws.send(jsoncommand)



def on_message(ws, message):
    global Clients
    try:
        Debug("received message as {}".format(message))
        data=json.loads(message)
        if "method" in data.keys():
            if data["method"]=="Server.OnUpdate":
                OnServerUpdate(data["params"]["server"])
            elif data["method"]=="Client.OnConnect" or data["method"]=="Client.OnDisconnect":
                OnClientConnectionChange(data["params"])
            elif data["method"]=="Client.OnVolumeChanged":
                Clients[data["params"]["id"]]["percent"]=data["params"]["volume"]["percent"]
                Clients[data["params"]["id"]]["muted"]=data["params"]["volume"]["muted"]
                client=Clients[data["params"]["id"]]
                UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])
                UpdateGroupVolume(client["GroupID"])
            elif data["method"]=="Client.OnNameChanged":
                OnNameChanged(data["params"])
                Debug("unsupported method")
        elif "result" in data.keys():
            if "server" in data["result"].keys():
                OnServerUpdate(data["result"]["server"])
            elif "volume" in data["result"].keys():
                if data["id"] in Clients.keys():
                    Clients[data["id"]]["percent"]=data["result"]["volume"]["percent"]
                    Clients[data["id"]]["muted"]=data["result"]["volume"]["muted"]
                    client=Clients[data["id"]]
                    UpdateDimmer(client["name"],client["UnitID"],client["muted"],client["percent"])
                    UpdateGroupVolume(client["GroupID"])
                else:
                    Log("ERROR: Unknown ID")
            else:
                Log("ERROR: Unknow RPC result")
        else:
            Log("ERROR: Unable to decode message")

    except Exception as err:
        Log("ERROR decoding message")
        Log(err)
        Domoticz.Log(traceback.format_exc())

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

    Connected=False

def on_open(ws):
    global Connected

    Connected=True
    RequestStatus()

def connect_websocket():
    global ws
    global wst

    url ="ws://"+Parameters["Address"]+":"+str(Parameters["Port"])+"/jsonrpc"
    Debug("Connecting to ["+url+"]")
    ws = websocket.WebSocketApp(url, on_message = on_message, on_error = on_error, on_close = on_close, on_open = on_open)

    wst=Thread(target=ws.run_forever)
    wst.start()

def heartbeat():
    if not Connected:
        try:
            connect_websocket()
        except Exception as err:
            Log("Connect Failed")
            Log(err)
            Domoticz.Log(traceback.format_exc())

def ReadConfig():
    global Clients
    global Groups

    try:
        if os.path.exists(Parameters["HomeFolder"]+ConfigFile):
            f = open(Parameters["HomeFolder"]+ConfigFile, "r+")
            data = json.loads(f.readline())
            f.close()
            Clients=data["Clients"]
            Groups=data["Groups"]
        else:
            Log("ERROR: file "+Parameters["HomeFolder"]+ConfigFile+" does not exist, rebuilding config")
            Clients={}
            Groups={}
    except Exception as err:
        Domoticz.Log("ERROR: Error reading file "+Parameters["HomeFolder"]+ConfigFile+": , rebuilding config")
        Domoticz.Log("ERROR: error = "+str(err))
        Domoticz.Log(traceback.format_exc())

        Clients={}
        Groups={}

def WriteConfig():
    Config={}
    Config["Clients"]=Clients
    Config["Groups"]=Groups
    f = open(Parameters["HomeFolder"]+ConfigFile, 'w')
    f.write(json.dumps(Config))
    f.close()

class BasePlugin:
    enabled = False
    global Debugging

    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        global Debugging
        Debug("onStart called")

        if Parameters["Mode1"]=="true":
            Debugging=True
        else:
            Debugging=False
        ReadConfig()
        heartbeat()

    def onStop(self):
        global ws
        global wst
        Debug("onStop called")

        ws.close() #stop the websocketapp
        wst.join()


    def onConnect(self, Connection, Status, Description):
        Debug("onConnect called")

    def onMessage(self, Connection, Data):
        Debug("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        UpdateVolume(Unit,Command,Level)

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
