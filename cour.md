# Agri ERP – Lecture complète du code

Document pédagogique pour comprendre **chaque fichier** du mini ERP Django.  
Organisation du repo (racine `agri_erp/`) :

- `manage.py` : lance les commandes Django.
- `agri_erp/` : configuration globale du projet (settings, urls, wsgi/asgi).
- `stocks/` : application métier (modèles, formulaires, vues, templates, admin, statiques).
- `db.sqlite3` : base locale SQLite (données dev).
- `README_Agri_ERP.md` : résumé rapide.

---

## Racine et configuration Django

### `manage.py`
- Lignes 1-15 : imports standard (`os`, `sys`) et fonction `main` qui prépare la variable d’environnement `DJANGO_SETTINGS_MODULE` vers `agri_erp.settings`.
- Lignes 16-24 : exécute `execute_from_command_line(sys.argv)` pour relayer toutes les commandes (`runserver`, `migrate`, `createsuperuser`, etc.).
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_erp.settings')
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
```

### `agri_erp/settings.py`
- Lignes 1-13 : en-tête généré par Django.
- Lignes 15-19 : `BASE_DIR` pointe sur la racine du projet.
- Lignes 23-31 : clé secrète (dev), `DEBUG=True`, `ALLOWED_HOSTS=[]` (aucune restriction en local).
- Lignes 35-45 : `INSTALLED_APPS` charge Django + l’app métier `stocks`.
- Lignes 47-59 : `MIDDLEWARE` standard (sécurité, sessions, CSRF, auth, messages, XFrame).
- Lignes 61-84 : configuration des templates Django (`APP_DIRS=True` permet de charger les templates dans `stocks/templates`).
- Lignes 86-93 : base de données SQLite `db.sqlite3` dans la racine.
- Lignes 96-114 : validateurs de mot de passe pour l’auth Django.
- Lignes 118-129 : internationalisation en français, timezone Paris.
- Lignes 133-137 : fichiers statiques servis via `STATIC_URL = "static/"` (les CSS sont dans `stocks/static`).
- Lignes 141-144 : clés primaires par défaut en `BigAutoField`.
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    ...
    "stocks",  # app métier
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
STATIC_URL = "static/"
```

### `agri_erp/urls.py`
- Lignes 1-22 : commentaire généré par Django.
- Lignes 23-25 : import `admin`, `include`, `path`.
- `urlpatterns` :
  - `path('admin/', admin.site.urls)` : interface d’administration.
  - `path("", include("stocks.urls"))` : toutes les routes publiques viennent de l’app `stocks`.
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("stocks.urls")),
]
```

### `agri_erp/wsgi.py` et `agri_erp/asgi.py`
- Fichiers standard pour exposer l’application aux serveurs WSGI/ASGI. Ils pointent simplement `DJANGO_SETTINGS_MODULE` vers `agri_erp.settings` et exposent l’objet `application`.

---

## Application métier `stocks`

### `stocks/models.py` — Données et logique métier
- Imports : `models` (ORM) et `Decimal` pour des montants précis.
- `TVA_STANDARD = Decimal("0.20")` : taux de TVA par défaut (20 %).

**Client**
- Classe `Client(models.Model)` : représente un client.
- `TYPES_CHOICES` : liste des valeurs autorisées (`pro` / `part`).
- Champs :
  - `nom` : texte obligatoire.
  - `email` : email unique, optionnel (`blank=True`).
  - `type_client` : champ à choix, défaut `pro`.
  - `created_at` : horodatage auto à la création.
- Meta : ordre par nom, libellés singulier/pluriel pour l’admin.
- `__str__` : affiche le nom dans l’admin et les relations.
```python
class Client(models.Model):
    TYPES_CHOICES = [("pro", "Professionnel"), ("part", "Particulier")]
    nom = models.CharField("Nom", max_length=100)
    email = models.EmailField("Email", unique=True, blank=True)
    type_client = models.CharField("Type de client", max_length=4, choices=TYPES_CHOICES, default="pro")
    created_at = models.DateTimeField("Crée le ", auto_now_add=True)
