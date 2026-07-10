# Prélude: Cas d'usage

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

NXAPI est une **feature** a activer sur les switchs. Une fois cette feature activée, il est possible de la manipuler dans *Developer SandBox*. Dessus, il est possible de générer du code dans le langage que l'on souhaite pour scripter ses demandes d'API.  
Il faut se connecter au Switch en HTTPS sur le navigatuer pour y accéder.  

Il existe deux types d'API:
- NXCLI qui permet d'envoyer des commandes cli au switch et de recevoir la réponse.
    > Mais cette API est lente et demande une authentification à chaque commande
- NXREST une api REST qui permet de vérifier l'état du switch et de modifier certaines configuration
    > Ces requêtes sont rapides et pratique pour le monitoring. **On utilise cette API en priorité**
    > L'API REST ne permet pas de sauvegarder la running-config et de correctement évaluer les niveaux optiques.


### Endpoints

L'API dispose de plusieurs endpoints donnant des informations différentes
- `https://<ip_switch>/api/ins` est l'endpoint de **NXAPI-CLI**. Elle permet d'envoyer des commandes CLI au switch avec `POST`. Et renvoie un json de résultat. Une réponse peut mettre **3 à 5 secondes** avant d'arriver.

La requête contient donc les identfiants d'authentification et son payload:
```json
{
    "jsonrpc": "2.0",
    "method": "cli",
    "params": {
        "cmd": <Commande CLI à envoyer au switch>,
        "version": 1
    },
    "id": 1
}
```

Il y a aussi des endpoints de type `GET` qu'il est possible d'obtenir avec NXAPI-REST, et qui permet de récupérer des données du switch:
- `https://<ip_switch>/api/mo/sys.json` renvoie les informations du switch, notamment son nom, son uptime...
- `https://<ip_switch>/api/class/ethpmPhysIf.json` renvoie l'état des interfaces. Notamment si elles sont **UP** ou **DOWN** administrativement et opérationnellement.   
On peut aussi voir si les interafces sont en full ou half-duplex.
- `https://<ip_switch>/api/class/rmonEtherStats.json` renvoie les statististiques des interfaces. Il s'agit de tous les compteurs: cRC, package drop...


# Utilisation du script

Le script a pour vocation d'être un cronjob. Il prends en entrée les tests à réaliser et renvoie un sorti un fichier de log et de résultat pour faire une intervention.

## Premier démarrage

Le script est écrit en Python 3. Assurez-vous d'avoir `pip` d'installé.
1. Placez vous à la racine du projet
2. Initialisez un environnement virtuel
```bash
pip -m venv .venv
```
3. Démarrez l'environnement virtuel  

Sur **Windows**:
```powershell
.venv\bin\activate.ps1
```
Sur **Linux** ou **MacOS**:
```zsh
source .venv/activate
```

4. Installez les dépendances
```bash
python -m pip install -e
```

## Utilisation courante

<u>**Assurez-vous:**</u>
1. D'avoir **démarré votre environnement virtuel python**
2. D'avoir un fichier `.env` à la racine du projet contenant les identifiants des siwthcs à contacter:
```env
SWITCH_USER_ID="nom_d_utilisateur"
SWITCH_PASSWORD="mot_de_passe"
```
Vous pourrez ensuite le programme avec:
```
python main.py -h
```
Vous aurez le manuel qui s'affiche, avec les différents arguments

```
usage: main.py [-h] [--unused_ports N] [--half_duplex]
               [--check_transceiver {WARN,ALERT}]
               [--CRC critical_delta reference_directory_path]
               [--demo_path demo_directory_path]
               switch_ip_list log_dir_path result_dir_path

A program to maintain Cisco switched through NX-API calls

positional arguments:
  switch_ip_list        The file containing all the switch ips (separated by a
                        newline)
  log_dir_path          The directory on where to store logs of the program
  result_dir_path       The directory on where to store results of the program

options:
  -h, --help            show this help message and exit
  --unused_ports N      Check for DOWN ports unused since N days
  --half_duplex         Check for interfaces running in half duplex mode
  --check_transceiver {WARN,ALERT}
                        Check transceivers hardware and notify for issues
                        higher or equal to specified level
  --CRC critical_delta reference_directory_path
                        Check for additional cRC and Align errors according to
                        the reference directory
  --demo_path demo_directory_path
                        Enable demo and read local files instead of switch
                        API. For testing purposes only.
```

