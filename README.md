# cisco-nxapi-wrapper


## Premier démarrage (Connexion HTTP sur Management)

Il faut s'assurer que http est bien en écoute et que le vrf est sur le port management
```
conf t
nxapi http port 80
nxapi use-vrf management
```
