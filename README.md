# domoticz-snapcast
python snapcast plugin for domoticz

## Description
Creates dimmer switches in domoticz for every snapclient connected to the snapserver. Using the dimmer the volume can be set. With on/off muting can be set.

## Installation steps
- navigate to your domoticz/plugins dir
- enter command: sudo -u <domoticz user> git clone https://github.com/akamming/domoticz-snapcast
- enter command: sudo pip install websocket-client
- restart domoticz
- select "snapcast" hardware in your domoticz hardware screen 
- configure the ip adress and port (on which json interface is available: usually 1780) of your snapcast server
- clock 'add' 
- if all is working well you should now see a dimmer switch for every snapcast client which is connected to your snapcast server, as well for every configured group in your snapcast server
  
## bug reporting
This plugin is in early stage of development, might contain bugs. If so: Pls report issues in the issues screen. At least report the following
1. The current behaviour of which you think is is a bug
2. the behaviour houw it should work 
3. Steps how to reproduce
4. Information about your setup: Both domoticz and snapcast
  
## Development
Feel free to contribute, as long as you make PR's so i can integrate..
