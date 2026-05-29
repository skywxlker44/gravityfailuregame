import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import gravityfailuregame.main as main


class GeometryAndColorTests(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(main.clamp(5, 0, 10), 5)
        self.assertEqual(main.clamp(-2, 0, 10), 0)
        self.assertEqual(main.clamp(20, 0, 10), 10)

    def test_color_helpers(self):
        self.assertEqual(main.darken((20, 30, 40), 10), (10, 20, 30))
        self.assertEqual(main.brighten((250, 250, 250), 20), (255, 255, 255))

    def test_tile_rect(self):
        rect = main.tile_rect(2, 3, 4, 5)
        self.assertEqual(rect, pygame.Rect(64, 96, 128, 160))

    def test_player_rect(self):
        player = {"x": 10.8, "y": 20.2}
        self.assertEqual(main.player_rect(player), pygame.Rect(10, 20, main.PLAYER_W, main.PLAYER_H))


class LevelAndRuntimeTests(unittest.TestCase):
    def test_build_level_has_required_fields(self):
        level = main.build_level(main.LEVEL_DEFS[0])
        self.assertIn("solids", level)
        self.assertIn("spikes", level)
        self.assertIn("crystals", level)
        self.assertIn("checkpoints", level)
        self.assertIn("bounces", level)
        self.assertIn("memories", level)
        self.assertIn("moving_platforms", level)
        self.assertEqual(level["goal"].height, main.TILE * 2)

    def test_update_moving_platforms_moves_platforms(self):
        old_level = main.level
        old_frame = main.frame_count
        try:
            main.level = main.build_level({
                "name": "Test",
                "theme": "violet",
                "hint": "",
                "spawn": (0, 0),
                "goal": (1, 1),
                "solids": [],
                "spikes": [],
                "crystals": [],
                "checkpoints": [],
                "bounces": [],
                "memories": [],
                "moving_platforms": [(1, 1, 2, 1, "x", 2, 0.1, 0.0)],
            })
            platform = main.level["moving_platforms"][0]
            main.frame_count = 15
            main.update_moving_platforms()
            self.assertNotEqual(platform["dx"], 0)
        finally:
            main.level = old_level
            main.frame_count = old_frame


if __name__ == "__main__":
    unittest.main()
