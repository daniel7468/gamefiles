import socket
import pickle
import threading
import pygame
import sys
from settings import *
from level import Level
 
#network config
SERVER_IP   = '192.0.0.2'
SERVER_PORT = 5555

 
 
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
 
 
class NetworkClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(5.0)
 
        raw = _recv_exact(self.sock, 4096)
        self.player_id = pickle.loads(raw)

        print(f"[CLIENT] Assigned player id: {self.player_id}")
 
        self.other_players = {}
        self._lock = threading.Lock()
        self._my_state = None
        self._running = True
 
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
 
    def send_state(self, state: dict):
        with self._lock:
            self._my_state = state
 
    def get_others(self) -> dict:
        with self._lock:
            return dict(self.other_players)
 
    def _loop(self):
        while self._running:
            with self._lock:
                state = self._my_state
 
            if state is not None:
                payload = pickle.dumps(state)
                prefix  = len(payload).to_bytes(4, 'big')
                try:
                    self.sock.sendall(prefix + payload)
                except OSError:
                    break
 
            raw_len = _recv_exact(self.sock, 4)
            if raw_len is None:
                break
            msg_len = int.from_bytes(raw_len, 'big')
 
            raw_data = _recv_exact(self.sock, msg_len)
            if raw_data is None:
                break
 
            snapshot = pickle.loads(raw_data)
            with self._lock:
                self.other_players = snapshot
 
        self._running = False
 
    def stop(self):
        self._running = False
        self.sock.close()
 
 
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGTH))
        pygame.display.set_caption('Larpers Simulator')
        self.clock  = pygame.time.Clock()
 
       #state opf menus
        self.state     = "menu"
        self.level     = None
        self.net       = None
        self.error_msg = ""
 
        self.main_sound = pygame.mixer.Sound('../audio/main.ogg')
        self.main_sound.set_volume(0.5)
        self.main_sound.play(loops=-1)
 
        self.font_title  = pygame.font.SysFont("arial", 80)
        self.font_button = pygame.font.SysFont("arial", 40)
        self.font_small  = pygame.font.SysFont("arial", 26)
 
    
    def _draw_button(self, rect, label, hover_color="gray", base_color="darkgray"):
        mouse = pygame.mouse.get_pos()
        color = hover_color if rect.collidepoint(mouse) else base_color
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, "white", rect, 2, border_radius=8)
        text = self.font_button.render(label, True, "white")
        self.screen.blit(text, text.get_rect(center=rect.center))
        return rect.collidepoint(mouse)
 
    
    def draw_menu(self):
        self.screen.fill((20, 20, 40))
 
        title = self.font_title.render("LARPERS SIMULATOR", True, "white")
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGTH // 4)))
 
        cx = WIDTH // 2
        solo_rect  = pygame.Rect(cx - 150, HEIGTH // 2 - 20,  300, 60)
        multi_rect = pygame.Rect(cx - 150, HEIGTH // 2 + 60,  300, 60)
        quit_rect  = pygame.Rect(cx - 150, HEIGTH // 2 + 150, 300, 60)
 
        solo_hovered  = self._draw_button(solo_rect,  "SINGLE PLAYER")
        multi_hovered = self._draw_button(multi_rect, "MULTIPLAYER")
        quit_hovered  = self._draw_button(quit_rect,  "QUIT", "firebrick", "darkred")
 
        clicked = pygame.mouse.get_pressed()[0]
        if clicked:
            if solo_hovered:
                self._start_singleplayer()
            elif multi_hovered:
                self._connect_and_start()
            elif quit_hovered:
                self._shutdown()
 
    def draw_error(self):
        self.screen.fill((40, 10, 10))
        msg1 = self.font_button.render("Could not connect to server!", True, "red")
        msg2 = self.font_small.render(self.error_msg, True, "white")
        msg3 = self.font_small.render("Press ESC to return to menu", True, (180, 180, 180))
        self.screen.blit(msg1, msg1.get_rect(center=(WIDTH // 2, HEIGTH // 2 - 60)))
        self.screen.blit(msg2, msg2.get_rect(center=(WIDTH // 2, HEIGTH // 2)))
        self.screen.blit(msg3, msg3.get_rect(center=(WIDTH // 2, HEIGTH // 2 + 50)))
 
    
    def _start_singleplayer(self):
        self.level = Level()
        self.state = "playing_solo"
 
    
    def _connect_and_start(self):
        try:
            self.net = NetworkClient(SERVER_IP, SERVER_PORT)
        except Exception as e:
            self.error_msg = str(e)
            self.state = "error"
            return
        self.level = Level()
        self.state = "playing_multi"
 
    
    @staticmethod
    def _player_state(player) -> dict:
        return {
            'pos':        (player.rect.centerx, player.rect.centery),
            'status':     player.status,
            'health':     player.health,
            'max_health': player.stats['health'],
        }
 
    
    def _draw_remote_players(self, others: dict):
        offset  = self.level.visible_sprites.offset
        colours = [(70, 130, 200), (200, 80, 80), (80, 200, 100), (200, 180, 50)]
 
        for pid, state in others.items():
            colour = colours[pid % len(colours)]
            wx, wy = state['pos']
            sx = wx - int(offset.x)
            sy = wy - int(offset.y)
 
            pygame.draw.circle(self.screen, colour,  (sx, sy), 20)
            pygame.draw.circle(self.screen, 'white', (sx, sy), 20, 2)
 
            if 'health' in state and 'max_health' in state:
                bar_w = 40
                ratio = max(0, state['health'] / max(1, state['max_health']))
                pygame.draw.rect(self.screen, (60, 60, 60),  (sx - 20, sy - 32, bar_w, 6))
                pygame.draw.rect(self.screen, (220, 60, 60), (sx - 20, sy - 32, int(bar_w * ratio), 6))
 
            label = self.font_small.render(f"P{pid}", True, "white")
            self.screen.blit(label, label.get_rect(midbottom=(sx, sy - 34)))
 
   
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
 
                if self.state in ("playing_solo", "playing_multi"):
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_m:
                            self.level.toggle_menu()
                        if event.key == pygame.K_ESCAPE:
                            self.level.game_paused = True
 
                if self.state == "error":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "menu"
 
            if self.state == "menu":
                self.draw_menu()
 
            elif self.state == "playing_solo":
                self.screen.fill(WATER_COLOR)
                self.level.run()
 
            elif self.state == "playing_multi":
                self.screen.fill(WATER_COLOR)
                self.level.run()
 
                if self.net and self.net._running:
                    self.net.send_state(self._player_state(self.level.player))
                    self._draw_remote_players(self.net.get_others())
                elif self.net and not self.net._running:
                    self.error_msg = "Lost connection to server."
                    self.net = None
                    self.level = None
                    self.state = "error"
 
            elif self.state == "error":
                self.draw_error()
 
            pygame.display.update()
            self.clock.tick(FPS)
 
    def _shutdown(self):
        if self.net:
            self.net.stop()
        pygame.quit()
        sys.exit()
 
 
if __name__ == '__main__':
    game = Game()
    game.run()

