"""
SondeR cat sprites.

What the reference actually shows (and v1-v3 got wrong):
  * the sitting cat is TALLER than wide — an upright cat, not a blob
  * distinct head -> chest -> two visible FRONT LEGS down to paws
  * haunches bulge at the sides; tail lies on the ground beside the paws
  * small triangle ears, big eyes, whiskers, thick white outline around all

Legend: . empty | K dark outline | B body | S stripe | W white/paws
        E eye white | N nose | M mouth | Z inner ear | H whisker
        G keycap front | g keycap top | O halo (computed, never authored)
"""

GRID_W, GRID_H = 26, 28
EYE_W, EYE_H = 3, 3

# ----------------------------------------------------------------- sitting ---
# upright sit: head / chest / front legs+paws / haunches / ground tail
SIT_A = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    ".HHKBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBBK..",
    "..KBBBBKWWBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

# tail tip flicked up
SIT_B = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    ".HHKBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK.K..",
    "..KBBBBKBBBBBBBBKBBBBKKBK.",
    "..KBBBBKBBBBBBBBKBBBKKBK..",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBK...",
    "..KBBBBKWWBKKBWWKBKBBK....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "..........................",
    "..........................",
]

BLINK = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBBBBBBBBBBBBBBBBKHH...",
    "...KBKKKBBBBBBBBKKKBK.....",
    ".HHKBBBBBBBNNBBBBBBBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBBK..",
    "..KBBBBKWWBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

# --------------------------------------- typing at two 3D keycaps (3/4) ------
TYPE_A = [
    "..........................",
    ".....KK........KK.........",
    "....KBBK......KBBK........",
    "....KBZBK....KBZBK........",
    "...KBBBBBKKKKBBBBBK.......",
    "...KBBBBBBBBBBBBBBK.......",
    "..KBBBBBBBBBBBBBBBBK......",
    ".HKBEEEBBBBBBBBEEEBK......",
    "..KBEEEBBBBBBBBEEEBK......",
    ".HKBEEEBBBNNBBBEEEBKKK....",
    "..KBBBBBBBMMBBBBBBKKBBK...",
    "..KBBBBBBBBBBBBBBBKKBBK...",
    "..KBBBBBBBBBBBBBBBBKBBK...",
    "...KBBBBBBBBBBBBBBBKBK....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBKBBBBKBBBBBBBK.....",
    "....KBBKBBBBKWWKBBBBK.....",
    "....KBBKBBBBKWWKBBBBK.....",
    "....KBBKBBBBKKKKBBBBK.....",
    "....KWWKBBBBBBKBBBBBK.....",
    "....KWWKBBBBBBKWWBBBK.....",
    "...KKKKKKKBBBBKKKKKKK.....",
    "...KggggggKKKKKggggggK....",
    "..KggggggGGKKKggggggGGK...",
    "..KGGGGGGGGK.KGGGGGGGGK...",
    "...KKKKKKKK...KKKKKKKK....",
    "..........................",
    "..........................",
]

TYPE_B = [
    "..........................",
    ".....KK........KK.........",
    "....KBBK......KBBK........",
    "....KBZBK....KBZBK........",
    "...KBBBBBKKKKBBBBBK.......",
    "...KBBBBBBBBBBBBBBK.......",
    "..KBBBBBBBBBBBBBBBBK......",
    ".HKBEEEBBBBBBBBEEEBK......",
    "..KBEEEBBBBBBBBEEEBK......",
    ".HKBEEEBBBNNBBBEEEBKKK....",
    "..KBBBBBBBMMBBBBBBKKBBK...",
    "..KBBBBBBBBBBBBBBBKKBBK...",
    "..KBBBBBBBBBBBBBBBBKBBK...",
    "...KBBBBBBBBBBBBBBBKBK....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBKBBBBKBBBBBBBK.....",
    "....KWWKBBBBKBBKBBBBK.....",
    "....KWWKBBBBKBBKBBBBK.....",
    "....KKKKBBBBKBBKBBBBK.....",
    ".....KBBBBBBKWWKBBBBK.....",
    ".....KBBBBBBKWWKWWBBK.....",
    "...KKKKKKKBBKKKKKKKKK.....",
    "...KggggggKKKKKggggggK....",
    "..KggggggGGKKKggggggGGK...",
    "..KGGGGGGGGK.KGGGGGGGGK...",
    "...KKKKKKKK...KKKKKKKK....",
    "..........................",
    "..........................",
]

# ------------------------------------- reaching for the paper roll (scroll) --
KNEAD_A = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    ".KKKKBBBBBBBBBBBBBBK......",
    ".KWWBBBBBBBBBBBBBBBBK.....",
    ".KWWBBKBBBBBBBBBBBBBK.....",
    ".KKKKBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBWWKBBKBBBK..",
    "..KBBBBKBBBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

KNEAD_B = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    ".KKKKBBBBBBBBBBBBBBBK.....",
    ".KWWBBBBBBBBBBBBBBBBK.....",
    ".KWWBBKBBBBBBBBBBBBBBK....",
    ".KKKKBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBWWKBBKBBBK..",
    "..KBBBBKBBBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

# ---------------------------------------------------------------- sleeping ---
SLEEP = [
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    ".......KK........KK.......",
    "......KBBK......KBBK......",
    "......KBZBK....KBZBK......",
    ".....KBBBBBKKKKBBBBBK.....",
    ".....KBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBBBK....",
    "....KBKKKBBBBBBBBKKKBK....",
    ".HHKBBBBBBBNNBBBBBBBBBK...",
    "...KBBBBBBBMMBBBBBBBBBKK..",
    ".HHKBBBBBBBBBBBBBBBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBK...",
    "..KBKKKBBBBBBBBBBBBBBBK...",
    "..KKBBBKKBBBBBBBBBBBBK....",
    "...KBBBBBKKKKKKKKKKKK.....",
    "....KKKKKKKKKKKKKKK.......",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
]

# ------------------------------------------------ hunting run (chase) -------
# compact happy gallop: two front paws reaching, two back feet — NOT a spider
RUN_A = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    ".HHKBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBK.K...",
    "...KBBBBBBBBBBBBBBBBKKBK..",
    "....KBBBBBBBBBBBBBBKKBK...",
    "...KBBBBBBBBBBBBBBBKKK....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBKWWKBBBBBBKWWKK.....",
    "....KBKWWKBBBBBBKWWKK.....",
    ".....KBKKBBBBBBBBKKK......",
    ".....KWWKBBBBBBKWWK.......",
    "......KKKKKKKKKKKK........",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
]

