# payment/migrations/0002_update_transaction_model.py
from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0001_initial'),  # Ajustez selon votre migration précédente
    ]

    operations = [
        # Ajouter le champ payment_method
        migrations.AddField(
            model_name='transaction',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('credit_card', 'Carte de crédit'),
                    ('moncash', 'MonCash'),
                    ('natcash', 'NatCash'),
                    ('other', 'Autre')
                ],
                default='credit_card',
                max_length=20,
                verbose_name='méthode de paiement'
            ),
        ),
        
        # Ajouter le champ external_transaction_id
        migrations.AddField(
            model_name='transaction',
            name='external_transaction_id',
            field=models.CharField(
                blank=True,
                help_text='ID de transaction du fournisseur de paiement',
                max_length=255,
                null=True,
                verbose_name='ID transaction externe'
            ),
        ),
        
        # Ajouter le champ thinkific_external_order_id
        migrations.AddField(
            model_name='transaction',
            name='thinkific_external_order_id',
            field=models.IntegerField(
                blank=True,
                help_text='ID de External Order créé dans Thinkific',
                null=True,
                verbose_name='ID commande externe Thinkific'
            ),
        ),
        
        # Ajouter le champ completed_at
        migrations.AddField(
            model_name='transaction',
            name='completed_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='date de complétion'
            ),
        ),
        
        # Modifier le champ status pour ajouter CANCELLED et REFUNDED
        migrations.AlterField(
            model_name='transaction',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'En attente'),
                    ('COMPLETED', 'Complétée'),
                    ('FAILED', 'Échouée'),
                    ('CANCELLED', 'Annulée'),
                    ('REFUNDED', 'Remboursée')
                ],
                default='PENDING',
                max_length=20,
                verbose_name='statut'
            ),
        ),
        
        # Modifier meta_data pour avoir un default=dict
        migrations.AlterField(
            model_name='transaction',
            name='meta_data',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Informations supplémentaires (cours, utilisateur, etc.)',
                verbose_name='métadonnées'
            ),
        ),
        
        # Ajouter GBP aux devises
        migrations.AlterField(
            model_name='transaction',
            name='currency',
            field=models.CharField(
                choices=[
                    ('USD', 'Dollar américain'),
                    ('HTG', 'Gourde haïtienne'),
                    ('EUR', 'Euro'),
                    ('GBP', 'Livre sterling')
                ],
                default='USD',
                max_length=3,
                verbose_name='devise'
            ),
        ),

        # Ajouter le champ user
        migrations.AddField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to=settings.AUTH_USER_MODEL,
                null=True,
                blank=True,
                verbose_name='utilisateur'
            ),
        ),
        
        # Ajouter des index pour les performances
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['external_transaction_id'], name='payment_tra_externa_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['transaction_number'], name='payment_tra_transac_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user'], name='payment_tra_user_id_idx'),
        ),
        
        # Modifier Payment pour avoir OneToOneField au lieu de ForeignKey
        migrations.AlterField(
            model_name='payment',
            name='transaction',
            field=models.OneToOneField(
                on_delete=models.CASCADE,
                related_name='payment',
                to='payment.transaction',
                verbose_name='transaction'
            ),
        ),
    ]