# server_gui.py
import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox

# ---------------- COLORS & FONTS ----------------
WHITE = "#E0E9F6"
NAME = "#0D0D3B"
BG_FRAME = "#FFFFFF"
BG_MAIN = "#000047"
BG_ENTRY = "#A1C6EA"
BG_BUTTON = "#3E6680"
BG_BUTTON_DISCONNECT = "#9C2007"
BG_BUTTON_DISCONNECT_LIGHT = "#F87C63"
FG_TEXT = "#181818"
FG_PLACEHOLDER = "#494949"
FONT_MAIN = ("sans-serif", 11)
FONT_BOLD = ("sans-serif", 11, "bold")

# ---------------- SERVER CONFIG ----------------
TCP_HOST = "0.0.0.0"
TCP_PORT = 9009
UDP_HOST = "0.0.0.0"
UDP_PORT = 9010
ENC = "utf-8"

tcp_clients = []
udp_clients = set()
tcp_lock = threading.Lock()
udp_lock = threading.Lock()

# ---------------- SERVER GUI ----------------
class ChatServer:
    def __init__(self, root):
        self.root = root
        root.title("Server [TCP/UDP]")
        root.configure(bg=BG_MAIN)
        root.geometry("700x580")

        # MAIN WRAPPER FRAME
        frame = tk.Frame(root, bg=BG_FRAME, bd=2, relief="groove")
        frame.pack(padx=8, pady=8, fill="both", expand=True)

        # HEADER
        tk.Label(frame, text="Server Interface", font=("sans-serif", 16, "bold"),
                 fg=NAME, bg=BG_FRAME).pack(pady=8)

        # BUTTONS FRAME
        btnframe = tk.Frame(frame, bg=BG_FRAME)
        btnframe.pack(pady=6)

        self.start_btn = tk.Button(btnframe, text="Start Server", bg=BG_BUTTON, fg=WHITE,
                                   font=FONT_BOLD, width=15, relief="flat", command=self.start_server)
        self.start_btn.pack(side="left", padx=6)

        self.stop_btn = tk.Button(btnframe, text="Stop Server", bg=BG_BUTTON_DISCONNECT, fg=WHITE,
                                  font=FONT_BOLD, width=15, relief="flat", command=self.stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        # LOG AREA
        self.log_area = ScrolledText(frame, width=70, height=25, bg=BG_ENTRY,
                                     fg=FG_TEXT, font=FONT_MAIN, state="disabled", relief="flat",
                                     insertbackground=FG_TEXT)
        self.log_area.pack(pady=10, padx=5)

        # SERVER THREAD CONTROL
        self.running = False
        self.tcp_sock = None
        self.udp_sock = None

    # ---------------- LOG HELPER ----------------
    def log(self, text):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", text + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    # ---------------- SERVER CONTROL ----------------
    def start_server(self):
        if self.running:
            messagebox.showinfo("Info", "Server already running")
            return

        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        threading.Thread(target=self.server_thread, daemon=True).start()
        self.log("[SYSTEM] Server starting...")

    def stop_server(self):
        self.running = False
        try:
            if self.tcp_sock:
                self.tcp_sock.close()
            if self.udp_sock:
                self.udp_sock.close()
        except:
            pass
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log("[SYSTEM] Server stopped")

    # ---------------- SERVER THREAD ----------------
    def server_thread(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.udp_sock.bind((UDP_HOST, UDP_PORT))
        self.log(f"[UDP] Listening on {UDP_HOST}:{UDP_PORT}")

        def udp_listener():
            while self.running:
                try:
                    data, client = self.udp_sock.recvfrom(4096)
                    text = data.decode(ENC).strip()
                    with udp_lock:
                        udp_clients.add(client)

                    self.log(f"[UDP]{client} > {text}\n")

                    self.broadcast_udp(f"[UDP_BROADCAST]{client} > {text}\n", exclude=client)
                    self.broadcast_tcp(f"[UDP]{client} > {text}\n")
                except:
                    continue

        threading.Thread(target=udp_listener, daemon=True).start()

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_sock.bind((TCP_HOST, TCP_PORT))
        self.tcp_sock.listen(50)
        self.log(f"[TCP] Listening on {TCP_HOST}:{TCP_PORT}\n")

        while self.running:
            try:
                conn, addr = self.tcp_sock.accept()
                threading.Thread(target=self.handle_tcp_client, args=(conn, addr), daemon=True).start()
            except:
                break

    # ---------------- BROADCAST ----------------
    def broadcast_tcp(self, message, exclude_conn=None):
        with tcp_lock:
            for conn, addr in tcp_clients.copy():
                try:
                    if conn != exclude_conn:
                        conn.sendall(message.encode(ENC))
                except:
                    tcp_clients.remove((conn, addr))

    def broadcast_udp(self, message, exclude=None):
        with udp_lock:
            for client in list(udp_clients):
                if client != exclude:
                    try:
                        self.udp_sock.sendto(message.encode(ENC), client)
                    except:
                        udp_clients.discard(client)

    # ---------------- TCP CLIENT HANDLER ----------------
    def handle_tcp_client(self, conn, addr):
        self.log(f"[TCP] New connection from {addr}")
        with tcp_lock:
            tcp_clients.append((conn, addr))
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                text = data.decode(ENC).strip()
                if text.startswith("REGISTER_UDP:"):
                    try:
                        _, port_str = text.split(":", 1)
                        port = int(port_str.strip())
                        ip = addr[0]
                        with udp_lock:
                            udp_clients.add((ip, port))
                        conn.sendall(f"Registered UDP {ip}:{port}\n".encode(ENC))
                        self.log(f"[UDP] Registered {ip}:{port}\n")
                    except Exception as e:
                        conn.sendall(f"ERR registering UDP: {e}\n".encode(ENC))
                    continue
                # Broadcast
                msg = f"[TCP]{addr} > {text}\n"
                self.log(msg)
                self.broadcast_tcp(msg)
                self.broadcast_udp(f"[TCP_BROADCAST]{text}\n")
        except:
            pass
        finally:
            with tcp_lock:
                try:
                    tcp_clients.remove((conn, addr))
                except:
                    pass
            try:
                conn.close()
            except:
                pass
            self.log(f"[TCP] Connection closed: {addr}\n")

# ---------------- RUN GUI ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatServer(root)
    root.mainloop()