RUN_B = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    ".HHKBEEEBBBNNBBBEEEBKHH...",
    "...KBBBBBBBMMBBBBBBBKK....",
    "...KBBBBBBBBBBBBBBBBKBK...",
    "....KBBBBBBBBBBBBBBKKBK...",
    "...KBBBBBBBBBBBBBBBKBK....",
    "...KBBBBBBBBBBBBBBBKK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBKWWKBBKWWKBBK.....",
    "....KBBBKWWKBBKWWKBBK.....",
    ".....KBBBKKBBBBKKBBK......",
    ".....KBWWKBBBBBBKWWK......",
    "......KKKKKKKKKKKKK.......",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
]

# --------------------------------------------------------------- stretching --
STRETCH = [
    "..........................",
    "...........KWWK...........",
    "..........KWWWWK..........",
    "..........KBKKBK..........",
    "..........KBKKBK..........",
    ".....KK...KBKKBK..KK......",
    "....KBBK..KBKKBK.KBBK.....",
    "....KBZBKKKBKKBKKBZBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBBBBBBBBBBBBBBBBKHH...",
    "...KBKKKBBBBBBBBKKKBK.....",
    "...KBBBBBBBNNBBBBBBBK.....",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.KK....",
    ".....KBBBBBBBBBBBBKKBBK...",
    ".....KBBBBBBBBBBBBKKBK....",
    ".....KBBBBBBBBBBBKKBK.....",
    ".....KWWBKBBBBKWWKKK......",
    "......KWWK....KWWK........",
    ".......KK......KK.........",
    "..........................",
]

# ------------------------------------------------------- dangling (drag) -----
DANGLE = [
    "..........................",
    "...........KWWK...........",
    "..........KWWWWK..........",
    "..........KBKKBK..........",
    "..........KBKKBK..........",
    ".....KK...KBKKBK..KK......",
    "....KBBK..KBKKBK.KBBK.....",
    "....KBZBKKKBKKBKKBZBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBEEEBBBNNBBBEEEBK.....",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.......",
    ".....KBBBBBBBBBBBBK.KK....",
    ".....KBBBBBBBBBBBBKKBBK...",
    ".....KBBBBBBBBBBBBKKBK....",
    ".....KBBBBBBBBBBBKKBK.....",
    ".....KWWBKBBBBKWWKKK......",
    "......KWWK....KWWK........",
    ".......KK......KK.........",
    "..........................",
    "..........................",
]

# ------------------------------------------------------------- peeking -------
PEEK = [
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KWWKBBBBBBBBBBBBKWWK....",
    "..KKKKKKKKKKKKKKKKKKKK....",
    "..........................",
    "..........................",
]

YAWN = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBBBBBBBBBBBBBBBBKHH...",
    "...KBKKKBBBBBBBBKKKBK.....",
    ".HHKBBBBBBBNNBBBBBBBKHH...",
    "...KBBBBBBBKMMKBBBBBK.....",
    "...KBBBBBBBKMMKBBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBBK..",
    "..KBBBBKWWBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

GROOM_A = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBBBBBBBBBBBBBBBBKHH...",
    "...KBKKKBBBBBBBBKKKBK.....",
    ".HHKBBBBBBBNNBBBBBBBKHH...",
    "...KBBBBBZBMMBBBBBBBK.....",
    "...KBBKWWKBBBBBBBBBBK.....",
    "....KBKWWKBBBBBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBWWKBBKBBBK..",
    "..KBBBBKBBBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

GROOM_B = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    ".HHKBBBBBBBBBBBBBBBBKHH...",
    "...KBKKKBBBBBBBBKKKBK.....",
    ".HHKBBBBBBBNNBBBBBBBKHH...",
    "...KBBBBBBBMMBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "....KBKWWKBBBBBBBBBK......",
    "....KBKWWKBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBWWKBBKBBBK..",
    "..KBBBBKBBBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

KNEAD_C = [
    "..........................",
    "..........................",
    "......KK........KK........",
    ".....KBBK......KBBK.......",
    ".....KBZBK....KBZBK.......",
    "....KBBBBBKKKKBBBBBK......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBEEEBBBBBBBBEEEBKHH...",
    "...KBEEEBBBBBBBBEEEBK.....",
    "...KBEEEBBBNNBBBEEEBKHH...",
    ".KWWKBBBBBBMMBBBBBBBK.....",
    ".KWWKBBBBBBBBBBBBBBBK.....",
    "..KBBKBBBBBBBBBBBBBK......",
    "...KBKBBBBBBBBBBBBBK......",
    ".....KBBBBBBBBBBBBBBK.....",
    "......KBBBBBBBBBBBBBK.....",
    ".....KBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBKK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBWWKBBKBBBK..",
    "..KBBBBKBBBKKBWWKBKBBBBK..",
    "...KKKKKKKKKKKKKKKKKKKK...",
    "..........................",
    "..........................",
]

# Dedicated Dog / Pup Sprites: Floppy/pointed ears, snout with white muzzle & nose, wagging tail
DOG_SIT_A = [
    "..........................",
    "..........................",
    "....KKKK........KKKK......",
    "...KBBBBK......KBBBBK.....",
    "...KBBZZBK....KBZZBBK.....",
    "...KBBZZBK....KBZZBBK.....",
    "....KBBBBBK..KBBBBBK......",
    "....KBBBBBBKKBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBEEEBBBBBBEEEBBK.....",
    "...KBEEEEBBBBBBEEEEBK.....",
    "...KBBEEEBBWWBBEEEBBK.....",
    "....KBBBBWWNNWWBBBBK......",
    "....KBBBBWWMMWWBBBBK......",
    ".....KBBBBWWWWBBBBK.......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK.KK.",
    "..KBBBBKBBBBBBBBKBBBBKBKK.",
    "..KBBBBKBBBBBBBBKBBBKKBBK.",
    "..KBBBBKBBBKKBBBKBBKBBBK..",
    "..KBBBBKWWBKKBWWKBBKBBK...",
    "..KBBBBKWWBKKBWWKBKBBK....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "..........................",
    "..........................",
]

