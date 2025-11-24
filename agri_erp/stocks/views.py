from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommandeForm, LigneCommandeFormSet

from .models import (
    Client,
    Commande,
    Produit,
    compute_price_with_discount,
    DISCOUNT_BY_CLIENT_TYPE,
)


FORMSET_PREFIX = "lignes"


def product_list(request):
    produits = Produit.objects.order_by("ref")
    return render(request, "stocks/product_list.html", {"produits": produits})


def order_create(request):
    produits_prix = {
        str(produit.id): str(produit.prix) for produit in Produit.objects.only("id", "prix")
    }
    clients_types = {
        str(client.id): client.type_client
        for client in Client.objects.only("id", "type_client")
    }
    discounts = {key: str(value) for key, value in DISCOUNT_BY_CLIENT_TYPE.items()}

    if request.method == "POST":
        form = CommandeForm(request.POST)
        formset = LigneCommandeFormSet(request.POST, prefix=FORMSET_PREFIX)
        if form.is_valid() and formset.is_valid():
            commande = form.save()
            lignes = formset.save(commit=False)
            for ligne in lignes:
                ligne.commande = commande
                ligne.prix_unitaire = compute_price_with_discount(
                    ligne.produit.prix,
                    commande.client.type_client,
                )
                ligne.save()
            return redirect(reverse("stocks:order_detail", args=[commande.id]))
    else:
        form = CommandeForm()
        formset = LigneCommandeFormSet(prefix=FORMSET_PREFIX)

    return render(
        request,
        "stocks/order_form.html",
        {
            "form": form,
            "formset": formset,
            "prix_produits": produits_prix,
            "clients_types": clients_types,
            "discounts": discounts,
        },
    )


def order_detail(request, pk: int):
    cmd = get_object_or_404(Commande, pk=pk)
    discount_rate = DISCOUNT_BY_CLIENT_TYPE.get(cmd.client.type_client, Decimal("0"))
    discount_percent = (discount_rate * Decimal("100")).quantize(Decimal("0.01"))
    return render(
        request,
        "stocks/order_detail.html",
        {
            "commande": cmd,
            "discount_percent": discount_percent,
        },
    )
