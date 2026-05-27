import pygame 
from settings import *
from tile import Tile
from player import Player
from debug import debug
from support import *
from random import choice, randint
from weapon import Weapon
from ui import UI
from enemy import Enemy
from particles import AnimationPlayer
from magic import MagicPlayer
from upgrade import Upgrade
import sys


class Level:
	def __init__(self):

		# #server stuff
		# def draw_multiplayer(self, players, my_id):
		# 	for pid, pos in players.items():
		# 		if pid != my_id:
		# 			pygame.draw.circle(self.display_surface, "blue", pos, 20)

		# display
		self.display_surface = pygame.display.get_surface()
		self.game_paused = False
		self.player_dead = False

		# groups
		self.visible_sprites = YSortCameraGroup()
		self.obstacle_sprites = pygame.sprite.Group()
		self.attack_sprites = pygame.sprite.Group()
		self.attackable_sprites = pygame.sprite.Group()

		self.current_attack = None

		# map
		self.create_map()

		# ui
		self.ui = UI()
		self.upgrade = Upgrade(self.player)

		# effects
		self.animation_player = AnimationPlayer()
		self.magic_player = MagicPlayer(self.animation_player)

		# pause menu fonts
		self.font_big = pygame.font.SysFont("arial", 60)
		self.font_small = pygame.font.SysFont("arial", 30)

	def create_map(self):
		layouts = {
			'boundary': import_csv_layout('../map/map_FloorBlocks.csv'),
			'grass': import_csv_layout('../map/map_Grass.csv'),
			'object': import_csv_layout('../map/map_Objects.csv'),
			'entities': import_csv_layout('../map/map_Entities.csv')
		}

		graphics = {
			'grass': import_folder('../graphics/Grass'),
			'objects': import_folder('../graphics/objects')
		}

		for style, layout in layouts.items():
			for row_index, row in enumerate(layout):
				for col_index, col in enumerate(row):
					if col != '-1':
						x = col_index * TILESIZE
						y = row_index * TILESIZE

						if style == 'boundary':
							Tile((x, y), [self.obstacle_sprites], 'invisible')

						if style == 'grass':
							image = choice(graphics['grass'])
							Tile((x, y), [self.visible_sprites, self.obstacle_sprites, self.attackable_sprites], 'grass', image)

						if style == 'object':
							image = graphics['objects'][int(col)]
							Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'object', image)

						if style == 'entities':
							if col == '394':
								self.player = Player(
									(x, y),
									[self.visible_sprites],
									self.obstacle_sprites,
									self.create_attack,
									self.destroy_attack,
									self.create_magic
								)
							else:
								if col == '390': name = 'bamboo'
								elif col == '391': name = 'spirit'
								elif col == '392': name = 'raccoon'
								else: name = 'squid'

								Enemy(
									name,
									(x, y),
									[self.visible_sprites, self.attackable_sprites],
									self.obstacle_sprites,
									self.damage_player,
									self.trigger_death_particles,
									self.add_exp
								)

	def create_attack(self):
		self.current_attack = Weapon(self.player, [self.visible_sprites, self.attack_sprites])

	def create_magic(self, style, strength, cost):
		if style == 'heal':
			self.magic_player.heal(self.player, strength, cost, [self.visible_sprites])

		if style == 'flame':
			self.magic_player.flame(self.player, cost, [self.visible_sprites, self.attack_sprites])

	def destroy_attack(self):
		if self.current_attack:
			self.current_attack.kill()
		self.current_attack = None

	def player_attack_logic(self):
		for attack in self.attack_sprites:
			hits = pygame.sprite.spritecollide(attack, self.attackable_sprites, False)

			if hits:
				for target in hits:
					if target.sprite_type == 'grass':
						pos = target.rect.center
						offset = pygame.math.Vector2(0, 75)

						for _ in range(randint(3, 6)):
							self.animation_player.create_grass_particles(pos - offset, [self.visible_sprites])

						target.kill()
					else:
						target.get_damage(self.player, attack.sprite_type)

	def damage_player(self, amount, attack_type):
		if self.player.vulnerable:
			self.player.health -= amount
			if self.player.health <= 0:
				self.player.health = 0
				self.player_dead = True
			self.player.vulnerable = False
			self.player.hurt_time = pygame.time.get_ticks()
			self.animation_player.create_particles(attack_type, self.player.rect.center, [self.visible_sprites])

	def trigger_death_particles(self, pos, type_):
		self.animation_player.create_particles(type_, pos, self.visible_sprites)

	def add_exp(self, amount):
		self.player.exp += amount

	def toggle_menu(self):
		self.game_paused = not self.game_paused

	def draw_pause_menu(self):

		#  dark background
		overlay = pygame.Surface((WIDTH, HEIGTH))
		overlay.set_alpha(180)
		overlay.fill((0, 0, 0))
		self.display_surface.blit(overlay, (0, 0))

		mouse = pygame.mouse.get_pos()
		clicked = pygame.mouse.get_pressed()

		#title
		title = self.font_big.render("PAUSED", True, "white")
		self.display_surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGTH//3)))

		 #buttons
		resume = pygame.Rect(WIDTH//2 - 100, HEIGTH//2, 200, 60)
		quit_btn = pygame.Rect(WIDTH//2 - 100, HEIGTH//2 + 80, 200, 60)

		resume_color = "gray" if resume.collidepoint(mouse) else "darkgray"
		quit_color = "red" if quit_btn.collidepoint(mouse) else "darkred"

		pygame.draw.rect(self.display_surface, resume_color, resume)
		pygame.draw.rect(self.display_surface, quit_color, quit_btn)

		resume_text = self.font_small.render("RESUME", True, "white")
		quit_text = self.font_small.render("QUIT", True, "white")

		self.display_surface.blit(resume_text, resume_text.get_rect(center=resume.center))
		self.display_surface.blit(quit_text, quit_text.get_rect(center=quit_btn.center))

		  #clicks
		if clicked[0]:
			if resume.collidepoint(mouse):
				self.game_paused = False

			if quit_btn.collidepoint(mouse):
				pygame.quit()
				sys.exit()

	def draw_death_screen(self):
		overlay = pygame.Surface((WIDTH,HEIGTH))
		overlay.set_alpha(200)
		overlay.fill((0, 0, 0))
		self.display_surface.blit(overlay, (0, 0))

		mouse = pygame.mouse.get_pos()
		clicked = pygame.mouse.get_pressed()

		title = self.font_big.render("YOU DIED", True, "red")
		self.display_surface.blit(title, title.get_rect(center=(WIDTH // 2, HEIGTH // 3)))

		restart_btn = pygame.Rect(WIDTH//2 - 120, HEIGTH//2, 240, 60)
		quit_btn = pygame.Rect(WIDTH//2 - 120, HEIGTH//2 + 90, 240, 60)

		restart_color = "gray" if restart_btn.collidepoint(mouse) else "darkgray"
		quit_color = "red" if quit_btn.collidepoint(mouse) else "darkred"

		pygame.draw.rect(self.display_surface, restart_color, restart_btn)
		pygame.draw.rect(self.display_surface, quit_color, quit_btn)

		restart_text = self.font_small.render("RESTART", True, "white")
		quit_text = self.font_small.render("QUIT", True, "white")

		self.display_surface.blit(
		restart_text,
		restart_text.get_rect(center=restart_btn.center)
		)

		self.display_surface.blit(
		quit_text,
		quit_text.get_rect(center=quit_btn.center)
		)

		if clicked[0]:

			if restart_btn.collidepoint(mouse):
				self.__init__()

			if quit_btn.collidepoint(mouse):
				pygame.quit()
				sys.exit()



	def run(self):

		self.visible_sprites.custom_draw(self.player)
		self.ui.display(self.player)

		keys = pygame.key.get_pressed()

		if not self.player_dead:
			if keys[pygame.K_ESCAPE]:
				self.game_paused = True

		if self.player_dead:
			self.draw_death_screen()

		elif self.game_paused:
			self.draw_pause_menu()

		else:
			self.visible_sprites.update()
			self.visible_sprites.enemy_update(self.player)
			self.player_attack_logic()


class YSortCameraGroup(pygame.sprite.Group):
	def __init__(self):
		super().__init__()

		self.display_surface = pygame.display.get_surface()
		self.half_width = self.display_surface.get_size()[0] // 2
		self.half_height = self.display_surface.get_size()[1] // 2
		self.offset = pygame.math.Vector2()

		self.floor_surf = pygame.image.load('../graphics/tilemap/ground.png').convert()
		self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))

	def custom_draw(self, player):

		self.offset.x = player.rect.centerx - self.half_width
		self.offset.y = player.rect.centery - self.half_height

		floor_pos = self.floor_rect.topleft - self.offset
		self.display_surface.blit(self.floor_surf, floor_pos)

		for sprite in sorted(self.sprites(), key=lambda s: s.rect.centery):
			pos = sprite.rect.topleft - self.offset
			self.display_surface.blit(sprite.image, pos)

	def enemy_update(self, player):
		for sprite in self.sprites():
			if hasattr(sprite, "sprite_type") and sprite.sprite_type == "enemy":
				sprite.enemy_update(player)