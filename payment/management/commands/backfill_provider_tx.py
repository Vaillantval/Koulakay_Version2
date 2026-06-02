"""
Backfill du numéro de transaction télco (MonCash/NatCash) pour les transactions
déjà confirmées avant l'ajout du champ provider_transaction_id.

Rappelle l'endpoint PlopPlop /api/paiement-verify avec le transaction_number
(= refference_id) de chaque transaction, et sauvegarde le id_transaction renvoyé.

Lecture seule côté PlopPlop. N'écrase jamais une valeur existante.

Usage :
    python manage.py backfill_provider_tx --dry-run        # simulation, n'écrit rien
    python manage.py backfill_provider_tx --limit 2        # ne traite que 2 transactions
    python manage.py backfill_provider_tx                  # backfill complet
"""
import time

from django.core.management.base import BaseCommand

from payment.models import Transaction
from payment.plopplop_service import PlopPlopService


class Command(BaseCommand):
    help = "Récupère le id_transaction MonCash/NatCash des transactions passées via PlopPlop verify."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Simule sans rien sauvegarder.")
        parser.add_argument('--limit', type=int, default=0,
                            help="Limite le nombre de transactions traitées (0 = toutes).")
        parser.add_argument('--sleep', type=float, default=0.5,
                            help="Pause en secondes entre chaque appel API (défaut 0.5).")

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        limit   = opts['limit']
        sleep_s = opts['sleep']

        qs = Transaction.objects.filter(
            status=Transaction.Status.COMPLETED,
            payment_method__in=['moncash', 'natcash'],
            provider_transaction_id__isnull=True,
        ).order_by('created_at')

        total = qs.count()
        if limit:
            qs = qs[:limit]

        self.stdout.write(self.style.NOTICE(
            f"{total} transaction(s) MonCash/NatCash sans provider_transaction_id"
            + (f" — traitement limité à {limit}" if limit else "")
            + (" — DRY RUN (aucune écriture)" if dry_run else "")
        ))

        svc = PlopPlopService()
        updated = skipped = errors = 0

        for tx in qs:
            ref = tx.transaction_number
            result = svc.verify_payment(ref)

            if not result.get('success'):
                errors += 1
                self.stdout.write(self.style.WARNING(
                    f"  ✗ {ref} → verify échoué : {result.get('error', 'inconnu')}"
                ))
            else:
                id_tx = result.get('id_transaction')
                if id_tx:
                    if dry_run:
                        self.stdout.write(
                            f"  ~ {ref} → id_transaction={id_tx} (dry-run, non sauvegardé)"
                        )
                    else:
                        tx.provider_transaction_id = str(id_tx)
                        tx.save(update_fields=['provider_transaction_id'])
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ {ref} → {id_tx}"
                        ))
                    updated += 1
                else:
                    skipped += 1
                    self.stdout.write(
                        f"  - {ref} → pas de id_transaction renvoyé (trans_status={result.get('paid')})"
                    )

            if sleep_s:
                time.sleep(sleep_s)

        self.stdout.write(self.style.NOTICE(
            f"\nTerminé : {updated} récupéré(s), {skipped} sans ID, {errors} erreur(s)."
        ))
