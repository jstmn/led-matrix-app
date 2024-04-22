from dataclasses import dataclass
from typing import List, Dict, Tuple
from time import time, sleep
from datetime import datetime
from threading import Thread
from math import floor

import numpy as np

N_LEDS_PER_DIM = 28

@dataclass
class Cell:
    r: int
    g: int
    b: int
    x: int
    y: int

    @property
    def led_idx(self) -> int:
        return xy_to_led_idx(self.x, self.y)

    @property
    def color(self) -> int:
        return (self.r << 16) + (self.g << 8) + self.b

    @property
    def color_tuple(self) -> Tuple[float, float, float]:
        return (self.r, self.g, self.b)

    def set_blank(self):
        self.r = 0
        self.g = 0
        self.b = 0

    def __post_init__(self):
       assert isinstance(self.led_idx, int)
       assert isinstance(self.r, int)
       assert isinstance(self.g, int)
       assert isinstance(self.b, int)
       assert 0 <= self.r <= 255
       assert 0 <= self.g <= 255
       assert 0 <= self.b <= 255


def xy_to_led_idx(x: int, y: int) -> int:
    """Converts the xy position of a led to the led_number which is
    used to index the buffer
    
    Led matrix numbering format:
    
        0  1  2  ... 26 27
        55 54 53 ... 29 28
        56 57 58 ... 59 60
        88 87 86 ... 62 61
        ...
        783 782  ...   756
    
    Coordinate system:
    
        +y
        ^
        |
        |
        |
        .-----> +x
    """
    y_inv = N_LEDS_PER_DIM - y - 1
    x_mod = x % N_LEDS_PER_DIM
    n0 = y_inv * N_LEDS_PER_DIM
    if y_inv == 0 or y_inv % 2 == 0:
        n = n0 + x_mod
    else:
        n = n0 + (N_LEDS_PER_DIM - x_mod - 1)
    return n

# TODO: Create LedWriter class, and make a subclass for LedWriterHardware. provide a callback to write_from_json so that LedWriterHardware can write to the LED


CGL_MODE = "cgl"
RGB_MODE = "rgb"



class LedWriterBase:
    def __init__(self):
        self.num_leds = N_LEDS_PER_DIM * N_LEDS_PER_DIM
        self.mode = RGB_MODE



class LedWriterSim:
    def __init__(self):
        self.state = []
        self.new_data_received = False
        super().__init__()

    def run(self):
        import pygame
        import sys

        pygame.init()
        px_per_led = 20
        screen_width = N_LEDS_PER_DIM * px_per_led
        screen = pygame.display.set_mode((screen_width, screen_width))
        pygame.display.set_caption("Simulated LED matrix")

        # Draw the line on the screen
        screen.fill((255, 255, 255))  # Fill the screen with white background

        # Main game loop
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            if self.new_data_received:
                screen.fill((255, 255, 255))
                self.new_data_received = False

            for cell in self.state:
                square_x = cell.x * px_per_led
                square_y = screen_width - (cell.y * px_per_led) - px_per_led
                pygame.draw.rect(screen, cell.color_tuple, (square_x, square_y, px_per_led, px_per_led))

            # Update the display
            pygame.display.flip()

            # Control the frame rate
            pygame.time.Clock().tick(30)

    def clear(self):
        """Clear the led matrix"""
        self.state = []

    def cgl_update_thread(self):
        import pygame
        import numpy as np
        from scipy import signal

        # Convolutional kernel that counts diagonals and top/bottom/sides as neighbors
        diag_kernel = np.ones((3, 3), dtype=np.int8)
        diag_kernel[1, 1] = 0

        # Convolutional kernel that doesn't count diagonals as neighbors
        # We give user option to choose either one.
        cross_kernel = np.zeros((3, 3), dtype=np.uint8)
        rows = np.array([[0, 2], [1, 1]])
        cols = np.array([[1, 1], [0, 2]])
        cross_kernel[rows, cols] = 1

        def calc_neighbors(pop):
            # return signal.convolve(pop, diag_kernel, mode='same')
            return signal.convolve(pop, cross_kernel, mode='same')

        # TODO: reimplement, this currently isn't working correctly, [x][x][x] should oscilate
        while self.mode == CGL_MODE:
            pygame.time.Clock().tick(1)
            # update state
            populated = np.zeros((N_LEDS_PER_DIM, N_LEDS_PER_DIM), dtype=np.bool_)
            for cell in self.state:
                populated[cell.x, cell.y] = True
            neighbors = calc_neighbors(populated)
            empty_3n = np.logical_and(~populated, neighbors >= 3)
            pop_14n = np.logical_and(populated, np.logical_or(neighbors <= 1, neighbors >= 4))
            pop_23n = np.logical_and(populated, np.logical_or(neighbors == 2, neighbors == 3))
            populated = np.where(pop_14n, 0, np.where(pop_23n, 1, np.where(empty_3n, 1, self)))

            new_state = []
            alive = np.nonzero(populated)
            for x_idx, y_idx in zip(alive[0], alive[1]):
                x = int(x_idx)
                y = int(y_idx)
                cell = Cell(r=255, g=255, b=255, x=x, y=y)
                new_state.append(cell)
            self.state = new_state


    def write_from_json(self, json_data: Dict):
        """Parse a json of rgb values and write to the led matrix. json format:
            { "data": [
                {"r":0,"g":0,"b":0,"a":0,"x":0,"y":0},
                ...
                {"r":0,"g":0,"b":0,"a":0,"x":27,"y":27}
                ]
            }
        """
        self.new_data_received = True
        new_state = []
        for data in json_data["data"]:
            r = int(data["r"])
            g = int(data["g"])
            b = int(data["b"])
            if r > 0 or g > 0 or b > 0:
                cell = Cell(r=r, g=g, b=b, x=int(data['x']), y=int(data['y']),  led_idx=0)
                new_state.append(cell)
        self.state = new_state

        if json_data["mode"] == CGL_MODE:
            if self.mode == RGB_MODE:
                thread = Thread(target=self.cgl_update_thread)
                thread.start()

        self.mode = json_data["mode"]