### Arguments

#### Obligatoires

- `switch_ip_list` La liste des adresses IP des switchs à monitorer, séparé par une nouvelle ligne  
- `log_dir_path` Le chemin d'accès du repertoire dans lequel stoquer les fichiers de logs
- `result_dir_path` Le chemin du repertoire dans lequel stocker les fichiers de résultats pour les interventions.

#### Optionnels

- `--unused_ports N` Vérifie l'existence de port **DOWN** qui ne sont pas administrativement down depuis plus de `N` jours.
- `--half_duplex` Vérifie l'existence d'interface **UP** qui fonctionne en half-duplex (au lieu de full-duplex)
- `--check_transceiver {WARN, ALERT}` Vérifie l'état hardware des transceivers et renvoie les erreurs satisfaisant au moins le niveau spécifié (`WARN` ou `ALERT`)
- `--CRC critical_delta reference_directory_path` Contrôle les satistiques cRC des interfaces par rapport au dossier de référence `reference_directory_path` spécifié. Affiche des erreurs **CRITICAL** si les compteurs ont augmenté d'au moins `critical_delta`
- `--demo_path demo_directory_path` Pour réaliser des tests, vérifie les valeurs renseigné dans le `demo_directory_path` plutôt que de s'adresser aux switchs.


### Exemple d'output
On exécute le programme avec
```bash
python main.py switch_ips.txt outputs/logs/ outputs/results/ --unused_ports 90 --check_transceivers WARN --half_duplex --CRC 5 references_data/
```
On obtient le résultat suivant:
```
=============[ Switch: hostname (10.10.10.1) ]=============

> The following ports are unused since 90 days
	- eth1/97
Consider unplugging or disabling them to not be notified again.

> CRITICAL: The following interfaces are running in half duplex
	- eth1/107

> The following transceivers show hahttps://github.com/mahmoud/glomrdware issues:
	- Interface: Ethernet1/2
		+ ALERT: Transceiver current exceeded the threshold ! (0.0 < 2.0)
		+ CRITICAL: Lane 1 is not plugged in !!!
		+ CRITICAL: Lane 2 is not plugged in !!!
		+ CRITICAL: Lane 3 is not plugged in !!!
		+ CRITICAL: Lane 4 is not plugged in !!!

	- Interface: Ethernet1/3
		+ ALERT: Transceiver temperature exceeded the threshold ! (67.0°C > 65.0°C)
		+ ALERT: Transceiver current exceeded the threshold ! (0.0 < 2.0)
		+ CRITICAL: Lane 1 is not plugged in !!!
		+ CRITICAL: Lane 2 is not plugged in !!!
		+ CRITICAL: Lane 3 is not plugged in !!!
		+ CRITICAL: Lane 4 is not plugged in !!!

	- Interface: Ethernet1/23
		+ WARN: Transceiver voltage exceeded the threshold ! (3.48 > 3.46)
		+ ALERT: Transceiver current exceeded the threshold ! (11.0 > 10.0)
		+ WARN: Lane 1 transfer power has exceeded the threshold ! (-7.02 < -6.0)
		+ ALERT: Lane 2 receive power has exceeded the threshold ! (7.0 > 6.99)

> The following interfaces shows additional cRC or Align errors compared to the last check
	- eth1/97 shows 3 new errors (now 61, was 58)
	- CRITICAL: eth1/99 shows 15 new errors (now 15, was 0)
	- eth1/102 shows 2 new errors (now 4, was 2)
	- CRITICAL: eth1/103 shows 20 new errors (now 20, was 34 and reset since)

================================================

=============[ Switch: hostname (10.10.10.2) ]=============
[...]
```

# Pour les développeurs

Le programme suit une logique de programmation objet qui le rend modulable:

