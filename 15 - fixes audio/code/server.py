

import socket
import threading
import pickle

# ── config ─────────────────────────────────────────────
HOST = '0.0.0.0'
PORT = 5555
MAX_PLAYERS = 4

players = {}  # {player_id: state}
players_lock = threading.Lock()

next_id = 0
next_id_lock = threading.Lock()


# ── exact recv helper ───────────────────────────────────
def _recv_exact(conn, n):
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


# ── handle each client ──────────────────────────────────
def handle_client(conn, addr, player_id):
	print(f"[SERVER] Player {player_id} connected from {addr}")

	# send player id (no framing needed for this simple message)
	conn.sendall(pickle.dumps(player_id))

	conn.settimeout(5.0)

	try:
		while True:

			# ── RECEIVE state (length-prefixed) ─────────────
			raw_len = _recv_exact(conn, 4)
			if raw_len is None:
				break

			msg_len = int.from_bytes(raw_len, 'big')

			raw_data = _recv_exact(conn, msg_len)
			if raw_data is None:
				break

			state = pickle.loads(raw_data)

			# store player state safely
			with players_lock:
				players[player_id] = state

			# ── build snapshot of OTHER players ─────────────
			with players_lock:
				snapshot = {
					pid: s
					for pid, s in players.items()
					if pid != player_id
				}

			# ── SEND snapshot (length-prefixed) ────────────
			payload = pickle.dumps(snapshot)
			prefix = len(payload).to_bytes(4, 'big')

			try:
				conn.sendall(prefix + payload)
			except (BrokenPipeError, ConnectionResetError):
				break

	except (ConnectionResetError, OSError, socket.timeout):
		pass

	finally:
		print(f"[SERVER] Player {player_id} disconnected.")

		with players_lock:
			players.pop(player_id, None)

		conn.close()


# ── main server loop ────────────────────────────────────
def main():
	global next_id

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server.bind((HOST, PORT))
	server.listen(MAX_PLAYERS)

	print(f"[SERVER] Listening on {HOST}:{PORT}")

	try:
		while True:
			conn, addr = server.accept()

			with next_id_lock:
				pid = next_id
				next_id += 1

			thread = threading.Thread(
				target=handle_client,
				args=(conn, addr, pid),
				daemon=True
			)
			thread.start()

	except KeyboardInterrupt:
		print("\n[SERVER] Shutting down...")

	finally:
		server.close()

if __name__ == "__main__":
	main()