DOG_SIT_B = [
    "..........................",
    "..........................",
    "....KKKK........KKKK......",
    "...KBBBBK......KBBBBK.....",
    "...KBBZZBK....KBZZBBK.....",
    "...KBBZZBK....KBZZBBK.....",
    "....KBBBBBK..KBBBBBK......",
    "....KBBBBBBKKBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBEEEBBBBBBEEEBBK.....",
    "...KBEEEEBBBBBBEEEEBK.....",
    "...KBBEEEBBWWBBEEEBBK.....",
    "....KBBBBWWNNWWBBBBK......",
    "....KBBBBWWMMWWBBBBK......",
    ".....KBBBBWWWWBBBBK.......",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK.KK.",
    "..KBBBBKBBBBBBBBKBBBBKBKK.",
    "..KBBBBKBBBBBBBBKBBBKKBBK.",
    "..KBBBBKBBBBBBBBKBBKBBBK..",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBK...",
    "..KBBBBKWWBKKBWWKBKBBK....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "..........................",
    "..........................",
]

# ---------------------------------------------------------------------------
# Dedicated Pokémon Pixel Sprites: Pikachu, Charmander, Gengar, and Eevee
# 26 wide x 28 tall authentic retro sprites with idle and action/wag frames
# ---------------------------------------------------------------------------
PIKACHU_IDLE = [
    "..........................",
    "...KK..............KK.....",
    "..KBBK............KBBK....",
    "..KBKKK..........KKKBK....",
    "..KBBKKK........KKKBBK....",
    "..KBBBBK........KBBBBK....",
    "...KBBBBK......KBBBBK.....",
    "...KBBBBKKKKKKKKBBBBK.....",
    "....KBBBBBBBBBBBBBBK......",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBEEEBBBBBBBBEEEBBK....",
    "..KBBPEEBBBBBBBBPEEBBK....",
    "..KZZBEEBBBNNBBBBEEBZZK...",
    "..KZZBBBBBBMMBBBBBBZZK....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBBBBBBBBBBBBBBBKKK..",
    "..KBBBBKBBBBBBBBKBBBBKBK..",
    "..KBBBBKBBBBBBBBKBBBKKBBK.",
    "..KBBBBKBBBBBBBBKBBKBBBKK.",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKK.....",
    "..KBBBBKWWBKKBWWKBK.......",
    "...KKKKKKKKKKKKKKKK.......",
    "..........................",
    "..........................",
]

PIKACHU_ACTION = [
    "..........................",
    "...KK..............KK.....",
    "..KBBK............KBBK....",
    "..KBKKK..........KKKBK....",
    "..KBBKKK........KKKBBK....",
    "..KBBBBK........KBBBBK.KK.",
    "...KBBBBK......KBBBBK.KBK.",
    "...KBBBBKKKKKKKKBBBBKKBBK.",
    "....KBBBBBBBBBBBBBBBKBKK..",
    "...KBBBBBBBBBBBBBBBBKK....",
    "..KBBEEEBBBBBBBBEEEBBK....",
    "..KBBPEEBBBBBBBBPEEBBK....",
    "..KZZBEEBBBNNBBBBEEBZZK...",
    "..KZZBBBBBBMMBBBBBBZZK....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "...KBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBBBBBBBBBBBBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBBBBBBKBBBBK....",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKBBBKKBBBKBBKBBK...",
    "..KBBBBKWWBKKBWWKBBKBBK...",
    "..KBBBBKWWBKKBWWKBKBBK....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "..........................",
    "..........................",
]

CHARMANDER_IDLE = [
    "..........................",
    "..........................",
    ".........KKKKKK...........",
    "........KBBBBBBK..........",
    ".......KBBBBBBBBK.........",
    "......KBBBBBBBBBBK........",
    ".....KBBZZZBBZZZBBK.......",
    ".....KBZEPZBBZEPZBK.......",
    ".....KBBZZZBBZZZBBK.......",
    ".....KBBBBBNNBBBBBK.......",
    "......KBBBBMMBBBBK........",
    ".......KBBBBBBBBK.........",
    ".......KBBBBBBBBK.........",
    "......KBBWWWWWWBBK........",
    ".....KBBBWWWWWWBBBK.......",
    ".....KBBBWWWWWWBBBK.......",
    "....KBBBBWWWWWWBBBBK.ZZ...",
    "....KBBBBWWWWWWBBBBKZSZK..",
    "....KBBBBWWWWWWBBBBKZZZK..",
    "....KBBBBKBBBBKBBBBKBKK...",
    "....KBBBBKBBBBKBBBBKBK....",
    "....KBBBBKBBBBKBBBBKK.....",
    ".....KKKKKBBBBKKKKK.......",
    ".....KWWBK....KBWWK.......",
    ".....KWWBK....KBWWK.......",
    "......KKKK....KKKK........",
    "..........................",
    "..........................",
]

CHARMANDER_ACTION = [
    "..........................",
    "..........................",
    ".........KKKKKK...........",
    "........KBBBBBBK..........",
    ".......KBBBBBBBBK.........",
    "......KBBBBBBBBBBK........",
    ".....KBBZZZBBZZZBBK.......",
    ".....KBZEPZBBZEPZBK.......",
    ".....KBBZZZBBZZZBBK.......",
    ".....KBBBBBNNBBBBBK.......",
    "......KBBBBMMBBBBK...ZZ...",
    ".......KBBBBBBBBK...KZSZK.",
    ".......KBBBBBBBBK...KZZZK.",
    "......KBBWWWWWWBBK...KBK..",
    ".....KBBBWWWWWWBBBK.KBK...",
    ".....KBBBWWWWWWBBBKKBK....",
    "....KBBBBWWWWWWBBBBKK.....",
    "....KBBBBWWWWWWBBBBK......",
    "....KBBBBWWWWWWBBBBK......",
    "....KBBBBKBBBBKBBBBK......",
    "....KBBBBKBBBBKBBBBK......",
    "....KBBBBKBBBBKBBBBKK.....",
    ".....KKKKKBBBBKKKKK.......",
    ".....KWWBK....KBWWK.......",
    ".....KWWBK....KBWWK.......",
    "......KKKK....KKKK........",
    "..........................",
    "..........................",
]

