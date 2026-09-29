import os
import sys
import pygame
pygame.init()

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def load_assets():
    images = {}
    audio = {}

    textures_root = resource_path('textures')
    for dirpath, dirnames, filenames in os.walk(textures_root):
        for filename in filenames:
            name, ext = os.path.splitext(filename)
            if ext.lower() in ['.png', '.jpg', '.jpeg', '.svg']:
                rel_dir = os.path.relpath(dirpath, textures_root)
                if rel_dir == ".":
                    dict_key = name
                else:
                    dict_key = os.path.join(rel_dir, name).replace("\\", "/")

                full_path = os.path.join(dirpath, filename)
                images[dict_key] = pygame.image.load(full_path).convert_alpha()

    audio_root = resource_path('audio')
    for dirpath, dirnames, filenames in os.walk(audio_root):
        for filename in filenames:
            name, ext = os.path.splitext(filename)
            if ext.lower() in ['.mp3', '.ogg', '.wav']:
                rel_dir = os.path.relpath(dirpath, audio_root)
                if rel_dir == ".":
                    dict_key = name
                else:
                    dict_key = os.path.join(rel_dir, name).replace("\\", "/")

                full_path = os.path.join(dirpath, filename)
                audio[dict_key] = pygame.mixer.Sound(full_path)

    return images, audio

images, audio = load_assets()

print("You found the easter egg")