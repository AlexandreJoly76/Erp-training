from django.db import models
from decimal import Decimal

TVA_STANDARD = Decimal("0.20")
# Remises par type de client (ex. 10% pour un pro)
DISCOUNT_BY_CLIENT_TYPE = {
    "pro": Decimal("0.10"),
    "part": Decimal("0.00"),
}


def compute_price_with_discount(base_price: Decimal, client_type: str | None) -> Decimal:
    # Retourne le prix TTC remisé pour le type de client.
    discount = DISCOUNT_BY_CLIENT_TYPE.get(client_type, Decimal("0"))
    return (base_price * (Decimal("1") - discount)).quantize(Decimal("0.01"))


class Client(models.Model):
    TYPES_CHOICES = [
        ("pro", "Professionnel"),
        ("part", "Particulier"),
    ]
    nom = models.CharField("Nom", max_length=100)
    email = models.EmailField("Email", unique=True, blank=True)
    type_client = models.CharField(
        "Type de client", max_length=4, choices=TYPES_CHOICES, default="pro"
    )
    created_at = models.DateTimeField("Crée le ", auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return self.nom


class Commande(models.Model):
    STATUS_CHOICES = [
        ("brouillon", "Brouillon"),
        ("validée", "Validée"),
        ("livrée", "Livrée"),
        ("annulée", "Annulée"),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="commande", verbose_name="Client"
    )
    date = models.DateTimeField("Date", auto_now_add=True)
    status = models.CharField(
        "Status", max_length=10, choices=STATUS_CHOICES, default="brouillon"
    )
    tva = models.DecimalField(
        "TVA", max_digits=4, decimal_places=2, default=TVA_STANDARD
    )

    class Meta:
        ordering = ["-date", "id"]
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"

    def __str__(self):
        return f"CMD-{self.id} - {self.client.nom}"  # type: ignore[attr-defined]

    @property
    def total_ht(self):
        total = Decimal("0.00")
        # utiliser le related_name exact: "lignes"
        for ligne in self.lignes.all():  # type: ignore[attr-defined]
            total += ligne.valeur_ligne
        return total

    @property
    def total_ttc(self) -> Decimal:
        # arrondir à 2 décimales
        return (self.total_ht * (1 + self.tva)).quantize(Decimal("0.01"))


class LigneCommande(models.Model):
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="lignes"
    )
    produit = models.ForeignKey("Produit", on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField("Quantité", default=1)
    prix_unitaire = models.DecimalField(
        "Prix unitaire (€)", max_digits=10, decimal_places=2
    )

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"
        unique_together = [("commande", "produit")]  # une ligne par produit (simple)

    def __str__(self):
        return f"{self.produit.ref} x {self.quantite}"

    @property
    def valeur_ligne(self) -> Decimal:
        return self.prix_unitaire * self.quantite

    def save(self, *args, **kwargs):
        # Par défaut, si pas de prix fourni, on applique la remise client au prix produit
        if not self.prix_unitaire:
            client_type = None
            if self.commande_id and self.commande and self.commande.client_id:
                client_type = self.commande.client.type_client
            self.prix_unitaire = compute_price_with_discount(
                self.produit.prix,
                client_type,
            )
        super().save(*args, **kwargs)


class Produit(models.Model):
    ref = models.CharField("Référence", max_length=20, unique=True)
    nom = models.CharField("Nom", max_length=100)
    prix = models.DecimalField("Prix unitaire (€)", max_digits=10, decimal_places=2)
    quantite = models.IntegerField("Quantité en stock", default=0)
    created_at = models.DateTimeField("Crée le ", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)

    class Meta:
        ordering = ["ref"]
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self):
        return f"{self.ref} - {self.nom}"

    @property
    def valeur_stock(self):
        return self.prix * self.quantite

    def en_alerte(self, seuil: int) -> bool:
        return self.quantite <= seuil
