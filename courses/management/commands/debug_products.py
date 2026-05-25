"""
Management command to dump raw Thinkific product data.
Usage: python manage.py debug_products
"""
import json
from django.core.management.base import BaseCommand
from courses.views import thinkific


class Command(BaseCommand):
    help = 'Affiche les données brutes des produits Thinkific (pour debug)'

    def handle(self, *args, **options):
        try:
            products = thinkific.products.list(limit=100).get('items', [])
        except Exception as e:
            self.stderr.write(f'Erreur API Thinkific: {e}')
            return

        self.stdout.write(f'\n=== {len(products)} produit(s) trouvé(s) ===\n')
        for p in products:
            self.stdout.write(
                f"  id={p.get('id')}  productable_type={p.get('productable_type')}  "
                f"productable_id={p.get('productable_id')}  "
                f"price={p.get('price')}  "
                f"days_until_expiry={p.get('days_until_expiry')}"
            )
        self.stdout.write('\n--- Clés disponibles sur le 1er produit ---')
        if products:
            self.stdout.write(json.dumps(list(products[0].keys()), indent=2))
