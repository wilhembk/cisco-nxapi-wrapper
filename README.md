# cisco-nxapi-wrapper


## Premier démarrage (Connexion HTTP sur Management)

Il faut s'assurer que http est bien en écoute et que le vrf est sur le port management
```
conf t
nxapi http port 80
nxapi use-vrf management
```
Si besoin, sauvegarder la configuration
```
copy run start
```


## Utilisation du certificat autosigné

Le switch autosigne un certificat par défaut pour permettre une connexion HTTPS.
Il est possible d'importer un certificat de confiance

```
conf t
nxapi certificate httpscrt certfile bootflash:certificate.crt
nxapi certificate httpskey keyfile bootflash:privkey.key password pass123! 
nxapi certificate enable
```