```

**Commande**
- Classe `Commande(models.Model)` : en-tête de commande.
- `STATUS_CHOICES` : brouillon / validée / livrée / annulée.
- Champs :
  - `client = ForeignKey(Client, on_delete=PROTECT, related_name="commande")` : une commande appartient à un client; `PROTECT` empêche la suppression d’un client ayant des commandes.
  - `date` : date auto à la création.
  - `status` : statut avec choix, défaut `brouillon`.
  - `tva` : taux stocké avec 2 décimales, défaut `TVA_STANDARD`.
- Meta : ordre inverse par date puis id.
- `__str__` : affiche `CMD-<id> - <client>`.
- `total_ht` (propriété) :
  - Initialise `total` à 0.
  - Boucle sur toutes les lignes liées (`self.lignes.all()` via `related_name` défini dans `LigneCommande`).
  - Additionne `ligne.valeur_ligne` (prix * quantité).
  - Retourne le total hors taxe en `Decimal`.
- `total_ttc` (propriété) :
  - Calcule `total_ht * (1 + tva)`.
  - `quantize(Decimal("0.01"))` pour arrondir à 2 décimales.
```python
class Commande(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="commande")
    date = models.DateTimeField("Date", auto_now_add=True)
    status = models.CharField("Status", max_length=10, choices=STATUS_CHOICES, default="brouillon")
    tva = models.DecimalField("TVA", max_digits=4, decimal_places=2, default=TVA_STANDARD)

    @property
    def total_ht(self):
        total = Decimal("0.00")
        for ligne in self.lignes.all():
            total += ligne.valeur_ligne
        return total

    @property
    def total_ttc(self):
        return (self.total_ht * (1 + self.tva)).quantize(Decimal("0.01"))
