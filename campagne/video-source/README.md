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

## Film « Elle s'était oubliée »

```bash
python3 render_story.py 39 img . ../videos/elle-s-etait-oubliee-39s.mp4
python3 render_story.py 15 img . ../videos/elle-s-etait-oubliee-15s.mp4
```

Plans de vie : `s1` (reflet), `s3` (bougies), `s4`, `s6`, `s7` (rituel), `s9` (nouveau regard). Les recadrages 9:16 (`box`), l'étalonnage et les durées se règlent dans `SCENES` ; voix off et textes dans `SUBS` et `TITLES`.
