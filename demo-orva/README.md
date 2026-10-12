# ORVA — démo motion design (marque fictive)

Pub verticale de 29,5 s (1080 × 1920, 30 i/s) dans le style « app promo » : point rouge qui bat, révélation du logo, recherche, flash rouge, accueil avec compteur et courbe, grille qui défile, carte « 248 k », chat, carte 3D, vitesse, « Transaction sécurisée », bâtiment isométrique, plan héros, paiement sans contact, fin en boucle.

ORVA, ses chiffres et ses personnages sont **inventés** pour la démo. Tout est dessiné par code, sans aucune image.

```bash
npm pack @fontsource/jost@5 && tar xzf fontsource-jost-*.tgz && mv package fontsource-jost-5.3.0
python3 orva.py . orva-motion-design-30s.mp4
```
