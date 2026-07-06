# cisco-nxapi-wrapper

## Reset de Switch

Un switch sur NX-OS antérieur à 10.0 peut se réinitialiser de la façon suivante:

### Réinitialisation du mot de passe

1. Eteindre le switch, et s'y connecter en serial
2. Appuyer sur CTRL+C continuellement pendant le boot
3. Une fois sur le loader taper la commande 
```
loader > cmdline recoverymode=1
```
4. Identifier avec `dir` l'image de nxos sur laquelle boot (la plus récente, pas les versions `cs`)
5. Utiliser la commande `boot nxos.<version>.bin` pour booter sur nxos
6. Sur le mode `boot` du switch
```
switch(boot)# conf t
switch(boot)(config)# admin-password <mot de passe>
switch(boot)(config)# exit
switch(boot)# load-nxos
```
7. Se connecter avec le username `admin` et le mot de passe choisi.

> **A NOTER** que le démarrage peut prendre du temps, la configuration n'est pas immédiatement accessible.


#### Simple réinitialisation de mot de passe
Si l'on souhaite simplement modifier le mot de passe, il faut l'enregistrer dans la config
```
switch# conf t
switch(config)# username admin password <mot de passe>
switch(config)# exit
switch# copy run start
```

### Réinitailisation complète

Une fois l'accès au switch obtenu. On le réinitialise comme suit
```
switch# conf t
switch(config)# write erase
switch(config)# write erase boot
switch(config)# exit
switch# reload 
```

Au redémarrage, le switch va se charger sur le loader. Il faut démarrer sur une image de nixos en utilisant la commande `boot` (les versions disponibles sont visibles via `dir`)

Une fois fait, le switch va boucler sur son processus POAP (POwer On Auto Provisioning), il cherche une configuration accesisble sur le réseau. Il faut taper `yes` pour passer en configuration manuelle.

Procéder ensuite aux configurations manuelles classique. **Ne pas oublier l'adresse IP du port management et l'accès via ssh.**

Une fois le switch configuré. IL faut lui indiquer l'image de boot. **Sinon, le switch redémarre en loader**
```
switch# conf t
switch(config)# boot nxos.<version>.bin
switch(config)# exit
switch# copy run start
```



## Premier démarrage (Connexion HTTP sur Management)

**A NOTER**: Il est aussi possible d'immadiatemment utiliser la configuration de base en HTTPS autosigné.

Il faut s'assurer que http est bien en écoute et que le vrf est sur le port management
```
switch# conf t
switch(config)# nxapi http port 80
switch(config)# nxapi use-vrf management
```
Si besoin, sauvegarder la configuration
```
copy run start
```


## Utilisation du certificat autosigné

Le switch autosigne un certificat par défaut pour permettre une connexion HTTPS.
Il est possible d'importer un certificat de confiance

```
switch# conf t
switch(config)# nxapi certificate httpscrt certfile bootflash:certificate.crt
switch(config)# nxapi certificate httpskey keyfile bootflash:privkey.key password pass123! 
switch(config)# nxapi certificate enable
```


## NXAPI

Il existe deux types d'API:
- NXCLI qui permet d'envoyer des commandes cli au switch et de recevoir la réponse.
    > Mais cette API est lente et demande une authentification à chaque commande
- NXREST une api REST qui permet de vérifier l'état du switch et de modifier certaines configuration
    > Ces requêtes sont rapides et pratique pour le monitoring. **On utilise cette API en priorité**
    > L'API REST ne permet pas de sauvegarder la running-config et de correctement évaluer les niveaux optiques.

