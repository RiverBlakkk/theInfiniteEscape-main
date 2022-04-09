from typing import IO
import pygame
from tiles import Tile
from settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT
from player import Player
from particles import ParticleEffect
from pathlib import Path
import yaml

with (Path(__file__).parent.parent / "tiles.yml").open() as f:
	tiles = yaml.safe_load(f)


ALLOW_FRAME_ADVANCE = True
# allow the usage of frame advance
# hint: ' and / are used for frame advance
pygame.font.init()
font = pygame.font.Font('MainMenu/font.ttf', 20)

COLOR1 = (200, 168, 90)


class Level:
	def __init__(
		self, path: str | Path | None, surface: pygame.Surface | pygame.surface.Surface
	):
		# level setup
		self.display_surface = surface
		self.setup_level(path)
		self.world_shift = 0
		self.current_x = 0

		# dust
		self.dust_sprite = pygame.sprite.GroupSingle()
		self.player_on_ground = False

	def create_jump_particles(self, pos):
		if self.player.sprite.facing_right:
			pos -= pygame.math.Vector2(10, 5)
		else:
			pos += pygame.math.Vector2(10, -5)
		jump_particle_sprite = ParticleEffect(pos, 'jump')
		self.dust_sprite.add(jump_particle_sprite)

	def setup_level(self, path: Path | str | None):
		if path is None:
			self.setup_empty()
			return

		if isinstance(path, str):
			path = Path(path)

		if hasattr(self, 'tiles'):
			self.tiles.empty()  # type:ignore
		else:
			self.tiles = pygame.sprite.Group()
		if hasattr(self, 'player'):
			self.player.empty()  # type:ignore
		else:
			self.player = pygame.sprite.GroupSingle()

		f: IO[bytes]

		with open(path, "rb") as f:
			first_byte = f.read(1)
			if first_byte == b"\x00":
				def read(n: int = 1) -> bytes:
					return f.read(n)
			elif first_byte == b"0":
				# hexadecimal
				f.read(1)

				def read(n: int = 1) -> bytes:
					if n == -1:
						while (c := f.read(1)) != b"\n":
							if c == b"":
								break
						return b""
					s = b""
					while len(s) < n*2:
						c = f.read(1)
						if c == b"":
							return bytes.fromhex(s.decode("ascii"))
						if c not in b"0123456789abcdefABCDEF?":
							continue
						if c == b"?" and s.count(b"?") != len(s):
							continue
						if c != b"?" and b"?" in s:
							s.replace(b"?", b"")
						s += c
					if s == b"????":
						return b"?"
					return bytes.fromhex(s.decode("ascii"))
			else:
				raise ValueError("Invalid file format")

			def read_num(n: int = 1):
				total = 0
				data = read(n)
				if data == b"?" and n == 2:
					return -1
				for i in data:
					total *= 256
					total += i
				return total

			p_size = read()[0]
			i = 0
			while True:
				v = read()
				i+=1
				if v == b"":
					break
				el_type = v[0]
				if el_type == 0:
					# comment
					length = read_num(2)
					read(length)
				elif el_type == 1:
					# tile
					tile_id = read(1)[0]
					x = read_num(p_size)
					y = read_num(p_size)
					self.tiles.add(
						Tile((0+x*TILE_SIZE, SCREEN_HEIGHT-(y+1)*TILE_SIZE),
							(
								TILE_SIZE*tiles[tile_id]['width'],
								TILE_SIZE*tiles[tile_id]['height']
							),
							tile_id
						)
					)
				elif el_type == 2:
					# player spawn
					x = read_num(p_size)
					y = read_num(p_size)
					self.player.add(Player(
						(0+x*TILE_SIZE, SCREEN_HEIGHT-(y+1)*TILE_SIZE),
						self.display_surface,
						self.create_jump_particles
					))

				else:
					print("Unknown element type:", el_type)
		"""
		for row_index,row in enumerate(layout):
			for col_index,cell in enumerate(row):
				x = col_index * tile_size
				y = row_index * tile_size

				if cell == 'X':
					tile = Tile((x,y),tile_size)
					self.tiles.add(tile)
				if cell == 'P':
					player_sprite = Player((x,y),self.display_surface,self.create_jump_particles)
					self.player.add(player_sprite)
		"""

	def setup_empty(self):
		if hasattr(self, 'tiles'):
			self.tiles.empty()
		else:
			self.tiles = pygame.sprite.Group()
		if hasattr(self, 'player'):
			self.player.empty()
		else:
			self.player = pygame.sprite.GroupSingle()
		self.player.add(Player((0,0),self.display_surface,self.create_jump_particles))

	def scroll_x(self):
		player: Player = self.player.sprite  # type:ignore
		player_x = player.rect.centerx

		if player_x < SCREEN_WIDTH / 4:
			self.world_shift = SCREEN_WIDTH / 4 - player.rect.centerx
			player.rect.centerx = int(SCREEN_WIDTH / 4)
		elif player_x > 3*(SCREEN_WIDTH / 4):
			self.world_shift = 3*(SCREEN_WIDTH / 4) - player.rect.centerx
			player.rect.centerx = int(3*(SCREEN_WIDTH / 4))
		else:
			self.world_shift = 0
			player.speed = 1

	def run(self):
		# dust particles
		self.dust_sprite.update(self.world_shift)
		self.dust_sprite.draw(self.display_surface)

		# level tiles
		self.tiles.update(self.world_shift)
		self.tiles.draw(self.display_surface)

		# player
		self.player.update(self)
		self.player.draw(self.display_surface)

		self.current_x += self.world_shift

		self.scroll_x()

		if ALLOW_FRAME_ADVANCE and pygame.key.get_pressed()[pygame.K_QUOTE]:
			# display some debug info
			player: Player = self.player.sprite  # type:ignore
			self.display_surface.blit(font.render(
					f"{player.rect.center} {player.direction}",
					True, COLOR1
				), (0, 0)
			)
			pygame.draw.rect(self.display_surface, COLOR1, player.rect, 1)
			pygame.display.update()
			while pygame.key.get_pressed()[pygame.K_QUOTE]:
				pygame.event.pump()
			while not(pygame.key.get_pressed()[pygame.K_QUOTE]) \
					and not(pygame.key.get_pressed()[pygame.K_SLASH]):
				pygame.event.pump()

	def draw(self):
		self.dust_sprite.draw(self.display_surface)
		self.tiles.draw(self.display_surface)
		self.player.draw(self.display_surface)