```

**LigneCommande**
- Classe `LigneCommande(models.Model)` : détail d’une commande pour un produit.
- Champs :
  - `commande = ForeignKey(Commande, on_delete=CASCADE, related_name="lignes")` : si la commande est supprimée, les lignes le sont aussi.
  - `produit = ForeignKey("Produit", on_delete=PROTECT)` : protège un produit utilisé.
  - `quantite = PositiveIntegerField` : quantité commandée.
  - `prix_unitaire = DecimalField` : prix unitaire saisi ou recopié du produit.
- Meta : `unique_together (commande, produit)` pour éviter deux lignes du même produit dans une commande.
- `__str__` : `"<ref> x <quantite>"`.
- `valeur_ligne` (propriété) : `prix_unitaire * quantite`.
- `save` surchargé :
  - Si aucun `prix_unitaire` n’est fourni, il prend `produit.prix`.
  - Appelle ensuite `super().save()` pour persister.
```python
class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="lignes")
    produit = models.ForeignKey("Produit", on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField("Quantité", default=1)
    prix_unitaire = models.DecimalField("Prix unitaire (€)", max_digits=10, decimal_places=2)

    @property
    def valeur_ligne(self):
        return self.prix_unitaire * self.quantite

    def save(self, *args, **kwargs):
        if not self.prix_unitaire:
            self.prix_unitaire = self.produit.prix
        super().save(*args, **kwargs)
```

**Produit**
- Classe `Produit(models.Model)` : article du catalogue.
- Champs :
  - `ref` : référence unique (code produit).
  - `nom` : libellé.
  - `prix` : prix unitaire (décimal, 2 décimales).
  - `quantite` : quantité en stock (entier, peut être négatif si on le souhaite).
  - `created_at`, `updated_at` : timestamps auto.
- Meta : tri par `ref`, libellés admin.
- `__str__` : affiche `"<ref> - <nom>"`.
- `valeur_stock` (propriété) : `prix * quantite`.
- `en_alerte(seuil)` : retourne `True` si le stock est inférieur ou égal au seuil.
```python
class Produit(models.Model):
    ref = models.CharField("Référence", max_length=20, unique=True)
    nom = models.CharField("Nom", max_length=100)
    prix = models.DecimalField("Prix unitaire (€)", max_digits=10, decimal_places=2)
    quantite = models.IntegerField("Quantité en stock", default=0)

    @property
    def valeur_stock(self):
        return self.prix * self.quantite
```

### `stocks/forms.py` — Formulaires Django
- Imports : `forms`, `inlineformset_factory`, et les modèles `Commande`, `LigneCommande`.
- `CommandeForm(forms.ModelForm)` :
  - Meta : utilise le modèle `Commande`.
  - Champs exposés dans le formulaire : `client`, `status`, `tva`.
- `LigneCommandeFormSet = inlineformset_factory(...)` :
  - Relie le parent `Commande` au modèle enfant `LigneCommande`.
  - Champs éditables : `produit`, `quantite`, `prix_unitaire`.
  - `extra=3` : 3 lignes vides proposées par défaut.
  - `can_delete=False` : pas de bouton de suppression dans ce formset.
```python
class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ["client", "status", "tva"]

LigneCommandeFormSet = inlineformset_factory(
    parent_model=Commande,
    model=LigneCommande,
    fields=["produit", "quantite", "prix_unitaire"],
    extra=3,
    can_delete=False,
)
```

### `stocks/views.py` — Contrôleurs HTTP
- Imports : helpers Django `render`, `redirect`, `get_object_or_404`, `reverse`.
- Imports applicatifs : `CommandeForm`, `LigneCommandeFormSet`, modèles `Commande`, `Produit`.
- Constante `FORMSET_PREFIX = "lignes"` : préfixe obligatoire pour que Django retrouve les données du formset dans le POST.

**`product_list(request)`**
- Récupère tous les produits triés par `ref`.
- Retourne le template `stocks/product_list.html` avec le contexte `{"produits": produits}`.

**`order_create(request)`**
- `produits_prix` : dictionnaire `{id_produit: prix}` envoyé au template pour pré-remplir les prix côté JS.
- Si `request.method == "POST"` :
  - Instancie `CommandeForm` et `LigneCommandeFormSet` avec `request.POST` + `prefix`.
  - Valide les deux formulaires.
  - Si ok : `commande = form.save()`, puis `lignes = formset.save(commit=False)` pour compléter chaque ligne avant la sauvegarde.
  - Pour chaque ligne : attache la commande (`ligne.commande = commande`), recopie le `prix_unitaire` depuis le produit si non fourni, puis `ligne.save()`.
  - Redirige vers la page de détail `order_detail` de la commande créée.
- Sinon (GET) :
  - Instancie un formulaire vide et un formset vide avec le `prefix`.
- Rend `stocks/order_form.html` avec `form`, `formset` et `prix_produits` (utilisé par le script front pour auto-remplir les prix).
```python
def order_create(request):
    produits_prix = {str(p.id): str(p.prix) for p in Produit.objects.only("id", "prix")}
    if request.method == "POST":
        form = CommandeForm(request.POST)
        formset = LigneCommandeFormSet(request.POST, prefix=FORMSET_PREFIX)
        if form.is_valid() and formset.is_valid():
            commande = form.save()
            lignes = formset.save(commit=False)
            for ligne in lignes:
                ligne.commande = commande
                if not ligne.prix_unitaire:
                    ligne.prix_unitaire = ligne.produit.prix
                ligne.save()
            return redirect(reverse("stocks:order_detail", args=[commande.id]))
    else:
        form = CommandeForm()
        formset = LigneCommandeFormSet(prefix=FORMSET_PREFIX)
    return render(request, "stocks/order_form.html", {"form": form, "formset": formset, "prix_produits": produits_prix})
```

**`order_detail(request, pk)`**
- `cmd = get_object_or_404(Commande, pk=pk)` : récupère ou renvoie 404.
- Rend `stocks/order_detail.html` avec `commande` dans le contexte pour afficher les lignes et totaux.
```python
def order_detail(request, pk: int):
    cmd = get_object_or_404(Commande, pk=pk)
    return render(request, "stocks/order_detail.html", {"commande": cmd})
```

### `stocks/urls.py` — Routage de l’app
- `app_name = "stocks"` pour l’espace de noms des URLs.
- Routes :
  - `""` → `product_list` (catalogue).
  - `"commande/nouvelle/"` → `order_create` (création).
  - `"commande/<int:pk>/"` → `order_detail` (consultation).
```python
urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("commande/nouvelle/", views.order_create, name="order_create"),
    path("commande/<int:pk>/", views.order_detail, name="order_detail"),
]
```

### `stocks/admin.py` — Interface d’administration
- Imports les modèles `Client`, `Commande`, `LigneCommande`, `Produit`.

**ProduitAdmin**
- `list_display` : colonnes visibles (ref, nom, prix, quantite, valeur_stock, created_at).
- `search_fields` : recherche par ref ou nom.
- `list_filter` : filtre par date de création.
- `ordering` : tri par ref.

**ClientAdmin**
- Colonnes : nom, email, type, created_at.
- Recherche sur nom/email, filtres sur type et date.

**LigneCommandeInline**
- `TabularInline` pour éditer les lignes directement dans l’admin d’une commande.
- `extra=1` ligne vide; `autocomplete_fields` sur produit.

**CommandeAdmin**
- Colonnes : id, client, date, statut, total_ht, total_ttc (propriétés du modèle).
- Recherche par client ou id; filtres par statut et date; tri décroissant par date.
- `inlines = [LigneCommandeInline]` pour gérer les lignes dans la même page.
- `autocomplete_fields` sur client.
```python
@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "date", "status", "total_ht", "total_ttc")
    search_fields = ("client__nom", "id")
    list_filter = ("status", "date")
    ordering = ("-date",)
    inlines = [LigneCommandeInline]
    autocomplete_fields = ("client",)
