import os
import sys
import time
import signal
import cv2 as cv
import numpy as np
import msvcrt
from typing import List
from enum import Enum, unique
from os import get_terminal_size

@unique
class PlayMode(Enum):
    VIDEO    = 'RESTART_CMD'
    REALTIME = 'SHUTDOWN_CMD'

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

def on_sigint_clear_console(sig, frame):
    if sig == signal.SIGINT:
        clearConsole()
    sys.exit(0)

def play_in_terminal(
        video_path_or_cam_idx: str | int,
        black2white_chars       : List[str],
        color_sets              : List[List[int]],
        height                  : int,
        width                   : int,
        mode                    : PlayMode,
        max_fps                 = None):

    cap = cv.VideoCapture(video_path_or_cam_idx)
    if not cap.isOpened():
        print("Cannot cap")
        exit()

    mirror_x = False
    mirror_y = False
    color_idx = 0

    signal.signal(signal.SIGINT, on_sigint_clear_console)
    max_fps = max_fps if max_fps else cap.get(cv.CAP_PROP_FPS)
    frame_period_ns = 1e9 / max_fps
    prev_frame_time_ns = time.time_ns()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame, exiting...")
            break

        elapsed_time_ns = time.time_ns() - prev_frame_time_ns
        if elapsed_time_ns < frame_period_ns:
            if mode == PlayMode.REALTIME:
                pass
            else:
                time.sleep((frame_period_ns - elapsed_time_ns) / 1e9)
        prev_frame_time_ns = time.time_ns()

        # MIRROR
        if mirror_x:
            frame = cv.flip(frame, 1)
        if mirror_y:
            frame = cv.flip(frame, 0)

        frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        frame = cv.resize(frame, (width, height), cv.INTER_NEAREST)

        ascii_frame = process_gray_frame(frame, black2white_chars, color_sets[color_idx])

        # KEY EVENTS
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8").lower()

            if key == "h":
                save_ascii_html(ascii_frame)
            elif key == "m":
                mirror_x = not mirror_x
            elif key == "n":
                mirror_y = not mirror_y
            elif key == "c":
                color_idx = (color_idx + 1) % len(color_sets)

        print_video_frame_ascii(ascii_frame)

    cap.release()
    clearConsole()

def save_ascii_html(frame):
    with open("ascii_frame.html", "w", encoding="utf-8") as f:
        f.write("<pre style='font-size:7px; line-height:7px; background:black;'>\n")
        for row in frame:
            for pix in row:
                if pix.startswith("\033["):
                    # format: \033[36;1mX\033[0m
                    try:
                        before, after = pix.split("m", 1)
                        code = before.replace("\033[", "")
                        char = after.replace("\033[0m", "")

                        # ambil angka pertama kalau ada ';'
                        code = int(code.split(";")[0])

                        html_color = ansi_to_html(code)
                        f.write(f"<span style='color:{html_color}'>{char}</span>")
                    except:
                        f.write(" ")
                else:
                    f.write(pix)
            f.write("<br>\n")
        f.write("</pre>")
    print("Saved -> ascii_frame.html")

def ansi_to_html(code):
    ansi_colors = {
        30: "#000000", 31: "#AA0000", 32: "#00AA00", 33: "#AA5500",
        34: "#0000AA", 35: "#AA00AA", 36: "#00AAAA", 37: "#AAAAAA",
        90: "#555555", 91: "#FF5555", 92: "#55FF55", 93: "#FFFF55",
        94: "#5555FF", 95: "#FF55FF", 96: "#55FFFF", 97: "#FFFFFF",
    }
    return ansi_colors.get(code, "#FFFFFF")

def process_gray_frame(frame: np.ndarray, chars: List[str], colors: List[int]):
    return np.vectorize(lambda pix: colorize_text_gray(pix2ascii_gray(pix, chars), pix, colors))(frame)

def colorize_text_gray(text: str, gray: int, colors: List[int]):
    step = 255 / len(colors)
    idx = min(int(gray / step), len(colors) - 1)
    return f"\033[{colors[idx]};1m{text}\033[0m"

def pix2ascii_gray(pix: int, chars: List[str]):
    step = 255 / len(chars)
    idx = min(int(pix / step), len(chars) - 1)
    return chars[idx]

def print_video_frame_ascii(frame: np.ndarray):
    frame_str = "\n".join("".join(row) for row in frame)
    clearConsole()
    print(frame_str, flush=True)

if __name__ == "__main__":
    term_size = get_terminal_size()
    h, w = term_size.lines, term_size.columns

    black2white_chars = [' ', '`', '.', '~', '+', '*', 'o', 'O', '0', '#', '@']

    color_sets = [
        [90, 37, 97],
        [32, 92, 97],
        [33, 93],
        [34, 36, 94, 96],
        list(range(30, 38)),
        list(range(90, 98))
    ]

    play_in_terminal(
        video_path_or_cam_idx = 0,
        black2white_chars = black2white_chars,
        color_sets = color_sets,
        height = h,
        width = w,
        mode = PlayMode.REALTIME,
        max_fps = 30
    )
