from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommandeForm, LigneCommandeFormSet

from .models import Commande, Produit


FORMSET_PREFIX = "lignes"


def product_list(request):
    produits = Produit.objects.order_by("ref")
    return render(request, "stocks/product_list.html", {"produits": produits})


def order_create(request):
    produits_prix = {
        str(produit.id): str(produit.prix) for produit in Produit.objects.only("id", "prix")
    }

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

    return render(
        request,
        "stocks/order_form.html",
        {
            "form": form,
            "formset": formset,
            "prix_produits": produits_prix,
        },
    )


def order_detail(request, pk: int):
    cmd = get_object_or_404(Commande, pk=pk)
    return render(request, "stocks/order_detail.html", {"commande": cmd})