```

### Templates et front-end

**`stocks/templates/stocks/product_list.html`**
- Page catalogue.
- Charge les statiques via `{% load static %}` et les feuilles `catalogueProduit.css`.
- Affiche un bouton “Créer une nouvelle commande”.
- Tableau listant les produits (`{% for p in produits %}`) avec : ref, nom, prix, quantité, valeur stock, état.
- Alerte visuelle si `p.quantite <= 10`, sinon “OK”.
```django
{% for p in produits %}
  <tr>
    <td>{{ p.ref }}</td>
    <td>{{ p.nom }}</td>
    <td>{{ p.prix }}</td>
    <td>{{ p.quantite }}</td>
    <td>{{ p.valeur_stock }}</td>
    <td>
      {% if p.quantite <= 10 %}<span class="alert">Alerte stock</span>
      {% else %}<span class="ok">OK</span>{% endif %}
    </td>
  </tr>
{% endfor %}
```

**`stocks/templates/stocks/order_form.html`**
- Formulaire de création d’une commande.
- Utilise `catalogueProduit.css` + `orderForm.css`.
- Bloc “Détails de la commande” : rend `{{ form.as_p }}` (client, status, tva).
- Bloc “Lignes de commande” : rend les 3 formulaires du formset (`{{ formset.management_form }}` + table produits/quantités/prix).
- Bouton “Enregistrer la commande”.
- Script JS en bas de page :
  - Récupère les prix produits via `{{ prix_produits|json_script:"produits-prix-data" }}`.
  - Pour chaque ligne du formset, écoute le changement du `select` produit et pré-remplit le champ `prix_unitaire` avec le prix catalogue tant que l’utilisateur n’a pas modifié manuellement (utilise `dataset.userEdited`).
```html
{{ formset.management_form }}
<tbody>
  {% for f in formset %}
  <tr class="formset-row">
    <td>{{ f.produit }}</td>
    <td>{{ f.quantite }}</td>
    <td>{{ f.prix_unitaire }}</td>
  </tr>
  {% endfor %}
</tbody>

