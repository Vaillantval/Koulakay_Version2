from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path
from django.utils.safestring import mark_safe
import courses.models as models


@admin.register(models.CourseTranslation)
class CourseTranslationAdmin(admin.ModelAdmin):
    list_display = ('course_id', 'language', 'name')
    list_filter = ('language',)
    search_fields = ('course_id', 'name')
    ordering = ('course_id', 'language')


def _fetch_thinkific_courses():
    """Retourne [(id, name), ...] depuis l'API Thinkific, trié par nom."""
    try:
        from courses.views import thinkific
        items = thinkific.courses.list(limit=100).get('items', [])
        return sorted(
            [(c['id'], c.get('name', f"Cours #{c['id']}")) for c in items],
            key=lambda x: x[1].lower()
        )
    except Exception:
        return []


def _fetch_thinkific_bundles():
    """Retourne [(bundle_id, name), ...] depuis l'API Thinkific (via products)."""
    try:
        from courses.views import thinkific, _fetch_bundle_details
        product_items = thinkific.products.list(limit=100).get('items', [])
        bundle_products = [p for p in product_items if p.get('productable_type') == 'Bundle']
        result = []
        for bp in bundle_products:
            bid = bp.get('productable_id')
            if not bid:
                continue
            try:
                info = _fetch_bundle_details(bid)
                name = info.get('name', f'Bundle #{bid}')
            except Exception:
                name = f'Bundle #{bid}'
            result.append((bid, name))
        return sorted(result, key=lambda x: x[1].lower())
    except Exception:
        return []


# ── Enrollment ──────────────────────────────────────────────────────────────────

class EnrollmentAdminForm(forms.ModelForm):
    """course_id devient un menu déroulant des cours Thinkific ; les autres champs
    techniques sont auto-remplis (thinkific_user_id depuis l'user, dates calculées)."""
    course_id = forms.TypedChoiceField(
        label='Cours',
        coerce=int,
        choices=[],
        help_text="L'utilisateur aura accès à ce cours dans Thinkific après enregistrement.",
    )

    class Meta:
        model = models.Enrollment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course_id'].choices = [('', '— Choisir un cours —')] + _fetch_thinkific_courses()
        # Auto-remplis → non obligatoires dans le formulaire
        self.fields['thinkific_user_id'].required = False
        self.fields['thinkific_user_id'].help_text = "Auto-rempli depuis l'utilisateur sélectionné."
        self.fields['activated_at'].required = False
        self.fields['activated_at'].help_text = "Laisser vide = maintenant."
        self.fields['expiry_date'].required = False
        self.fields['expiry_date'].help_text = "Laisser vide = calculé selon la durée du cours."