![Vu d'ensemble du programme](program_overview.svg)


## Contacter un endpoint 

Pour ajouter un point de contacter à endpoint. On procède en 5 étapes

### Etape 1: Identification du besoin

**Questions**: 
- Est-ce qu'on peut utiliser l'API REST, ou est-ce qu'on doit plutôt utiliser l'API CLI ? 
  - Si c'est l'**API REST** on modifie la classe `NXREST-API` de `nxapi_requests.py`
  - Si c'est l'**API CLI** on modifie la classe `NXCLI-API` de `nxapi_requests.py` et on utilise la méthode `_wrap_cmd()` pour envoyer le CMD au switch
- C'est un `POST`, c'est un `GET` ?
  - Si c'est un `GET` on utilise la méthode `_get` et on renseigne le endpoint (sans le `/api`)
  - Si c'est un `POST` il faut regarder le résultat du sandbox NXAPI pour avoir une idée de la structure
- Si je modifie une configuration, est-ce que ça va avoir une incidence de synchronisation avec NDFC ?


On vérifie le format de retour du endpoint avec la sandbox de NXAPI (trouver l'ip d'un switch et s'y connecter via le navigateur)


### Etape 2: Ecriture dans le fichier de Résultat

Dans le fichier `result_file.py`

1. Créez un nouveau `Label` correspondant à ce que vous souhaitez monitorer (et ajouter dans le fichier résultat)
2. Créez un nouvel objet qui hérite de la classe abstraite `ResultOutput`. Utilisez la structure de donnée la plus propice pour récupérer les données de monitoring
3. Créez la fonction `write` de votre objet qui prend la fonction `output` en paramètre. Considérez cette fonction comme la fonction `print` qui renverra tout dans le fichier de résultat.
> Votre objet sera géré dans la classe ResultFile. La fonction d'output qui est passé en paramètre y est définie par `_output`. Vous n'avez pas besoin de la modifier.
4. Ajoutez votre objet dans la gestion du ResultFile dans le dictionaire `switch_ouputs[<ip_du_switch>][<Label du monitoring>]`. Votre objet sera automatiquement géré par `ResultFile` une fois fait.
> Il est recommandé d'utiliser la fonction `_init_dict(ip_addr)` où `ip_addr` est l'ip du switch, pour être sûr que le dictionnaire dispose bien d'une entrée correspondant au switch.
5. Si besoin, créez des méthodes pour alimenter votre objet au fur et à mesure de votre monitoring


### Etape 3: Formatage de la réponse

La réponse dun `GET` sur l'API REST est **toujours** composée d'un `"total_count"` à la racine qui contient le nombre de résultat renvoyé par le switch. S'il vaut `0`, alors il n'y a rien à traîter, et on devrait s'arrêter immédiatemment pour éviter tout plantage.

Avec [glom](https://glom.readthedocs.io/en/latest/tutorial.html) il est possible de rapidement récupérer des données formatées en `json`. Des exemples sont disponibles dans le code et sur le manuel de `glom`

Une fois la réponse correctement formaté, on peut commencer à réaliser des tests de monitoring
> Si des données utilisateurs sont nécéssaires pour pouvoir réaliser ces tests, ajourtez ces variables dans la fonction qui s'occupe de faire le monitoring


- Utiliser la variable `result` pour communiquer avec le `ResultFile` et envoyer vos résultats à l'objet de Monitoring que vous avez précédemment créé.
- Utiliser la variable `logger` pour communiquer avec le `Logger` (défini dans `utils.py`) et la méthode `log` pour logger vos actions dans le fichier de log.
> Ces objets sont créés dans `main.py` en fonction de l'input utilisateur, et passé dans les objets de connexion à NXAPI via `switch_connection.py`. Vous n'avez pas besoin de les modifier.

### Etape 4: Ajouter la fonction de monitoring à `switch_connection.py`

Comme l'objet `SwitchConnection` fait le lien entre l'API REST ou CLI, il faut que la fonction de monitoring soit accessible via cet objet.

- Si votre méthode de monitoring via de l'API REST, utilisez la variable `rest` pour faire appelle à votre fonciton
- Si votre méthode de monitoring via de l'API CLI, utilisez la variable `cli` pour faire appelle à votre fonction
> Il est recommandé d'utiliser le même nom de fonction dans SwitchConnection par rapport à celui que vous avez choisit dans les objets NXAPI pour éviter les confusions.

### Etape 5: Parser les inputs utilisateurs dans `main.py`

La librairie Python native [argparse](https://docs.python.org/3/library/argparse.html) rend cette partie très facile:

- Ajouter une option avec `parser.add_argument` (dans le `if __name__ == "__main__"` en bas du fichier)
  - Renseignez une section help pour documenter ce que fait votre monitoring
- Dans la fonction `main` définie en haut du fichier, utiliser `args` pour récupérer les données de votre argument, et faites appelle à la méthode de `SwitchConnection` précdemment définie
