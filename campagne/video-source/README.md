# Sources des vidéos publicitaires

- `render.py` : montage complet (scènes, textes, animations, fondus, grain) en 1080 × 1920, 30 i/s.
- `music.py` : musique d'ambiance et bruitages, composés par synthèse (originaux, donc sans droits à payer).
- `img/` : les plans utilisés, recadrés depuis la planche de référence fournie (sans ses textes incrustés).

## Régénérer

```bash
npm pack @fontsource/cormorant-garamond@5 @fontsource/jost@5   # polices libres (OFL)
for f in fontsource-*.tgz; do tar xzf "$f" && mv package "${f%.tgz}"; done
python3 render.py 25 img . ../videos/sorienka-masque-collagene-25s.mp4
python3 render.py 15 img . ../videos/sorienka-masque-collagene-15s.mp4
```

Prérequis : Python 3 avec Pillow et NumPy, et ffmpeg.

## Remplacer par tes vraies photos

Garde les mêmes noms de fichiers dans `img/`, puis relance les commandes : `c_sachet`, `c_hero` et `c_cta` pour le packaging réel, `c_hook`, `c_relax` et `c_texture` pour les plans de rituel, `c_water` pour le fond final. Les textes et la durée de chaque scène se règlent dans `S25` et `S15`, en haut de `render.py`.
