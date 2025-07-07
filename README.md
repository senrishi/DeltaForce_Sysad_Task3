# **TASK 3A** 
## <mark style="background: #BBFABBA6;"><span style="color:rgb(0, 0, 0)">Not Discord V2</span></mark>

Few things still in WIP
-  Incorrect passwords should re prompt the user 
-  Better time stats tracking
-  More cleaner look in chats
-  Option to display chat history
-  Haven't created dockerhub account yet, so the automated 
	workflow is broken for now

# **TASK 3B**

## <mark style="background: #FF5582A6;"><span style="color:rgb(0, 0, 0)">Z3 Solver</span> </mark>

-  Length reduced by, assuming that the last character is a null terminator 
- Result:
- i # &l"4!0[t"0!G Qj`,8AW(I(oq

## <mark style="background: #ADCCFFA6;"><span style="color:rgb(0, 0, 0)">JWT Web App</span> </mark>

- Used Flask and HTML to create the login page. 
- "none" algorithm used.
- Exploit script sends normal user credentials to the login page to retrieve the token. The token is then modified to change the value of 'isAdmin' to True. When this new token is sent to the web app, the flag is returned. 

# <mark style="background: #FFB86CA6;"><span style="color:rgb(0, 0, 0)">Forensics</span> </mark>

- 2 files were split into chunks
	- Image chunks : Used steghide to embed a message in the clean.jpeg file. Password to extract: delta
	- Text file chunks : simple text message 
- The chunks were locally transferred using a python file server and curl (to get http traffic)
- tcpdump was used to capture and store traffic in fragments.pcap. Only traffic from port 8000 (the python web server) was specified, to minimize the number of requests captured in the pcap file. 