GENGAR_IDLE = [
    "..........................",
    "....KK..............KK....",
    "...KZZK............KZZK...",
    "...KZZZK..........KZZZK...",
    "....KZZZK........KZZZK....",
    "....KBBBBKKKKKKKKBBBBK....",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBEEBBBBBBBBBBBBEEBBK..",
    "..KBPEEBZZZZZZZZZZBPEEBK..",
    "..KBEEBBBBBBBBBBBBBBEEBK..",
    "..KBBBBWWWWWWWWWWWWBBBBK..",
    "..KBBBBWWMWMWMWMWMMBBBBK..",
    "..KBBBBWWWWWWWWWWWWBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBKKBBBBBBKKBBBBK...",
    "...KBBBK..KBBBBK..KBBBK...",
    "....KKK....KKKK....KKK....",
    "..........................",
    "..........................",
    "..........................",
]

GENGAR_ACTION = [
    "..........................",
    "....KK..............KK....",
    "...KZZK............KZZK...",
    "...KZZZK..........KZZZK...",
    "....KZZZK........KZZZK....",
    "....KBBBBKKKKKKKKBBBBK....",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBEEEBBBBBBBBBBEEEBBK..",
    "..KBPEEEBZZZZZZZZZBPEEEBK.",
    "..KBEEEBBBBBBBBBBBBEEEBK..",
    "..KBBBBWWWWWWWWWWWWBBBBK..",
    "..KBBBBWWMWMWMWMWMMBBBBK..",
    "..KBBBBWWWWWWWWWWWWBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "..KBBBBBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBKKBBBBBBKKBBBBK...",
    "...KBBBK..KBBBBK..KBBBK...",
    "....KKK....KKKK....KKK....",
    "..........................",
    "..........................",
    "..........................",
]

EEVEE_IDLE = [
    "..........................",
    "...KK................KK...",
    "..KZZK..............KZZK..",
    "..KZZZK............KZZZK..",
    "..KZZZZK..........KZZZZK..",
    "...KZZZZK........KZZZZK...",
    "...KBBZZZK......KZZZBBK...",
    "....KBBBBKKKKKKKKBBBBK....",
    "....KBBBBBBBBBBBBBBBBK....",
    "...KBBEEEEBBBBBBEEEEBBK...",
    "...KBPEEEEBBBBBBPEEEEBK...",
    "...KBBEEEEBBBNNBBEEEEBK...",
    "....KBBBBBWWMMWWBBBBK.....",
    "....KWWWWWWWWWWWWWWWWK....",
    "...KWWWWWWWWWWWWWWWWWWK...",
    "..KWWWWWWWWWWWWWWWWWWWWK..",
    "..KWWWWWWWWWWWWWWWWWWWWK..",
    "...KBBBBWWWWWWWWWWBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK.KK",
    "...KBBBBKBBBBBBBBKBBBKKBWK",
    "...KBBBBKBBBBBBBBKBBKKBWWK",
    "...KBBBBKBBBKKBBBKBBKKBWK.",
    "...KBBBBKWWBKKBWWKBBKK....",
    "...KBBBBKWWBKKBWWKBK......",
    "....KKKKKKKKKKKKKKK.......",
    "..........................",
]

EEVEE_ACTION = [
    "..........................",
    "...KK................KK...",
    "..KZZK..............KZZK..",
    "..KZZZK............KZZZK..",
    "..KZZZZK..........KZZZZK..",
    "...KZZZZK........KZZZZK...",
    "...KBBZZZK......KZZZBBK...",
    "....KBBBBKKKKKKKKBBBBK.KK.",
    "....KBBBBBBBBBBBBBBBBKBWK.",
    "...KBBEEEEBBBBBBEEEEKBWWK.",
    "...KBPEEEEBBBBBBPEEEKBWWK.",
    "...KBBEEEEBBBNNBBEEKBKWWK.",
    "....KBBBBBWWMMWWBBBKKBWK..",
    "....KWWWWWWWWWWWWWWWKK....",
    "...KWWWWWWWWWWWWWWWWWWK...",
    "..KWWWWWWWWWWWWWWWWWWWWK..",
    "..KWWWWWWWWWWWWWWWWWWWWK..",
    "...KBBBBWWWWWWWWWWBBBBK...",
    "...KBBBBBBBBBBBBBBBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK...",
    "...KBBBBKBBBBBBBBKBBBBK...",
    "...KBBBBKBBBKKBBBKBBKBBK..",
    "...KBBBBKWWBKKBWWKBBKBBK..",
    "...KBBBBKWWBKKBWWKBKBBK...",
    "....KKKKKKKKKKKKKKKKKK....",
    "..........................",
]

FRAMES = {
    "sit_a": SIT_A, "sit_b": SIT_B, "blink": BLINK,
    "type_a": TYPE_A, "type_b": TYPE_B,
    "knead_a": KNEAD_A, "knead_b": KNEAD_B,
    "sleep": SLEEP, "run_a": RUN_A, "run_b": RUN_B,
    "stretch": STRETCH, "dangle": DANGLE, "peek": PEEK,
    "yawn": YAWN,
    "groom_a": GROOM_A, "groom_b": GROOM_B, "knead_c": KNEAD_C,
    "dog_sit_a": DOG_SIT_A, "dog_sit_b": DOG_SIT_B, "dog_wag": DOG_SIT_B, "dog_listen": DOG_SIT_A,
    "pikachu_idle": PIKACHU_IDLE, "pikachu_wag": PIKACHU_ACTION,
    "charmander_idle": CHARMANDER_IDLE, "charmander_flame": CHARMANDER_ACTION,
    "gengar_idle": GENGAR_IDLE, "gengar_glow": GENGAR_ACTION,
    "eevee_idle": EEVEE_IDLE, "eevee_wag": EEVEE_ACTION
}

EYE_CELLS = {
    "sit_a": [(5, 8), (16, 8)], "sit_b": [(5, 8), (16, 8)],
    "type_a": [(4, 7), (15, 7)], "type_b": [(4, 7), (15, 7)],
    "knead_a": [(5, 8), (16, 8)], "knead_b": [(5, 8), (16, 8)],
    "run_a": [(5, 8), (16, 8)], "run_b": [(5, 8), (16, 8)],
    "knead_c": [(5, 8), (16, 8)],
    "dangle": [(5, 10), (16, 10)], "peek": [(5, 20), (16, 20)],
    "dog_sit_a": [(5, 10), (16, 10)], "dog_sit_b": [(5, 10), (16, 10)], "dog_wag": [(5, 10), (16, 10)],
    "pikachu_idle": [(5, 11), (16, 11)], "pikachu_wag": [(5, 11), (16, 11)],
    "charmander_idle": [(6, 7), (14, 7)], "charmander_flame": [(6, 7), (14, 7)],
    "gengar_idle": [(4, 9), (16, 9)], "gengar_glow": [(4, 9), (16, 9)],
    "eevee_idle": [(5, 10), (15, 10)], "eevee_wag": [(5, 10), (15, 10)]
}