class LedWriter(LedWriterBase):
    def __init__(self, brightness: int = 10):
        super().__init__()
        assert 0 < brightness <= 31
        # from src import apa102_v2
        # self.strip = apa102_v2.APA102(
        #     num_led=self.num_leds, bus_method='spi', spi_bus=0, mosi=None, sclk=None, ce=None,
        #     bus_speed_hz=8000000, global_brightness=4
        #     )
        from src import apa102
        self.strip = apa102.APA102(self.num_leds, brightness)

    def clear(self):
        """Clear the led matrix"""
        self.strip.clearStrip()

    def draw_time(self):
        if self.mode == CGL_MODE:
            return

        cells = []
        t = datetime.now()
        intensity = 1
        # nighttime
        if t.hour < 5 or t.hour > 21:
            intensity = 1
        else:
            intensity = 50

        for i in range(t.hour):
            x = i
            y = N_LEDS_PER_DIM - 1
            cells.append(Cell(
                r=intensity,
                g=0,
                b=0,
                x=x, 
                y=y
            ))

        # for i in range(t.minute):
        for i in range(t.second):
            x = i
            y = N_LEDS_PER_DIM - 2 - floor(i / N_LEDS_PER_DIM)
            cells.append(Cell(
                r=0,
                g=floor(intensity/2),
                b=floor(intensity/2),
                x=x,
                y=y
            ))
        self.write(cells)


    # TODO(@jstmn): Speed up write time by setting pixel buffer in a 
    # single call, using numpy or something
    def write(self, cells: List[Cell], debug_timing: bool = False):
        """Write to the led matrix.
        """
        self.strip.reset_buffer()

        t0 = time()
        for cell in cells:
            assert isinstance(cell, Cell)
            self.strip.setPixel(cell.led_idx, cell.r, cell.g, cell.b)
            # self.strip.setPixelRGB(cell.led_idx, cell.color)
        if debug_timing:
            print("strip.setPixel():", time() - t0)

        # ~ 0.008191 sec for 100 cells
        t0 = time()
        self.strip.show()
        if debug_timing:
            print("strip.show():    ", time() - t0)

    def update_buffer(self, cells):
        for cell in cells:
            assert isinstance(cell, Cell)
            self.strip.setPixel(cell.led_idx, cell.r, cell.b, cell.g)



    def cgl_update_thread(self, initial_cells: List[Cell]):

        # write to board
        def write_to_board():
            cells = []
            alives = alive.nonzero()
            for x, y in zip(alives[0], alives[1]):
                cells.append(Cell(r=255, g=255, b=255, x=int(x), y=int(y)))
            self.write(cells)


        alive = np.zeros((N_LEDS_PER_DIM, N_LEDS_PER_DIM), dtype=np.bool_)
        for cell in initial_cells:
            alive[cell.x, cell.y] = 1.0

        while True:
            write_to_board()

            sleep(1.0)
            if self.mode != CGL_MODE:
                self.clear()
                return



    def write_from_json(self, json_data: Dict):
        """Parse a json of rgb values and write to the led matrix. json format:
            { "data": [
                {"r":0,"g":0,"b":0,"a":0,"x":0,"y":0},
                ...
                {"r":0,"g":0,"b":0,"a":0,"x":27,"y":27}
                ]
            }
        """
        self.clear()
        cells = []
        for idx, data in enumerate(json_data["data"]):
            r = int(data["r"])
            g = int(data["g"])
            b = int(data["b"])
            if r > 0 or g > 0 or b > 0:
                cell = Cell(r=r, g=g, b=b, x=int(data['x']), y=int(data['y']))
                cells.append(cell)

        if json_data["mode"] == CGL_MODE:
            self.mode = CGL_MODE
            thread = Thread(target=self.cgl_update_thread, args=(cells, ))
            thread.start()

        else:
            if self.mode == CGL_MODE:
                self.mode = RGB_MODE
            self.write(cells)


if __name__ == "__main__":
    writer = LedWriter()
