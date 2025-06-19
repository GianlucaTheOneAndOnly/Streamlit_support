# Outil de Diagnostic Réseau

Une application Streamlit pour faciliter les opérations de diagnostic sur les gateways réseau.

## Fonctionnalités

- **Diagnostic Individuel**: Exécuter des commandes sur une seule gateway
- **Diagnostic par Lots**: Exécuter des commandes sur plusieurs gateways simultanément
- **Historique de Commandes**: Accès rapide aux commandes précédemment utilisées
- **Personnalisation**: Filtrage par type d'équipement et catégorie

## Structure du Projet

```
.
├── app.py                  # Point d'entrée principal
├── pages/                  # Dossier contenant les pages de l'application
│   ├── __init__.py         # Fichier pour marquer le dossier comme un package Python
│   ├── individual_diagnostic.py  # Page de diagnostic individuel
│   └── batch_diagnostic.py       # Page de diagnostic par lots
└── README.md               # Ce fichier
```

## Installation

1. Assurez-vous que Python 3.7+ est installé
2. Installez les dépendances:

```bash
pip install streamlit pandas
```

## Exécution

Pour lancer l'application:

```bash
streamlit run app.py
```

L'application sera accessible à l'adresse http://localhost:8501 dans votre navigateur.

## Utilisation

### Page de Diagnostic Individuel

1. Sélectionnez le type d'équipement (OLD, NEXT ou all)
2. Entrez l'identifiant unique (UID) de la gateway
3. Utilisez les commandes spécifiques à l'UID ou parcourez les commandes par catégorie
4. Filtrez les commandes à l'aide de la barre de recherche
5. Cliquez sur "Préparer & Ajouter à l'historique" pour copier une commande

### Page de Diagnostic par Lots

1. Entrez une liste de numéros de série de gateways (un par ligne) ou téléchargez un fichier texte
2. Sélectionnez une commande à exécuter pour toutes les gateways
3. Consultez les commandes générées et ajoutez-les à l'historique ou téléchargez-les comme fichier batch
4. Gérez la table de correspondance entre numéros de série et adresses MAC

### Historique des Commandes

L'historique des commandes est accessible via la barre latérale et peut être:
- Consulté
- Effacé
- Téléchargé au format JSON

## Personnalisation

Pour ajouter de nouvelles commandes, modifiez la liste `commands_data` dans le fichier `pages/individual_diagnostic.py`.