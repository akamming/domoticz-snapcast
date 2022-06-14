# Domoticz Snapcasdt pluging
#
# Author: akamming
#
"""
<plugin key="snapcast" name="Snapcast" author="akamming" version="0.0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/badaix/snapcast">
    <description>
        <h2>Snapcast plugin</h2><br/>
        Overview...
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Feature one...</li>
            <li>Feature two...</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul>
        <h3>Configuration</h3>
        Configuration options...
    </description>
    <params>
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

def Debug(txt):
    global Debugging
    if Debugging:
        Domoticz.Log("DEBUG: "+str(txt))

def Log(txt):
    Domoticz.Log(txt)

def on_message(ws, message):
    '''
        This method is invoked when ever the client
        receives any message from server
    '''
    Debug("received message as {}".format(message))
    data=json.loads(message)

def on_error(ws, error):
    '''
        This method is invoked when there is an error in connectivity
    '''
    Log("received error as {}".format(error))

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
    ws.send('{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}')

def connect_websocket():
    global ws
    global wst

    ws = websocket.WebSocketApp("ws://192.168.2.22:1780/jsonrpc",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close,
                              on_open = on_open)

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
            Log(print(err))
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
