import socket
import threading
import pickle
 
#configs
HOST = '0.0.0.0'   # listen on all interfaces
PORT = 5555
MAX_PLAYERS = 4

 
players = {}          # { player_id: state_dict }
players_lock = threading.Lock()
next_id = 0
next_id_lock = threading.Lock()
 
 
def handle_client(conn, addr, player_id):
    print(f"[SERVER] Player {player_id} connected from {addr}")
 
    # Send the player their assigned id
    conn.sendall(pickle.dumps(player_id))
 
    conn.settimeout(5.0)
 
    try:
        while True:
            # ── receive this player's state ───────────────────────────────
            raw_len = _recv_exact(conn, 4)
            if raw_len is None:
                break
            msg_len = int.from_bytes(raw_len, 'big')
 
            raw_data = _recv_exact(conn, msg_len)
            if raw_data is None:
                break
 
            state = pickle.loads(raw_data)
 
            with players_lock:
                players[player_id] = state
 
            # ── send snapshot of every OTHER player ───────────────────────
            with players_lock:
                snapshot = {pid: s for pid, s in players.items() if pid != player_id}
 
            payload = pickle.dumps(snapshot)
            length_prefix = len(payload).to_bytes(4, 'big')
            try:
                conn.sendall(length_prefix + payload)
            except (BrokenPipeError, ConnectionResetError):
                break
 
    except (ConnectionResetError, OSError, socket.timeout):
        pass
    finally:
        print(f"[SERVER] Player {player_id} disconnected.")
        with players_lock:
            players.pop(player_id, None)
        conn.close()
 
 
def _recv_exact(conn, n):
    """Read exactly n bytes from conn; return None on disconnect."""
    buf = b''
    while len(buf) < n:
        try:
            chunk = conn.recv(n - len(buf))
        except (socket.timeout, OSError):
            return None
        if not chunk:
            return None
        buf += chunk
    return buf
 
 
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_PLAYERS)
    print(f"[SERVER] Listening on {HOST}:{PORT}  (max {MAX_PLAYERS} players)")
 
    global next_id
    try:
        while True:
            conn, addr = server.accept()
            with next_id_lock:
                pid = next_id
                next_id += 1
            t = threading.Thread(target=handle_client, args=(conn, addr, pid), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down.")
    finally:
        server.close()
 
 
if __name__ == '__main__':
    main()