HEAD_RECT = (3, 2, 22, 13)
# the peek pose draws just a head poking up near the BOTTOM of the 26x28
# grid (see PEEK below) — HEAD_RECT (top-of-grid) misses it entirely.
PEEK_HEAD_RECT = (1, 14, 25, 26)
SCROLL_ROLL = (2, 18)           # roll sits under the reaching paw
SIT_A_REF = SIT_A
SIT_A = SIT_A                   # tray icon uses this

PALETTES = {
    "mimi": {"B": "#ded5c6", "S": "#8a7c68", "W": "#f7f3ea",
             "K": "#4a4238", "E": "#f8f8f4", "N": "#b5744f",
             "M": "#4a4238", "Z": "#d9b09a", "P": "#4f7da8"},
    "jj": {"B": "#96896e", "S": "#453e32", "W": "#f1ebdd",
           "K": "#2f2a24", "E": "#f8f8f4", "N": "#c06a3f",
           "M": "#2f2a24", "Z": "#d9a58f", "P": "#4f7d42"},
    "lilly": {"B": "#efa75a", "S": "#d8853a", "W": "#f7f2e8",
              "K": "#503219", "E": "#f8f8f4", "N": "#e78a8a",
              "M": "#503219", "Z": "#f2b8ac", "P": "#3c5240"},
    "orange tabby": {"B": "#e8963c", "S": "#c9752a", "W": "#f6ead8", "K": "#4a2f1a",
                     "E": "#f8f8f4", "N": "#e06a7c", "M": "#4a2f1a", "Z": "#eeb0a0", "P": "#2c3138"},
    "gray":         {"B": "#8b8f98", "S": "#6e727c", "W": "#e8e8ea", "K": "#33353b",
                     "E": "#f8f8f4", "N": "#d98794", "M": "#33353b", "Z": "#d9a8a8", "P": "#26282e"},
    "black":        {"B": "#26262b", "S": "#1e1e22", "W": "#e8e8ea", "K": "#0f0f12",
                     "E": "#f8f8f4", "N": "#d98794", "M": "#0e0e10", "Z": "#a87d7d", "P": "#101013"},
    "white":        {"B": "#f2efe8", "S": "#e0dacd", "W": "#ffffff", "K": "#8a8378",
                     "E": "#fbfbf8", "N": "#e79aa6", "M": "#8a8378", "Z": "#efb9b0", "P": "#33383f"},
    "calico":       {"B": "#efe6d6", "S": "#d88a3a", "W": "#ffffff", "K": "#584134",
                     "E": "#f8f8f4", "N": "#e06a7c", "M": "#584134", "Z": "#eeb0a0", "P": "#2c3138"},
    "cream":        {"B": "#f0dfc0", "S": "#dcc49a", "W": "#fdf8ee", "K": "#6e5a42",
                     "E": "#f8f8f4", "N": "#e79aa6", "M": "#6e5a42", "Z": "#f0bcae", "P": "#33383f"},
    "chocolate":    {"B": "#6b4a35", "S": "#583b28", "W": "#e9ddd0", "K": "#2e1e13",
                     "E": "#f8f8f4", "N": "#d98794", "M": "#2e1e13", "Z": "#c99486", "P": "#1c1d21"},
    "lilac":        {"B": "#b7a8c4", "S": "#a08fb1", "W": "#f0ecf4", "K": "#4c4058",
                     "E": "#f8f8f4", "N": "#e096a4", "M": "#4c4058", "Z": "#e3b6c0", "P": "#2b2e34"},
    "pink":         {"B": "#f2b9c6", "S": "#e5a0b2", "W": "#fdf1f4", "K": "#7e4454",
                     "E": "#f8f8f4", "N": "#e06a7c", "M": "#7e4454", "Z": "#f6cfd8", "P": "#33383f"},
    "mint":         {"B": "#b4dcc8", "S": "#9ccab4", "W": "#f0faf5", "K": "#3c5f4f",
                     "E": "#f8f8f4", "N": "#e096a4", "M": "#3c5f4f", "Z": "#e0b8b2", "P": "#2b2e34"},
    "siamese":      {"B": "#ded5c6", "S": "#4a3c31", "W": "#f7f3ea", "K": "#2a2018",
                     "E": "#f8f8f4", "N": "#4a3c31", "M": "#2a2018", "Z": "#b89080", "P": "#3878b4"},
    "shiba inu":    {"B": "#d48238", "S": "#b86b24", "W": "#fdf7eb", "K": "#3d2211",
                     "E": "#f8f8f4", "N": "#221108", "M": "#3d2211", "Z": "#df9d8b", "P": "#2c1c0f"},
    "golden retriever": {"B": "#e8ba6b", "S": "#cf9d4e", "W": "#fefaf0", "K": "#4a3518",
                         "E": "#f8f8f4", "N": "#361d0f", "M": "#4a3518", "Z": "#e5ab91", "P": "#261a0f"},
    "corgi":        {"B": "#c9742c", "S": "#a85a1e", "W": "#ffffff", "K": "#381f0d",
                     "E": "#f8f8f4", "N": "#20120a", "M": "#381f0d", "Z": "#e89988", "P": "#1c1109"},
    "husky":        {"B": "#68707c", "S": "#4a515c", "W": "#f8f9fa", "K": "#22252a",
                     "E": "#a2d2ff", "N": "#1d2024", "M": "#22252a", "Z": "#dfa5a5", "P": "#0077b6"},
    "pikachu":      {"B": "#fcd116", "S": "#b57a22", "W": "#ffffff", "K": "#241e12",
                     "E": "#ffffff", "N": "#241e12", "M": "#241e12", "Z": "#e73b27", "P": "#18140c"},
    "charmander":   {"B": "#f17f29", "S": "#cf5c13", "W": "#fae19c", "K": "#33160a",
                     "E": "#ffffff", "N": "#33160a", "M": "#33160a", "Z": "#2eb4c6", "P": "#103b42"},
    "gengar":       {"B": "#6d4c87", "S": "#4a2f60", "W": "#ffffff", "K": "#1e0f2b",
                     "E": "#ef3038", "N": "#1e0f2b", "M": "#ef3038", "Z": "#9b72ba", "P": "#1e0f2b"},
    "eevee":        {"B": "#b87333", "S": "#8c5321", "W": "#faeed9", "K": "#301a0c",
                     "E": "#ffffff", "N": "#200e06", "M": "#301a0c", "Z": "#592b10", "P": "#200e06"},
}

