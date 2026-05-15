from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_coursetranslation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('slug', models.SlugField(blank=True, unique=True, verbose_name='Slug')),
                ('icon', models.CharField(blank=True, default='fa-graduation-cap', help_text='Classe Font Awesome, ex: fa-laptop-code', max_length=50, verbose_name='Icône FA')),
                ('color', models.CharField(blank=True, default='#6366F1', help_text='Couleur hex, ex: #6366F1', max_length=20, verbose_name='Couleur')),
                ('order', models.PositiveSmallIntegerField(default=0, verbose_name='Ordre')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
            ],
            options={
                'verbose_name': 'Catégorie',
                'verbose_name_plural': 'Catégories',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='CourseCategoryMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_id', models.IntegerField(verbose_name='ID cours Thinkific')),
                ('course_name_cache', models.CharField(blank=True, max_length=255, verbose_name='Nom (cache)')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='courses.coursecategory', verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': 'Cours de la catégorie',
                'verbose_name_plural': 'Cours de la catégorie',
                'unique_together': {('category', 'course_id')},
            },
        ),
    ]
