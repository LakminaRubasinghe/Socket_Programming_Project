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
FONT_MAIN = ("sans-serif ", 11)
FONT_BOLD = ("sans-serif ", 11, "bold")


class ChatClient:
    def __init__(self, root):
        self.root = root
        root.title("Message Sharing (TCP & UDP)")
        root.configure(bg=BG_MAIN)
        root.geometry("600x540")

        # ---------- MAIN WRAPPER ----------
        frame = tk.Frame(root, bg=BG_FRAME, bd=2, relief="groove")
        frame.pack(padx=8, pady=8, fill="both", expand=True)

        # ---------- HEADER ----------
        tk.Label(
            frame,
            text="Client Interface",
            font=("Segoe UI", 20, "bold"),
            fg=NAME,
            bg=BG_FRAME
        ).pack(pady=8)

        # ---------- IP + CONNECT ----------
        ipframe = tk.Frame(frame, bg=BG_FRAME)
        ipframe.pack(anchor="center" , pady=(5, 10))
        

        tk.Label(ipframe, text="Server IP:", fg=FG_TEXT, bg=BG_FRAME, font=FONT_MAIN).pack(side="left")

        self.server_ip_var = tk.StringVar(value=SERVER_IP_DEFAULT)

        tk.Entry(
            ipframe, 
            textvariable=self.server_ip_var, 
            width=18,
            font=FONT_MAIN,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            relief="flat",
            insertbackground=WHITE
        ).pack(side="left", padx=8)
        
        btn_connect = tk.Button(
            ipframe,
            text="Connect",
            command=self.connect,
            bg=BG_BUTTON,
            fg="white",
            relief="flat",
            font=FONT_BOLD,
            width=10
            )
        btn_connect.pack(side="left", padx=6)

        def on_enter(e):
            btn_connect.config(bg=BG_ENTRY)  # hover color

        def on_leave(e):
            btn_connect.config(bg=BG_BUTTON)  # original color

        btn_connect.bind("<Enter>", on_enter)
        btn_connect.bind("<Leave>", on_leave)
        
        btn_disconnect = tk.Button(
            ipframe,
            text="Disconnect",
            command=self.disconnect,
            bg=BG_BUTTON_DISCONNECT,
            fg="white",
            relief="flat",
            font=FONT_BOLD,
            width=10
            )
        btn_disconnect.pack(side="left", padx=6)

        def on_enter(e):
            btn_disconnect.config(bg=BG_BUTTON_DISCONNECT_LIGHT)  # hover color

        def on_leave(e):
            btn_disconnect.config(bg=BG_BUTTON_DISCONNECT)  # original color

        btn_disconnect.bind("<Enter>", on_enter)
        btn_disconnect.bind("<Leave>", on_leave)

        # ---------- CHAT AREA ----------
        self.chat_area = ScrolledText(
            frame,
            width=60,
            height=18,
            state="disabled",
            bg=BG_ENTRY,
            fg=FG_TEXT,
            font=(FONT_MAIN, 11),
            relief="flat",
            insertbackground=FG_TEXT
        )
        self.chat_area.pack(pady=10, padx=5)

        # ---------- MESSAGE INPUT ----------        
        msgframe = tk.Frame(frame, bg=BG_FRAME)
        msgframe.pack(anchor="center" )

        self.msg_entry = tk.Entry(
            msgframe,
            width=45,
            font=FONT_MAIN,
            bg=BG_ENTRY,
            fg=FG_TEXT,
            relief="flat",
            insertbackground=WHITE)
        
        self.msg_entry.pack(side="left", padx=(0,6), pady=5, anchor="center" )
        self.msg_entry.bind("<Return>", lambda e: self.send_tcp())

        placeholder = "Type your message here..."
        self.msg_entry.insert(0, placeholder)
        self.msg_entry.config(fg=FG_PLACEHOLDER)

        def on_focus_in(event):
            if self.msg_entry.get() == placeholder:
                self.msg_entry.delete(0, "end")
                self.msg_entry.config(fg=FG_TEXT)

        def on_focus_out(event):
            if not self.msg_entry.get():
                self.msg_entry.insert(0, placeholder)
                self.msg_entry.config(fg="#999999")

        self.msg_entry.bind("<FocusIn>", on_focus_in)
        self.msg_entry.bind("<FocusOut>", on_focus_out)

        # ---------- BUTTONS (TCP/UDP) ----------
        btnframe = tk.Frame(frame, bg=BG_FRAME)
        btnframe.pack(pady=6, anchor="center" )

        btn_tcp = tk.Button(
            btnframe,
            text="Send via TCP",
            command=self.send_tcp,
            bg=BG_BUTTON,
            fg=WHITE,
            relief="flat",
            font=FONT_BOLD,
            width=15
        )
        btn_tcp.pack(side="left", padx=6)

        def on_enter(e):
            btn_tcp.config(bg=BG_ENTRY)  # hover color

        def on_leave(e):
            btn_tcp.config(bg=BG_BUTTON)  # original color

        btn_tcp.bind("<Enter>", on_enter)
        btn_tcp.bind("<Leave>", on_leave)

        btn_udp = tk.Button(
            btnframe,
            text="Send via UDP",
            command=self.send_udp,
            bg=BG_BUTTON,
            fg=WHITE,
            relief="flat",
            font=FONT_BOLD,
            width=15
        )
        btn_udp.pack(side="left", padx=6)

        def on_enter(e):
            btn_udp.config(bg=BG_ENTRY)  # hover color

        def on_leave(e):
            btn_udp.config(bg=BG_BUTTON)  # original color

        btn_udp.bind("<Enter>", on_enter)
        btn_udp.bind("<Leave>", on_leave)

        # sockets
        self.tcp_sock = None
        self.udp_sock = None
        self.running = False

    # ------------------ CONNECTION ---------------------
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

    # ------------------ DISCONNECT ---------------------
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

    # ------------------ UI HELPERS ---------------------
    def append_text(self, text):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", text)
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    # ------------------ THREADS ------------------------
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
                self.append_text(f"\n{addr} (UDP) > {text}\n")
        except Exception as e:
            self.append_text(f"[SYSTEM] UDP recv error (likely closed): {e}\n")

    # ------------------ SEND MSGS ------------------------
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