EXTRA_COLORS = {"G": "#8a8f98", "g": "#d4d8de", "O": "#ffffff", "H": "#f2f4f6"}

OVERHEAT_PALETTE = {
    "B": "#e6483a", "S": "#d13527", "W": "#ffd9d2", "K": "#8e1a0c",
    "E": "#fdf3f1", "N": "#a41d10", "M": "#8e1a0c", "Z": "#ff9a8c", "P": "#54100a",
}

PATTERNS = ["tabby", "solid", "tuxedo", "spots", "siamese", "lilly", "jj", "mimi"]


def _spot_hash(x, y):
    return ((x * 73856093) ^ (y * 19349663)) % 100


def apply_pattern(grid, pattern, head_only=False):
    if pattern in (None, "tabby"):
        return grid
    # head_only: the peek frame is just a head poking over an edge. Themed
    # patterns place stripes/bibs by body-row and would smear body markings
    # across the peeking face (a stripe on the forehead). A poking-out head
    # reads cleanest plain, so skip pattern recolouring entirely here — the
    # face keeps its base fur colour, no misplaced body markings.
    if head_only:
        return grid
    h, w = len(grid), len(grid[0])
    # Region markings (chin, chest bib, crown, mackerel split) are placed by
    # row fraction of the FULL grid. Compact poses that sit higher/lower than
    # a sitting cat (e.g. the curled sleep loaf, head at rows ~6-13) would get
    # body markings smeared onto the head. Guard against that below by never
    # letting a body marking land on or above the face: find the nose row (the
    # face anchor) and protect everything from there up.
    _face = [yy for yy, r in enumerate(grid) if "N" in r]
    _head_guard = (_face[0] + 1) if _face else -1     # rows <= this are head
    out = []
    for y, row in enumerate(grid):
        py = y
        new = []
        for x, ch in enumerate(row):
            c = ch
            if pattern == "solid":
                if c == "S":
                    c = "B"
            elif pattern == "spots":
                if c == "S":
                    c = "B"
                if c == "B" and _spot_hash(x, y) < 16:
                    c = "S"
            elif pattern == "tuxedo":
                if c == "S":
                    c = "B"
                if c == "B" and py >= int(h * 0.55) and w * 0.30 <= x <= w * 0.70:
                    c = "W"
                if c == "B" and h * 0.36 <= py <= h * 0.46 and w * 0.36 <= x <= w * 0.64:
                    c = "W"
            elif pattern == "lilly":
                if c == "B" and py >= int(h * 0.52) \
                        and w * 0.28 <= x <= w * 0.72:
                    c = "W"
                if c == "B" and h * 0.36 <= py <= h * 0.47 \
                        and w * 0.36 <= x <= w * 0.64:
                    c = "W"
            elif pattern == "jj":
                if c == "B" and h * 0.38 <= py <= h * 0.47 \
                        and w * 0.40 <= x <= w * 0.60:
                    c = "W"                      # white chin/muzzle
                elif c == "B" and py >= int(h * 0.58) \
                        and w * 0.40 <= x <= w * 0.60:
                    c = "W"                      # chest bib
                elif c == "B":
                    on_line = (x + (y // 3)) % 3 == 0
                    if py < h * 0.46:
                        # head: only short forehead lines, cheeks clear
                        if on_line and py < h * 0.30 \
                                and w * 0.32 <= x <= w * 0.68 \
                                and _spot_hash(x, y) > 8:
                            c = "S"
                    else:
                        # body: broken, irregular mackerel stripes
                        if on_line and _spot_hash(x, y) > 7:
                            c = "S"
            elif pattern == "mimi":
                if c == "B" and py <= int(h * 0.22):
                    c = "S"                      # dusky crown and ears
                elif c == "B" and h * 0.38 <= py <= h * 0.47 \
                        and w * 0.40 <= x <= w * 0.60:
                    c = "W"                      # white chin
                elif c == "B" and h * 0.52 <= py <= h * 0.75 \
                        and w * 0.34 <= x <= w * 0.66:
                    c = "W"                      # white chest
                elif c == "B" and py >= int(h * 0.78) and y % 3 == 1:
                    c = "S"                      # ringed paws
            elif pattern == "siamese":
                if c == "S":
                    c = "B"
                if c == "B" and (py <= 4 or py >= h - 4 or x >= w - 4):
                    c = "S"
            # head guard: on/above the nose row, don't let a body marking
            # (white chin/chest bib, or a random spot) overwrite the face —
            # keep the original fur so patterns never smear onto the head of
            # compact poses like the curled sleep loaf. Deliberate head marks
            # (JJ forehead lines, mimi crown) are placed by head-region logic
            # and stay; this only reverts B->W/spot bleed above the nose.
            if 0 <= _head_guard and y <= _head_guard and ch == "B" \
                    and c != ch and (c == "W" or pattern == "spots"):
                c = ch
            new.append(c)
        out.append("".join(new))
    return out


def add_halo(grid):
    h, w = len(grid), len(grid[0])
    out = [list(r) for r in grid]
    solid = set("KBSWEZNMGg")
    for y in range(h):
        for x in range(w):
            if grid[y][x] != ".":
                continue
            hit = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] in solid:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                out[y][x] = "O"
    return ["".join(r) for r in out]


def render_frame(grid, palette, scale=6, flip=False, halo=True):
    from PySide6.QtGui import QImage, QColor, QPainter
    if halo:
        grid = add_halo(grid)
    img = QImage(GRID_W * scale, GRID_H * scale, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    cache = {}
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch == ".":
                continue
            col = cache.get(ch)
            if col is None:
                col = QColor(palette.get(ch)
                             or EXTRA_COLORS.get(ch, "#ff00ff"))
                cache[ch] = col
            x = (GRID_W - 1 - gx) if flip else gx
            p.fillRect(x * scale, gy * scale, scale, scale, col)
    p.end()
    return img


def render_icon(palette, pattern="tabby", scale=12, frame="sit_a"):
    """Frame render + baked-in pupils (they're normally drawn at runtime)."""
    from PySide6.QtGui import QPainter, QColor
    grid = apply_pattern(FRAMES[frame], pattern, head_only=(frame == "peek"))
    img = render_frame(grid, palette, scale)
    cells = EYE_CELLS.get(frame, [])
    p = QPainter(img)
    pc = QColor(palette["P"])
    pw = 2 * scale
    for (ex, ey) in cells:
        bx = ex * scale + (EYE_W * scale - pw) // 2
        by = ey * scale + (EYE_H * scale - pw) // 2 + scale // 3
        p.fillRect(bx, by, pw, pw, pc)
    p.end()
    return img


def render_kitty_pixmap(frame="sit_a", palette_name="orange tabby", scale=2, flip=False, is_dog=False):
    from PySide6.QtGui import QPixmap
    # If is_dog or dog palette selected, map to dog frame
    if is_dog or palette_name in ("shiba inu", "golden retriever", "corgi", "husky"):
        if frame in ("sit_b", "wag"):
            grid = FRAMES.get("dog_sit_b", DOG_SIT_B)
        else:
            grid = FRAMES.get("dog_sit_a", DOG_SIT_A)
        pal = PALETTES.get(palette_name, PALETTES.get("shiba inu"))
    elif palette_name in ("pikachu", "charmander", "gengar", "eevee"):
        is_action = frame in ("wag", "action", "sit_b", "flame", "glow")
        grid_key = f"{palette_name}_wag" if is_action else f"{palette_name}_idle"
        if palette_name == "charmander":
            grid_key = "charmander_flame" if is_action else "charmander_idle"
        elif palette_name == "gengar":
            grid_key = "gengar_glow" if is_action else "gengar_idle"
        grid = FRAMES.get(grid_key, FRAMES.get(f"{palette_name}_idle", SIT_A))
        pal = PALETTES.get(palette_name)
    else:
        grid = FRAMES.get(frame, SIT_A)
        pal = PALETTES.get(palette_name, PALETTES.get("orange tabby"))

    img = render_frame(grid, pal, scale=scale, flip=flip, halo=True)
    return QPixmap.fromImage(img)


def render_pup_pixmap(frame="dog_sit_a", palette_name="shiba inu", scale=2, flip=False):
    return render_kitty_pixmap(frame=frame, palette_name=palette_name, scale=scale, flip=flip, is_dog=True)


def render_pokemon_pixmap(pokemon_name="pikachu", frame="idle", scale=2, flip=False):
    pkmn = pokemon_name.lower().strip()
    if pkmn not in ("pikachu", "charmander", "gengar", "eevee"):
        pkmn = "pikachu"
    return render_kitty_pixmap(frame=frame, palette_name=pkmn, scale=scale, flip=flip)



# ---------------------------------------------------------------------------
# DUCK HUNT easter-egg sprites (self-contained; not part of the cat FRAMES).
# Two wing positions per duck, drawn flying to the RIGHT; flipped for left.
# Grid is 18 wide x 13 tall. Legend: . transparent, K outline, B body,
# W belly, O beak/orange, E eye-white, P pupil.
# ---------------------------------------------------------------------------
DUCK_W, DUCK_H = 18, 13

DUCK_WINGUP = [
    "..................",
    "......KK..........",
    ".....KBBK.........",
    "....KBBBBK...KKKK.",
    "....KBBBBBKKKBBBEK",
    ".....KBBBBBBBBBPKO",
    "......KBBBBBBBBKKO",
    "......KBWWWWWBBK..",
    ".......KWWWWWWK...",
    "........KKKKKK....",
    "..................",
    "..................",
    "..................",
]

DUCK_WINGDOWN = [
    "..................",
    "..................",
    "............KKKK..",
    "...........KBBBEK.",
    "....KKKKKKKKBBBPKO",
    "....KBBBBBBBBBBKKO",
    "....KBWWWWWWBBBK..",
    ".....KWWWWWWWBK...",
    "......KKKKKKKK....",
    ".....KBBBK........",
    "....KBBBBK........",
    ".....KBBK.........",
    "......K...........",
]

# colour variants → (body, belly) ; outline/beak/eye shared. Higher-point
# ducks are rarer (see the game code).
DUCK_PALETTES = {
    "brown": {"K": "#2b2b2b", "B": "#8a6b45", "W": "#f4ead7",
              "O": "#e8912e", "E": "#ffffff", "P": "#141414"},
    "blue":  {"K": "#20263a", "B": "#4a74c8", "W": "#dfe8fb",
              "O": "#e8912e", "E": "#ffffff", "P": "#141414"},
    "red":   {"K": "#331a1a", "B": "#c8503a", "W": "#f8ddd2",
              "O": "#ffcf3a", "E": "#ffffff", "P": "#141414"},
}


def render_duck(wing_down=False, color="brown", scale=4, flip=False):
    """Render a duck frame to a QImage. flip=True → facing left."""
    from PySide6.QtGui import QImage, QColor, QPainter
    grid = DUCK_WINGDOWN if wing_down else DUCK_WINGUP
    pal = DUCK_PALETTES.get(color, DUCK_PALETTES["brown"])
    img = QImage(DUCK_W * scale, DUCK_H * scale, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    cache = {}
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch == "." or gx >= DUCK_W:
                continue
            col = cache.get(ch)
            if col is None:
                col = QColor(pal.get(ch, "#ff00ff"))
                cache[ch] = col
            x = (DUCK_W - 1 - gx) if flip else gx
            p.fillRect(x * scale, gy * scale, scale, scale, col)
    p.end()
    return img


# ---------------------------------------------------------------------------
# Tiny 3x5 pixel font for the Duck Hunt arcade score panel. Each glyph is 5
# rows of 3 chars ('#'=on). Only the characters we actually display.
# ---------------------------------------------------------------------------
PIXFONT = {
    "0": ["###", "# #", "# #", "# #", "###"],
    "1": [" # ", "## ", " # ", " # ", "###"],
    "2": ["###", "  #", "###", "#  ", "###"],
    "3": ["###", "  #", "###", "  #", "###"],
    "4": ["# #", "# #", "###", "  #", "  #"],
    "5": ["###", "#  ", "###", "  #", "###"],
    "6": ["###", "#  ", "###", "# #", "###"],
    "7": ["###", "  #", "  #", "  #", "  #"],
    "8": ["###", "# #", "###", "# #", "###"],
    "9": ["###", "# #", "###", "  #", "###"],
    "H": ["# #", "# #", "###", "# #", "# #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "G": ["###", "#  ", "# #", "# #", "###"],
    "S": ["###", "#  ", "###", "  #", "###"],
    "C": ["###", "#  ", "#  ", "#  ", "###"],
    "O": ["###", "# #", "# #", "# #", "###"],
    "R": ["###", "# #", "###", "## ", "# #"],
    "E": ["###", "#  ", "###", "#  ", "###"],
    "B": ["## ", "# #", "## ", "# #", "## "],
    "D": ["## ", "# #", "# #", "# #", "## "],
    "K": ["# #", "## ", "#  ", "## ", "# #"],
    "L": ["#  ", "#  ", "#  ", "#  ", "###"],
    "N": ["# #", "###", "###", "###", "# #"],
    "Q": ["###", "# #", "# #", "###", "  #"],
    "T": ["###", " # ", " # ", " # ", " # "],
    "U": ["# #", "# #", "# #", "# #", "###"],
    "W": ["# #", "# #", "###", "###", "# #"],
    "X": ["# #", "# #", " # ", "# #", "# #"],
    "A": ["###", "# #", "###", "# #", "# #"],
    "P": ["###", "# #", "###", "#  ", "#  "],
    "V": ["# #", "# #", "# #", "# #", " # "],
    "Y": ["# #", "# #", "###", " # ", " # "],
    # The alphabet was missing F, J, M and Z. draw_pixel_text falls back to a
    # SPACE for any glyph it doesn't know, silently — so "BLACKJACK" rendered
    # as "BLACK ACK" and a Jack card had a blank rank. Completed here.
    "F": ["###", "#  ", "###", "#  ", "#  "],
    "J": ["  #", "  #", "  #", "# #", "###"],
    "M": ["# #", "###", "###", "# #", "# #"],
    "Z": ["###", "  #", " # ", "#  ", "###"],
    ".": ["   ", "   ", "   ", "   ", " # "],
    "!": [" # ", " # ", " # ", "   ", " # "],
    " ": ["   ", "   ", "   ", "   ", "   "],
}


def draw_pixel_text(painter, text, x, y, px, color, shadow=None):
    """Draw `text` as chunky 3x5 pixel glyphs. `px` = pixel cell size.
    Returns the total width drawn. Uses QPainter fillRect (no font)."""
    from PySide6.QtCore import QRect
    gap = px                       # 1-cell gap between glyphs
    cx = x
    for ch in text.upper():
        glyph = PIXFONT.get(ch, PIXFONT[" "])
        for ry, row in enumerate(glyph):
            for rxi, c in enumerate(row):
                if c == "#":
                    if shadow is not None:
                        painter.fillRect(cx + rxi * px + px, y + ry * px + px,
                                         px, px, shadow)
                    painter.fillRect(cx + rxi * px, y + ry * px,
                                     px, px, color)
        cx += 3 * px + gap
    return cx - x - gap


def pixel_text_width(text, px):
    return len(text) * (3 * px + px) - px


# ---------------------------------------------------------------------------
# Rock / Paper / Scissors minigame icons (12x12, '#' = filled).
# ---------------------------------------------------------------------------
RPS_ROCK = [
    "....####....",
    "..########..",
    ".##########.",
    "############",
    "############",
    "############",
    "############",
    "############",
    ".##########.",
    "..########..",
    "....####....",
    "............",
]
RPS_PAPER = [
    ".#########..",
    ".#........#.",
    ".#........#.",
    ".#..####..#.",
    ".#........#.",
    ".#..####..#.",
    ".#........#.",
    ".#..####..#.",
    ".#........#.",
    ".#........#.",
    ".#########..",
    "............",
]
RPS_SCISSORS = [
    "##.......##.",
    "###.....###.",
    ".###...###..",
    "..###.###...",
    "...#####....",
    "....###.....",
    "...#####....",
    "..##.#.##...",
    ".##..#..##..",
    ".#...#...#..",
    ".....#......",
    "............",
]
RPS_ICONS = {"rock": RPS_ROCK, "paper": RPS_PAPER, "scissors": RPS_SCISSORS}
RPS_COLORS = {"rock": "#c8b496", "paper": "#e8e8ee", "scissors": "#b4c8e6"}


def draw_rps_icon(painter, kind, x, y, px, color=None):
    """Draw a 12x12 RPS icon with pixel cells of size px."""
    from PySide6.QtGui import QColor
    grid = RPS_ICONS.get(kind)
    if grid is None:
        return
    col = QColor(color or RPS_COLORS.get(kind, "#ffffff"))
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch == "#":
                painter.fillRect(x + gx * px, y + gy * px, px, px, col)


# ---------------------------------------------------------------------------
# Card suits for the Blackjack minigame (7x7, '#' = filled).
# Hand-drawn pixel cells rather than the ♠♥♦♣ unicode glyphs on purpose: the
# app also runs on Linux, where the Segoe UI Symbol / emoji fonts the RPS panel
# leans on are not guaranteed to exist. fillRect always works.
# ---------------------------------------------------------------------------
SUIT_SPADE = [
    "...#...",
    "..###..",
    ".#####.",
    "#######",
    "#######",
    "...#...",
    ".#####.",
]
SUIT_HEART = [
    ".##.##.",
    "#######",
    "#######",
    "#######",
    ".#####.",
    "..###..",
    "...#...",
]
SUIT_DIAMOND = [
    "...#...",
    "..###..",
    ".#####.",
    "#######",
    ".#####.",
    "..###..",
    "...#...",
]
SUIT_CLUB = [
    "..###..",
    ".#####.",
    "#######",
    "#######",
    "..###..",
    "...#...",
    ".#####.",
]

SUITS = {"S": SUIT_SPADE, "H": SUIT_HEART,
         "D": SUIT_DIAMOND, "C": SUIT_CLUB}
SUIT_W = 7          # cells; pixel width at cell size px is SUIT_W * px


def draw_suit(painter, suit, x, y, px, color):
    """Draw a 7x7 suit pip with pixel cells of size px. `suit` is one of
    S H D C. Mirrors draw_rps_icon: no font, no antialiasing, just fillRect."""
    from PySide6.QtGui import QColor
    grid = SUITS.get(suit)
    if grid is None:
        return
    col = QColor(color)
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch == "#":
                painter.fillRect(x + gx * px, y + gy * px, px, px, col)