@admin.register(models.Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    form = EnrollmentAdminForm
    list_display = ('id', 'user', 'thinkific_user_id', 'course_id', 'activated_at', 'expiry_date')
    list_filter = ('activated_at', 'expiry_date', 'course_id')
    search_fields = ('user__email', 'thinkific_user_id', 'course_id')

    class Media:
        js = ('admin/js/enrollment_autofill.js',)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'thinkific-id/<int:user_id>/',
                self.admin_site.admin_view(self.get_thinkific_id),
                name='enrollment_thinkific_id',
            ),
        ]
        return custom + urls

    def get_thinkific_id(self, request, user_id):
        """Endpoint AJAX : renvoie le thinkific_user_id de l'utilisateur sélectionné."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            u = User.objects.get(pk=user_id)
            return JsonResponse({'thinkific_user_id': u.thinkific_user_id})
        except User.DoesNotExist:
            return JsonResponse({'thinkific_user_id': None})

    def save_model(self, request, obj, form, change):
        """Crée l'inscription RÉELLE dans Thinkific, puis enregistre la ligne locale."""
        from django.utils import timezone
        from datetime import timedelta
        from courses.views import thinkific
        from accounts.views import get_thinkific_user_by_email

        # 1. thinkific_user_id depuis l'utilisateur (source de vérité)
        tk_id = obj.user.thinkific_user_id
        if not tk_id:
            tk_user = get_thinkific_user_by_email(obj.user.email)
            if tk_user and tk_user.get('id'):
                tk_id = tk_user['id']
                obj.user.thinkific_user_id = tk_id
                obj.user.save(update_fields=['thinkific_user_id'])
        if not tk_id:
            messages.error(request, f"Inscription impossible : {obj.user.email} n'a pas de compte Thinkific lié.")
            return
        obj.thinkific_user_id = tk_id

        # 2. Dates (durée du produit si dispo, sinon ~à vie)
        activated_at = obj.activated_at or timezone.now()
        days = None
        try:
            for p in thinkific.products.list(limit=100).get('items', []):
                if p.get('productable_id') == obj.course_id and p.get('days_until_expiry'):
                    days = int(p['days_until_expiry'])
                    break
        except Exception:
            pass
        if obj.expiry_date:
            expiry = obj.expiry_date
        elif days:
            expiry = activated_at + timedelta(days=days)
        else:
            expiry = activated_at.replace(year=activated_at.year + 10)
        obj.activated_at = activated_at
        obj.expiry_date = expiry

        # 3. Inscription Thinkific réelle
        enrollment_data = {
            'user_id':      tk_id,
            'course_id':    obj.course_id,
            'activated_at': activated_at.isoformat(),
        }
        if days:
            enrollment_data['expiry_date'] = expiry.isoformat()
        try:
            result = thinkific.enrollments.create_enrollment(enrollment_data)
        except Exception as e:
            messages.error(request, f"Échec inscription Thinkific : {e}. Enrollment non créé.")
            return
        if not result:
            messages.error(request, "Thinkific n'a pas confirmé l'inscription. Enrollment non créé.")
            return

        # 4. Enregistrer la ligne locale
        super().save_model(request, obj, form, change)

        course_name = dict(_fetch_thinkific_courses()).get(obj.course_id, f'Cours #{obj.course_id}')
        messages.success(request, f"« {course_name} » activé pour {obj.user.email} dans Thinkific ✓")

        # 5. Emails (non bloquant)
        import uuid
        ref = f"ADMIN-{activated_at.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        try:
            from pages.models import SiteConfig
            from payment.email_service import send_enrollment_confirmation
            send_enrollment_confirmation(
                user=obj.user,
                course_name=course_name,
                transaction_number=ref,
                amount=0,
                currency=SiteConfig.get().currency,
                payment_method='Inscription manuelle (admin)',
                activated_at=activated_at,
                expiry_date=expiry,
            )
        except Exception as e:
            print(f"[Admin Enroll] Email confirmation échoué : {e}")
        try:
            from accounts.admin_notify import notify_admin_new_enrollment
            notify_admin_new_enrollment(
                user=obj.user,
                course_name=course_name,
                is_free=True,
                payment_method='Inscription manuelle (admin)',
                transaction_number=ref,
                activated_at=activated_at,
                expiry_date=expiry,
            )
        except Exception as e:
            print(f"[Admin Enroll] Notification admin échouée : {e}")


class CourseCategoryAdminForm(forms.ModelForm):
    selected_courses = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Cours inclus dans cette catégorie',
        help_text='Cochez les cours Thinkific à associer à cette catégorie.',
    )
    selected_bundles = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Bundles inclus dans cette catégorie',
        help_text='Cochez les bundles Thinkific à associer à cette catégorie.',
    )

    class Meta:
        model = models.CourseCategory
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        courses = _fetch_thinkific_courses()
        self.fields['selected_courses'].choices = [
            (str(cid), name) for cid, name in courses
        ]
        bundles = _fetch_thinkific_bundles()
        self.fields['selected_bundles'].choices = [
            (str(bid), name) for bid, name in bundles
        ]
        if self.instance and self.instance.pk:
            self.fields['selected_courses'].initial = [
                str(m.course_id) for m in self.instance.memberships.all()
            ]
            self.fields['selected_bundles'].initial = [
                str(m.bundle_id) for m in self.instance.bundle_memberships.all()
            ]


