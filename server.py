# server.py
# Simple combined TCP + UDP chat server
# Python 3.8+
import socket
import threading

TCP_HOST = "0.0.0.0"
TCP_PORT = 9009
UDP_HOST = "0.0.0.0"
UDP_PORT = 9010
ENC = "utf-8"

tcp_clients = []            # list of (conn, addr)
udp_clients = set()         # set of (ip, port) known for UDP

tcp_lock = threading.Lock()
udp_lock = threading.Lock()

def broadcast_tcp(message, exclude_conn=None):
    with tcp_lock:
        for conn, addr in tcp_clients.copy():
            try:
                if conn is not exclude_conn:
                    conn.sendall(message.encode(ENC))
            except Exception:
                try:
                    conn.close()
                except:
                    pass
                tcp_clients.remove((conn, addr))

def broadcast_udp(message, exclude_addr=None, udp_sock=None):
    if udp_sock is None:
        return
    with udp_lock:
        for (ip, port) in list(udp_clients):
            if exclude_addr and (ip, port) == exclude_addr:
                continue
            try:
                udp_sock.sendto(message.encode(ENC), (ip, port))
            except Exception:
                udp_clients.discard((ip, port))

def handle_tcp_client(conn, addr, udp_sock):
    # conn: TCP socket connected to client
    print(f"[TCP] New connection from {addr}")
    with tcp_lock:
        tcp_clients.append((conn, addr))

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            text = data.decode(ENC).strip()
            # special registration: REGISTER_UDP:<port>
            if text.startswith("REGISTER_UDP:"):
                try:
                    _, port_str = text.split(":", 1)
                    port = int(port_str.strip())
                    ip = addr[0]
                    with udp_lock:
                        udp_clients.add((ip, port))
                    print(f"[UDP] Registered {ip}:{port}")
                    # acknowledge
                    conn.sendall(f"Registered UDP {ip}:{port}\n".encode(ENC))
                except Exception as e:
                    conn.sendall(f"ERR registering UDP: {e}\n".encode(ENC))
                continue

            # Normal chat message over TCP
            message = f"[TCP]{addr[0]}:{addr[1]} > {text}\n"
            print(message.strip())
            # broadcast to all TCP clients
            broadcast_tcp(message, exclude_conn=None)
            # also broadcast via UDP to known udp clients
            broadcast_udp(f"[TCP_BROADCAST]{text}", exclude_addr=None, udp_sock=udp_sock)

    except Exception as e:
        print(f"[TCP] Error with {addr}: {e}")
    finally:
        print(f"[TCP] Connection closed: {addr}")
        with tcp_lock:
            try:
                tcp_clients.remove((conn, addr))
            except ValueError:
                pass
        try:
            conn.close()
        except:
            pass

def tcp_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # We use a UDP server socket to send to clients; bind for receiving direct UDP messages too.
    udp_sock.bind((UDP_HOST, UDP_PORT))
    print(f"[UDP] UDP server bound on {UDP_HOST}:{UDP_PORT}")

    # thread: listen for UDP messages from clients
    def udp_listener():
        while True:
            try:
                data, client = udp_sock.recvfrom(4096)
                text = data.decode(ENC).strip()
                # remember client
                with udp_lock:
                    udp_clients.add(client)
                print(f"[UDP] Received from {client}: {text}")
                # broadcast the udp message to others (both UDP clients and TCP clients)
                # Send to TCP clients
                broadcast_tcp(f"[UDP]{client[0]}:{client[1]} > {text}\n")
                # Send to other UDP clients
                broadcast_udp(f"[UDP_BROADCAST]{client[0]}:{client[1]} > {text}", exclude_addr=client, udp_sock=udp_sock)
            except Exception as e:
                print("[UDP] Listener error:", e)
                continue

    threading.Thread(target=udp_listener, daemon=True).start()

    # start TCP server for chat & registration
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_sock.bind((TCP_HOST, TCP_PORT))
    tcp_sock.listen(50)
    print(f"[TCP] TCP server listening on {TCP_HOST}:{TCP_PORT}")

    try:
        while True:
            conn, addr = tcp_sock.accept()
            t = threading.Thread(target=handle_tcp_client, args=(conn, addr, udp_sock), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        tcp_sock.close()
        udp_sock.close()

if __name__ == "__main__":
    tcp_server()
