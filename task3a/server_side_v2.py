import socket, threading
import hashlib
import psycopg2
import datetime, time
import os
import math

HOST = "localhost"
PORT = 5005

DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "discordv2"
DB_USER = "postgresql"
DB_PASSWORD = "DB_PASSWORD"

def db():
    db_postgresql = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return db_postgresql

def db_setup():
    db_postgresql = db()
    cur = db_postgresql.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(128) NOT NULL,
        active_time INT DEFAULT 0,
        message_count INT DEFAULT 0
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS schatt (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        message VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS chatrooms (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE
    );""")

    db_postgresql.commit()
    db_postgresql.close()


MESSAGE_DELIMITER="/end/"
active_connections={}
active_chatrooms_registry = {}


def send_message(sock,message):
    try:
        fm=message + MESSAGE_DELIMITER
        sock.sendall(fm.encode('utf-8'))
    except (socket.error) as e:
        pass

def receive_message(sock):
    msg = ""
    buffer = ""
    while MESSAGE_DELIMITER not in buffer:
        try:
            chunck = sock.recv(1024)
            if not chunck:
                return None
            buffer += chunck.decode('utf-8')
        except (socket.error,) as e:
            return None
        except UnicodeDecodeError:
            return None

    message, buffer = buffer.split(MESSAGE_DELIMITER,1)
    return message.strip()


def login(client_socket,client_address,username,hash):
    conn = None
    cur = None
    try:
        conn = db()
        cur = conn.cursor()
        if username in active_connections:
            send_message(client_socket, "LOGIN:ALREADY_LOGGED_IN")
            return False
        else:
            cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and user[0] == hash:
                send_message(client_socket, "LOGIN:SUCCESS")
                return True
            else:
                send_message(client_socket, "LOGIN:FAILED:Invalid credentials")
                return False
    except Exception as e:
        send_message(client_socket, "LOGIN:FAILED:Server error")
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()

def register(client_socket,client_address,username,hash):
    conn = None
    cur = None
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            send_message(client_socket, "REGISTER:FAILED:USERNAME_TAKEN")
            return False
        else:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hash))
            conn.commit()
            send_message(client_socket, "REGISTER:SUCCESS")
            return True
    except Exception as e:
        send_message(client_socket, "REGISTER:FAILED:Server error")
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()


def get_rooms(client_socket, client_address):
    conn = None
    cur = None
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM chatrooms")
        rooms = [row[0] for row in cur.fetchall()]
        if rooms:
            send_message(client_socket, f"GET_ROOMS:SUCCESS:{':'.join(rooms)}")
        else:
            send_message(client_socket, "GET_ROOMS:SUCCESS:No rooms available.")
    except Exception as e:
        send_message(client_socket, "GET_ROOMS:FAILED:Server error")
    finally:
        if cur: cur.close()
        if conn: conn.close()


def new_room(client_socket, client_address, room_name):
    conn = None
    cur = None
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM chatrooms WHERE name = %s", (room_name,))
        room_data = cur.fetchone()

        if room_data:
            send_message(client_socket, "NEW_ROOM:EXISTS")
            return False
        else:
            cur.execute("INSERT INTO chatrooms (name) VALUES (%s) RETURNING id;", (room_name,))
            new_room_id = cur.fetchone()[0]
            conn.commit()
            chatroom_obj = ChatRoom(new_room_id, room_name)
            active_chatrooms_registry[room_name] = chatroom_obj

            send_message(client_socket, "NEW_ROOM:SUCCESS")
            return True

    except psycopg2.IntegrityError:
        conn.rollback()
        send_message(client_socket, "NEW_ROOM:FAILED:Integrity error")
        return False
    except Exception as e:
        conn.rollback()
        send_message(client_socket, "NEW_ROOM:FAILED:Server error")
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()

class ChatRoom:
    def __init__(self, room_id, name):
        self.id = room_id
        self.name = name
        self.members = {}

    def add_member(self, username, client_socket):
        if username not in self.members:
            self.members[username] = client_socket
            return True
        return False

    def remove_member(self, username):
        if username in self.members:
            del self.members[username]
            return True
        return False

    def get_member_sockets(self):
        return list(self.members.values())

def join_room(client_socket, client_address, room_name, username):
    conn = None
    cur = None
    try:
        if room_name not in active_chatrooms_registry:
            conn = db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM chatrooms WHERE name = %s", (room_name,))
            room_data = cur.fetchone()
            if room_data:
                room_id = room_data[0]
                active_chatrooms_registry[room_name] = ChatRoom(room_id, room_name)
            else:
                send_message(client_socket, f"JOIN:FAILED:Room '{room_name}' does not exist.")
                return None

        target_room_obj = active_chatrooms_registry[room_name]

        if target_room_obj.add_member(username, client_socket):
            send_message(client_socket,f"JOIN:SUCCESS:{room_name}")
            for member_sock in target_room_obj.get_member_sockets():
                if member_sock != client_socket:
                    send_message(member_sock, f"MESSAGE:SERVER:{username} has joined the room.")
            return target_room_obj.name
        else:
            send_message(client_socket,"JOIN:FAILED:ALREADY_JOINED")
            return None
    except Exception as e:
        send_message(client_socket, "JOIN:FAILED:Server error")
        return None
    finally:
        if cur: cur.close()
        if conn: conn.close()

def handle_chat_message(sender_socket, room_name, sender_username, message_content):
    if room_name in active_chatrooms_registry:
        room = active_chatrooms_registry[room_name]
        msg = f"MESSAGE:{sender_username}:{message_content}"

        for member_socket in room.get_member_sockets():
            if member_socket != sender_socket:
                send_message(member_socket, msg)
    else:
        send_message(sender_socket, f"ERROR:ROOM_NOT_FOUND:{room_name}")


def stats(client_socket, client_address, username):
    conn = None
    cur = None
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT username, active_time FROM users ORDER BY active_time DESC")
        time_lb = cur.fetchall()
        cur.execute("SELECT username, message_count FROM users ORDER BY message_count DESC")
        msg_lb = cur.fetchall()

        time_lb_arr = ["Active time leaderboard:"]
        if time_lb:
            for i, (user, u_time) in enumerate(time_lb):
                time_lb_arr.append(f"{i+1}. {user} = {u_time} seconds")
        else:
            time_lb_arr.append("N/A")

        msg_lb_arr = ["Message count leaderboard:"]
        if msg_lb:
            for i, (user, count) in enumerate(msg_lb):
                msg_lb_arr.append(f"{i+1}. {user} = {count} messages")
        else:
            msg_lb_arr.append("N/A")

        full_leaderboard_output = "\n".join(time_lb_arr) + "\n\n" + "\n".join(msg_lb_arr)
        send_message(client_socket, f"STATS:SUCCESS:{full_leaderboard_output}")
    except Exception as e:
        send_message(client_socket, f"STATS:FAILED:Error fetching stats: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

def handle_quit_command(client_socket, client_address, username, current_room):
    if current_room and current_room in active_chatrooms_registry:
        room_obj = active_chatrooms_registry[current_room]

        if room_obj.remove_member(username):
            pass
        if not room_obj.members:
            del active_chatrooms_registry[current_room]

    if username in active_connections:
        del active_connections[username]
    elif client_address in active_connections:
        del active_connections[client_address]


def handle_client(client_socket, client_address):
    username = None
    current_room = None
    start_time = None
    message_count = 0

    try:
        active_connections[client_address] = client_socket

        while username is None:
            message = receive_message(client_socket)
            if message is None:
                break

            chunk = message.split(':', 2)
            if len(chunk) < 1:
                send_message(client_socket, "ERROR:INVALID_FORMAT")
                continue

            command = chunk[0]

            if command == "LOGIN":
                if len(chunk) < 3:
                    send_message(client_socket, "ERROR:INVALID_LOGIN_FORMAT")
                    continue
                temp_username = chunk[1]
                hash_pw = chunk[2]
                login_result = login(client_socket, client_address,temp_username, hash_pw)
                if login_result:
                    start_time = time.time()
                    username = temp_username
                    active_connections[username] = active_connections.pop(client_address)

            elif command == "REGISTER":
                if len(chunk) < 3:
                    send_message(client_socket, "ERROR:INVALID_REGISTER_FORMAT")
                    continue
                temp_username = chunk[1]
                hash_pw = chunk[2]
                register_result = register(client_socket, client_address, temp_username, hash_pw)
                if register_result:
                    start_time = time.time()
                    username = temp_username
                    active_connections[username] = active_connections.pop(client_address)
            else:
                send_message(client_socket, "ERROR:AUTH_REQUIRED")

        if username is None:
            return

        while True:
            msg = receive_message(client_socket)
            if msg is None:
                break

            chunks = msg.split(':', 3)
            if len(chunks) < 1:
                send_message(client_socket, "ERROR:INVALID_COMMAND_FORMAT")
                continue

            command = chunks[0]

            if command == "GET_ROOMS":
                get_rooms(client_socket, client_address)

            elif command == "NEW_ROOM":
                if len(chunks) < 2:
                    send_message(client_socket, "ERROR:INVALID_NEW_ROOM_FORMAT");
                    continue
                nroom = chunks[1]
                new_room_success = new_room(client_socket, client_address, nroom)
                if new_room_success:
                    current_room = nroom

            elif command == "JOIN":
                if len(chunks) < 2:
                    send_message(client_socket, "ERROR:INVALID_JOIN_FORMAT");
                    continue
                room_name = chunks[1]
                joined_room_name = join_room(client_socket, client_address, room_name, username)
                if joined_room_name:
                    current_room = joined_room_name

            elif command == "QUIT_ROOM":
                if len(chunks) < 2:
                    send_message(client_socket, "ERROR:INVALID_QUIT_ROOM_FORMAT")
                    continue
                room_to_leave = chunks[1]
                if room_to_leave == current_room:

                    if current_room in active_chatrooms_registry:
                        room_obj = active_chatrooms_registry[current_room]

                        if room_obj.remove_member(username):
                            send_message(client_socket, f"QUIT_ROOM:SUCCESS:{room_to_leave}")
                            for member_sock in room_obj.get_member_sockets():
                                send_message(member_sock, f"MESSAGE:SERVER:{username} has left the room.")
                            current_room = None

                        else:
                            send_message(client_socket, f"QUIT_ROOM:FAILED:Not member of {room_to_leave}.")


            elif command =="STATS":
                stats(client_socket, client_address, username)

            elif command == "MESSAGE":
                if len(chunks) < 4:
                    send_message(client_socket, "ERROR:INVALID_MESSAGE_FORMAT")
                    continue
                room_name = chunks[1]
                sender_username = chunks[2]
                message_content = chunks[3]

                if room_name != current_room:
                    send_message(client_socket, f"ERROR:NOT_IN_ROOM:{room_name}")
                    continue

                handle_chat_message(client_socket, room_name, sender_username, message_content)
                message_count += 1

                conn = None
                cur = None
                try:
                    conn = db()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO schatt (username, message) VALUES (%s, %s)", (sender_username, message_content))
                        cur.execute("UPDATE users SET message_count = message_count + 1 WHERE username = %s", (username,))
                        conn.commit()
                    else:
                        pass
                except Exception as e:
                    pass
                finally:
                    if cur: cur.close()
                    if conn: conn.close()

            else:
                send_message(client_socket, "ERROR:UNKNOWN_COMMAND")

    except (socket.error) as e:
        pass
    except Exception as e:
        pass

    finally:
        if username and start_time:
            conn = None
            cur = None
            try:
                conn = db()
                if conn:
                    cur = conn.cursor()
                    session_duration_seconds = int(time.time() - start_time)
                    cur.execute("UPDATE users SET active_time = active_time + %s WHERE username = %s",(session_duration_seconds, username))
                    conn.commit()
                else:
                    pass
            except Exception as e:
                pass
            finally:
                if cur: cur.close()
                if conn: conn.close()

        if username in active_connections:
            del active_connections[username]
        elif client_address in active_connections:
            del active_connections[client_address]

        if current_room and current_room in active_chatrooms_registry:
            room_obj = active_chatrooms_registry[current_room]
            if username and room_obj.remove_member(username):
                for member_sock in room_obj.get_member_sockets():
                    send_message(member_sock, f"MESSAGE:SERVER:{username} has left the room.")
                if not room_obj.members:
                    del active_chatrooms_registry[current_room]

        try:
            if client_socket and client_socket.fileno() != -1:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
        except (socket.error) as e:
            pass

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server started on {HOST}:{PORT}")
    db_run = db_setup()
    while True:
            client_socket, client_address = server_socket.accept()
            print(f"Accepted connection from {client_address}")
            client_handler = threading.Thread(
                target = handle_client,
                args=(client_socket, client_address)
            )
            client_handler.start()

if __name__ == "__main__":
    start_server()
