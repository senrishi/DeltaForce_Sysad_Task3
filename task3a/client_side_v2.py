import socket, threading
import hashlib
import sys

HOST = '127.0.0.1'
PORT = 5005

MESSAGE_DELIMITER = "/end/"

def send_message(sock,message):
    try:
        fm=message + MESSAGE_DELIMITER
        sock.sendall(fm.encode('utf-8'))
    except (socket.error) as e:
        print(f"Error sending message: {e}")
        sys.exit(1)

def receive_message(sock):
    buffer = ""
    while MESSAGE_DELIMITER not in buffer:
        try:
            chunck = sock.recv(1024)
            if not chunck:
                return None
            buffer += chunck.decode('utf-8', errors='ignore')
        except (socket.error) as e:
            return None
        except UnicodeDecodeError:
            return None

    message, buffer = buffer.split(MESSAGE_DELIMITER,1)
    return message.strip()


def receive_message_room(sock, username, name):
    while True:
        try:
            response = receive_message(sock)
            if response is None:
                print("Server disconnected or error occurred.")
                break

            chunk = response.split(":", 1)
            command = chunk[0]
            message_content = chunk[1] if len(chunk) > 1 else ""

            if command == "STATS":
                print(f"\n{message_content}")
                sys.stdout.flush()
            elif command == "QUIT_ROOM":
                print(f"\n{message_content} has left the chatroom.\n")
                sys.stdout.flush()
            elif command == "MESSAGE":
                msg_parts = message_content.split(':', 1)
                sender = msg_parts[0]
                content = msg_parts[1] if len(msg_parts) > 1 else ""
                print(f"\r<{sender}@{name}>  {content}\n")
                sys.stdout.flush()
            elif command == "ERROR":
                print(f"\nError from server: {message_content}\n")
            elif command == "DISCONNECT":
                print("\nDisconnected from server. Goodbye!\n")
                break

            elif command == "JOIN": # Handle JOIN_SUCCESS/FAILED messages here
                print(f"\n{message_content}\n")
            elif command == "NEW_ROOM": # Handle NEW_ROOM_SUCCESS/FAILED/EXISTS here
                print(f"\n{message_content}\n")
            elif command == "GET_ROOMS": # Handle GET_ROOMS messages here
                print(f"\n{message_content}\n")
            else:
                print(f"\nUnknown message type from server: {response}\n")
        except Exception as e:
            print(f"\nAn error occurred in receive_message_room: {e}\n")
            break

def messages(client_socket, username, name):

    try:
        send_message(client_socket,f"JOIN:{name}")
        response = receive_message(client_socket)

        chunk = response.split(":", 1)
        command = chunk[0]
        message_body = chunk[1] if len(chunk) > 1 else ""

        if command == "JOIN" and message_body.startswith("SUCCESS"):

            receive_thread = threading.Thread(target=receive_message_room, args=(client_socket, username, name))
            receive_thread.daemon = True
            receive_thread.start()

            print(f"You have successfully joined the chatroom {name}.")
            print("Type /stat to get room statistics, /q to exit the room, or /disconnect to log out.")
            print("\n")
            while True:
                message = input(f"<{username}@{name}>  ")
                if message == "/q":
                    send_message(client_socket, f"QUIT_ROOM:{name}")
                    break
                elif message == "/disconnect":
                    send_message(client_socket, "DISCONNECT")
                    break
                elif message == "/stat":
                    send_message(client_socket, "STATS")
                else:
                    send_message(client_socket, f"MESSAGE:{name}:{username}:{message}")

        else:
            print(f"Failed to join chatroom: {message_body}")

    except Exception as e:
        print(f"An error occurred in messages function: {e}")
    finally:
        pass

def create_chatroom(client_socket, username):

    name = ""
    while True:
        temp = input("\nEnter the name of your glorious new chatroom :")
        send_message(client_socket, f"NEW_ROOM:{temp}")
        response = receive_message(client_socket)

        chunk = response.split(":", 1)
        command = chunk[0]
        message_body = chunk[1] if len(chunk) > 1 else ""

        if command == "NEW_ROOM" and message_body == "EXISTS":
            print("Room already exists, please try again.")
            continue
        elif command == "NEW_ROOM" and message_body == "SUCCESS":
            print("Your new chatroom has been successfully created!")
            print("Entering your chatroom...")
            name = temp
            messages(client_socket=client_socket, username=username, name=name)
            return
        else:
            print(f"Error creating chatroom: {response}")
            return


def chatroom(client_socket, username):
    print(f"\nA wild {username} appears!")
    print("Choose/create a chatroom:")

    send_message(client_socket,"GET_ROOMS")
    response = receive_message(client_socket)

    if response is None:
        print("No response from server. Connection lost.")
        client_socket.close()
        return

    chunk = response.split(":", 1)
    command = chunk[0]
    room_list_str = chunk[1] if len(chunk) > 1 else ""

    available_rooms = []
    if command == "GET_ROOMS" and room_list_str.startswith("SUCCESS:"):
        actual_list = room_list_str.split("SUCCESS:", 1)[1]
        if actual_list == "No rooms available.":
            print(actual_list)
        else:
            available_rooms = actual_list.split(":")
            print("Available Rooms:")
            for room in available_rooms:
                print(f"- {room}")
    else:
        print(f"Error getting room list: {response}")

    print()

    while True:
        choice = input("Enter the name of the room you wish to join, or type /n to create a new chatroom: ")
        if choice == "/n":
            create_chatroom(client_socket, username)
            return
        elif choice in available_rooms:
            messages(client_socket=client_socket, username=username, name=choice)
            return
        else:
            print("Invalid chatroom name or command. Please try again.")

def register():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST,PORT))

    username = input("Enter your username: ")
    password = input("Enter your password: ")
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    send_message(client_socket, f"REGISTER:{username}:{hashed_password}")
    response = receive_message(client_socket)

    chunk = response.split(":", 1)
    command = chunk[0]
    message_body = chunk[1] if len(chunk) > 1 else ""

    if command == "REGISTER" and message_body == "SUCCESS":
        print("Registration successful! Moving on to the chatrooms...")
        chatroom(client_socket,username)
    elif command == "REGISTER" and message_body == "FAILED:USERNAME_TAKEN":
        print("Username already taken. Please choose a different one.")
        prompt_register()
    else:
        print(f"Registration failed: {response}")
        client_socket.close()


def prompt_register():
    while True:
        choice = input("Would you like to register? (y/n): ")
        if choice.lower() == 'y':
            register()
            return
        elif choice.lower() == 'n':
            print("Thank you for trying out NotDiscord. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter 'y' or 'n'.")

def login():

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    username = input("Enter your username: ")
    password = input("Enter your password: ")
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    send_message(client_socket, f"LOGIN:{username}:{hashed_password}")
    response = receive_message(client_socket)

    if response is None:
        print("Invalid response or server disconnected.")
        client_socket.close()
        return

    chunk = response.split(":", 1)
    command = chunk[0]
    message_body = chunk[1] if len(chunk) > 1 else ""

    if command == "LOGIN" and message_body == "SUCCESS":
        print("Login successful!")
        chatroom(client_socket, username)
    elif command == "LOGIN" and message_body == "ALREADY_LOGGED_IN":
        print("You are already logged in.")
        client_socket.close()
    else:
        print(f"Login failed: {message_body}")
        print("Please try logging in again by restarting the script or registering a new user.")
        print("Redirecting to registration page...")
        client_socket.close()
        prompt_register()



if __name__ == "__main__":
    print("Welcome to NotDiscordV2")
    print("\n---------------------\n")
    sys.stdout.flush()
    login()