@admin.register(models.CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    form = CourseCategoryAdminForm
    list_display = ('name', 'order', 'slug', 'icon', 'color', 'is_active', 'course_count', 'bundle_count')
    list_display_links = ('name',)
    list_editable = ('order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'icon', 'color', 'image', 'description', 'order', 'is_active', 'selected_courses', 'selected_bundles')

    class Media:
        css = {'all': ('admin/css/category_courses.css',)}

    def course_count(self, obj):
        return obj.memberships.count()
    course_count.short_description = 'Nb cours'

    def bundle_count(self, obj):
        return obj.bundle_memberships.count()
    bundle_count.short_description = 'Nb bundles'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # ── Cours ──
        selected_ids = [int(x) for x in form.cleaned_data.get('selected_courses', [])]
        courses = _fetch_thinkific_courses()
        course_map = {cid: name for cid, name in courses}
        obj.memberships.exclude(course_id__in=selected_ids).delete()
        for cid in selected_ids:
            models.CourseCategoryMembership.objects.update_or_create(
                category=obj,
                course_id=cid,
                defaults={'course_name_cache': course_map.get(cid, '')},
            )

        # ── Bundles ──
        selected_bundle_ids = [int(x) for x in form.cleaned_data.get('selected_bundles', [])]
        bundles = _fetch_thinkific_bundles()
        bundle_map = {bid: name for bid, name in bundles}
        obj.bundle_memberships.exclude(bundle_id__in=selected_bundle_ids).delete()
        for bid in selected_bundle_ids:
            models.BundleCategoryMembership.objects.update_or_create(
                category=obj,
                bundle_id=bid,
                defaults={'bundle_name_cache': bundle_map.get(bid, '')},
            )


class CourseGroupAdminForm(forms.ModelForm):
    selected_courses = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Cours inclus dans ce groupe',
        help_text='Cochez les cours Thinkific à associer à ce groupe.',
    )

    class Meta:
        model = models.CourseGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        courses = _fetch_thinkific_courses()
        self.fields['selected_courses'].choices = [
            (str(cid), name) for cid, name in courses
        ]
        if self.instance and self.instance.pk:
            self.fields['selected_courses'].initial = [
                str(m.course_id) for m in self.instance.memberships.all()
            ]


@admin.register(models.CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    form = CourseGroupAdminForm
    list_display = ('name', 'order', 'is_active', 'course_count')
    list_display_links = ('name',)
    list_editable = ('order', 'is_active')
    fields = ('name', 'description', 'image', 'category', 'order', 'is_active', 'selected_courses')

    class Media:
        css = {'all': ('admin/css/category_courses.css',)}

    def course_count(self, obj):
        return obj.memberships.count()
    course_count.short_description = 'Nb cours'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        selected_ids = [int(x) for x in form.cleaned_data.get('selected_courses', [])]
        courses = _fetch_thinkific_courses()
        course_map = {cid: name for cid, name in courses}
        obj.memberships.exclude(course_id__in=selected_ids).delete()
        for cid in selected_ids:
            models.CourseGroupMembership.objects.update_or_create(
                group=obj,
                course_id=cid,
                defaults={'course_name_cache': course_map.get(cid, '')},
            )


@admin.register(models.CoursePriceDisplay)
class CoursePriceDisplayAdmin(admin.ModelAdmin):
    change_list_template = 'admin/courses/coursepricedisplay/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        CURRENCIES = [
            ('USD', 'USD — Dollar américain'),
            ('HTG', 'HTG — Gourde haïtienne'),
            ('EUR', 'EUR — Euro'),
            ('CAD', 'CAD — Dollar canadien'),
            ('GBP', 'GBP — Livre sterling'),
        ]
        if request.method == 'POST':
            all_courses = _fetch_thinkific_courses()
            for cid, name in all_courses:
                chosen = request.POST.get(f'currency_{cid}', 'USD')
                models.CoursePriceDisplay.objects.update_or_create(
                    course_id=cid,
                    defaults={'course_name_cache': name, 'display_currency': chosen},
                )
            self.message_user(request, f"Devises mises à jour pour {len(all_courses)} cours.")
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(request.path)

        all_courses = _fetch_thinkific_courses()
        currency_map = {
            entry.course_id: entry.display_currency
            for entry in models.CoursePriceDisplay.objects.all()
        }
        courses_with_currency = [
            {'id': cid, 'name': name, 'currency': currency_map.get(cid, 'USD')}
            for cid, name in all_courses
        ]
        extra = extra_context or {}
        extra['courses_with_currency'] = courses_with_currency
        extra['currencies'] = CURRENCIES
        extra['title'] = 'Devise d\'affichage par cours'
        return super().changelist_view(request, extra_context=extra)


@admin.register(models.CourseVisibility)
class CourseVisibilityAdmin(admin.ModelAdmin):
    change_list_template = 'admin/courses/coursevisibility/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if request.method == 'POST':
            all_courses = _fetch_thinkific_courses()
            visible_ids = set(int(x) for x in request.POST.getlist('visible'))
            for cid, name in all_courses:
                models.CourseVisibility.objects.update_or_create(
                    course_id=cid,
                    defaults={'course_name_cache': name, 'is_visible': cid in visible_ids},
                )
            self.message_user(request, f"Visibilité mise à jour pour {len(all_courses)} cours.")
            return HttpResponseRedirect(request.path)

        all_courses = _fetch_thinkific_courses()
        visibility_map = {
            v.course_id: v.is_visible
            for v in models.CourseVisibility.objects.all()
        }
        courses_with_state = [
            {'id': cid, 'name': name, 'visible': visibility_map.get(cid, True)}
            for cid, name in all_courses
        ]
        extra = extra_context or {}
        extra['courses_with_state'] = courses_with_state
        extra['title'] = 'Visibilité des cours'
        return super().changelist_view(request, extra_context=extra)
