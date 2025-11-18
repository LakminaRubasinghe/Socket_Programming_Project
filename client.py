# client.py
# Simple Tkinter chat client that can send via TCP or UDP
# Python 3.8+
import socket
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import simpledialog, messagebox

SERVER_IP_DEFAULT = "127.0.0.1"
TCP_PORT = 9009
UDP_PORT = 9010
ENC = "utf-8"

#Color themes
BG_MAIN = "#F6F8D5"
BG_FRAME = "#205781"
BG_ENTRY = "#98D2C0"
BG_BUTTON = "#4F959D"
FG_TEXT = "#F8E559"
FG_PLACEHOLDER = "#F6ECA9"
FONT_MAIN = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")


class ChatClient:
    def __init__(self, root):
        self.root = root
        root.title("Socket Chat Client (TCP & UDP)")

        frame = tk.Frame(root)
        frame.pack(padx=8, pady=8)

        ipframe = tk.Frame(frame)
        ipframe.pack(fill="x")
        tk.Label(ipframe, text="Server IP:").pack(side="left")
        self.server_ip_var = tk.StringVar(value=SERVER_IP_DEFAULT)
        tk.Entry(ipframe, textvariable=self.server_ip_var, width=18).pack(side="left")
        tk.Button(ipframe, text="Connect", command=self.connect).pack(side="left", padx=6)
        tk.Button(ipframe, text="Disconnect", command=self.disconnect).pack(side="left")

        self.chat_area = ScrolledText(frame, width=60, height=20, state="disabled")
        self.chat_area.pack(pady=6)

        msgframe = tk.Frame(frame)
        msgframe.pack(fill="x")
        self.msg_entry = tk.Entry(msgframe, width=46)
        self.msg_entry.pack(side="left", padx=(0,6))
        self.msg_entry.bind("<Return>", lambda e: self.send_tcp())

        btnframe = tk.Frame(frame)
        btnframe.pack(pady=6)
        tk.Button(btnframe, text="Send via TCP", width=15, command=self.send_tcp).pack(side="left", padx=6)
        tk.Button(btnframe, text="Send via UDP", width=15, command=self.send_udp).pack(side="left", padx=6)

        # sockets
        self.tcp_sock = None
        self.udp_sock = None
        self.running = False

    def connect(self):
        if self.tcp_sock:
            messagebox.showinfo("Info", "Already connected")
            return
        server_ip = self.server_ip_var.get().strip()
        try:
            # TCP connect
            self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_sock.connect((server_ip, TCP_PORT))
            self.running = True
            # start TCP receive thread
            threading.Thread(target=self.tcp_recv_thread, daemon=True).start()

            # UDP socket: bind to any free port and tell server our UDP port
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.bind(('', 0))  # OS picks port
            local_udp_port = self.udp_sock.getsockname()[1]
            # tell server our UDP port
            self.tcp_sock.sendall(f"REGISTER_UDP:{local_udp_port}\n".encode(ENC))
            # start udp recv thread
            threading.Thread(target=self.udp_recv_thread, daemon=True).start()

            self.append_text("[SYSTEM] Connected to server {}\n".format(server_ip))
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect: {e}")
            self.tcp_sock = None
            if self.udp_sock:
                self.udp_sock.close()
                self.udp_sock = None

    def disconnect(self):
        self.running = False
        try:
            if self.tcp_sock:
                self.tcp_sock.close()
        except:
            pass
        try:
            if self.udp_sock:
                self.udp_sock.close()
        except:
            pass
        self.tcp_sock = None
        self.udp_sock = None
        self.append_text("[SYSTEM] Disconnected\n")

    def append_text(self, text):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", text)
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def tcp_recv_thread(self):
        try:
            while self.running:
                data = self.tcp_sock.recv(4096)
                if not data:
                    break
                text = data.decode(ENC)
                self.append_text(text)
        except Exception as e:
            self.append_text(f"[SYSTEM] TCP recv error: {e}\n")
        finally:
            self.running = False
            self.append_text("[SYSTEM] TCP connection closed\n")

    def udp_recv_thread(self):
        try:
            while self.running:
                data, addr = self.udp_sock.recvfrom(4096)
                text = data.decode(ENC)
                self.append_text(f"{addr} (UDP) > {text}\n")
        except Exception as e:
            self.append_text(f"[SYSTEM] UDP recv error (likely closed): {e}\n")

    def send_tcp(self):
        text = self.msg_entry.get().strip()
        if not text or not self.tcp_sock:
            return
        try:
            self.tcp_sock.sendall((text + "\n").encode(ENC))
            self.msg_entry.delete(0, "end")
        except Exception as e:
            self.append_text(f"[SYSTEM] Failed to send TCP: {e}\n")

    def send_udp(self):
        text = self.msg_entry.get().strip()
        if not text or not self.udp_sock:
            return
        try:
            server_ip = self.server_ip_var.get().strip()
            self.udp_sock.sendto(text.encode(ENC), (server_ip, UDP_PORT))
            self.msg_entry.delete(0, "end")
            # Optionally show what we sent
            self.append_text(f"[You->UDP] {text}\n")
        except Exception as e:
            self.append_text(f"[SYSTEM] Failed to send UDP: {e}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