<script>
const productPrices = JSON.parse(document.getElementById("produits-prix-data").textContent);
rows.forEach(row => {
  const select = row.querySelector("select[name$='-produit']");
  const price = row.querySelector("input[name$='-prix_unitaire']");
  const fillPrice = () => { const p = productPrices[select.value]; if (p && !price.dataset.userEdited) price.value = p; };
  if (!price.value) fillPrice();
  select.addEventListener("change", () => { delete price.dataset.userEdited; fillPrice(); });
  price.addEventListener("input", () => price.dataset.userEdited = price.value ? "true" : undefined);
});
</script>
```

**`stocks/templates/stocks/order_detail.html`**
- Vue de confirmation/détail d’une commande.
- Affiche les métadonnées (client, date, statut, TVA).
- Liste les lignes de commande (`commande.lignes.all`) avec ref, nom, quantité, prix unitaire, total ligne.
- Affiche les totaux calculés côté modèle (`commande.total_ht`, `commande.total_ttc`).
```django
{% for l in commande.lignes.all %}
  <tr>
    <td>{{ l.produit.ref }}</td>
    <td>{{ l.produit.nom }}</td>
    <td>{{ l.quantite }}</td>
    <td>{{ l.prix_unitaire }}</td>
    <td>{{ l.valeur_ligne }}</td>
  </tr>
{% endfor %}
<p class="totaux">
  <strong>Total HT :</strong> {{ commande.total_ht }} €
  <strong>Total TTC :</strong> {{ commande.total_ttc }} €
</p>
```

### Fichiers statiques (CSS)
- `stocks/static/stocks/catalogueProduit.css` : thème global (couleurs, typographie, table responsive, badges “alerte/ok”).
- `stocks/static/stocks/orderForm.css` : styles spécifiques pour le formulaire (fieldset, inputs, bouton primaire).
- `stocks/static/stocks/orderDetail.css` : styles du détail de commande (cartouche méta, bloc totaux).

### Migrations (`stocks/migrations/0001...`, `0002...`)
- Historique de schéma généré par `makemigrations`. Crée les tables `Produit` d’abord, puis `Client`, `Commande`, `LigneCommande` avec les champs décrits plus haut.

---

## Cycle de vie d’une commande (flux applicatif)
1. L’utilisateur arrive sur `/` → `product_list` : voit le catalogue et un bouton pour créer une commande.
2. Il clique sur “Créer une nouvelle commande” → `/commande/nouvelle/` :
   - Remplit le client, statut, TVA.
   - Remplit jusqu’à 3 lignes (produit, quantité) ; le prix s’auto-remplit via le JS.
   - Soumet le formulaire : la vue valide, crée la commande + lignes, puis redirige vers le détail.
3. La page `/commande/<id>/` affiche les lignes et les totaux HT/TTC calculés côté modèle.
4. En parallèle, l’admin Django (`/admin/`) permet de gérer produits, clients, commandes et lignes avec recherche/filtre/inline.

---

## Points clés à expliquer en entretien
- **Séparation des responsabilités** : modèles (données + logique métier), formulaires (validation), vues (flux), templates (présentation), admin (back-office).
- **Calculs métier encapsulés** dans les modèles (`valeur_stock`, `valeur_ligne`, `total_ht`, `total_ttc`) pour éviter de dupliquer la logique.
- **Formset inline** pour créer plusieurs lignes de commande en une seule page, avec un `prefix` constant et un remplissage automatique côté front.
- **Utilisation de `related_name`** pour naviguer des commandes vers leurs lignes (`commande.lignes.all`).
- **Sécurité / intégrité** : `on_delete=PROTECT` empêche de supprimer un client ou un produit utilisé dans des commandes; `unique_together` évite les doublons de produit dans une commande.
- **Internationalisation** : paramètres langue/timezone `fr-fr` et `Europe/Paris`.

---

## Commandes utiles (rappel)
- Lancer le serveur : `python manage.py runserver`.
- Accéder à l’app : http://127.0.0.1:8000/ ; admin : http://127.0.0.1:8000/admin/.
- Créer un superuser (admin) : `python manage.py createsuperuser`.
- Appliquer les migrations : `python manage.py migrate`.

---

Avec ce guide, tu peux présenter chaque fichier : qui fait quoi, comment les données circulent, et où la logique métier est située. Bon entretien !
