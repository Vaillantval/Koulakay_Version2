from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.http import Http404
from datetime import datetime, timezone
from decimal import Decimal
import requests

from .monkey_patch.patch_thinkific import ThinkificExtend
from .models import Enrollment
from payment.models import Transaction

# Configuration Thinkific
thinkific = ThinkificExtend(settings.THINKIFIC['AUTH_TOKEN'], settings.THINKIFIC['SITE_ID'])


@login_required
def course_enrollment_step1(request, course_id):
    """Étape 1: Afficher les options de paiement ou inscription directe"""
    if request.method != 'POST':
        return redirect('courses')
    
    try:
        # Récupérer les détails du cours
        course = thinkific.courses.retrieve_course(id=course_id)
        course_name = course.get('name', f'Course ID {course_id}')
        
        # Récupérer le prix et product_id
        course_price = Decimal('0.00')
        product_id = None
        product_response = thinkific.products.list()
        product_items = product_response.get('items', [])
        
        for p in product_items:
            if p.get('productable_id') == course_id:
                if p.get('price') is not None:
                    course_price = Decimal(str(p['price']))
                product_id = p.get('id')
                break
        
        # Trouver l'ID Thinkific de l'utilisateur
        thinkific_user_id = None
        user_list = thinkific.users.list().get('items', [])
        for u in user_list:
            if u.get('email') == request.user.email:
                thinkific_user_id = u.get('id')
                break
        
        if not thinkific_user_id:
            messages.error(request, _("Impossible de trouver votre profil Thinkific."))
            return redirect('course_details', course_id=course_id)
        
        # Vérifier si déjà inscrit
        if Enrollment.objects.filter(user=request.user, course_id=course_id).exists():
            messages.info(request, _("Vous êtes déjà inscrit à ce cours."))
            return redirect('course_details', course_id=course_id)
        
        # Si gratuit, inscription directe
        if course_price == 0:
            return enroll_user_free(request, course_id, thinkific_user_id, course_name)
        
        # Si payant, afficher les options de paiement
        request.session['enrollment_data'] = {
            'course_id': course_id,
            'course_name': course_name,
            'course_price': float(course_price),
            'product_id': product_id,
            'thinkific_user_id': thinkific_user_id
        }
        
        return render(request, 'courses/payment_options.html', {
            'course': course,
            'course_price': course_price,
        })
        
    except Exception as e:
        messages.error(request, _("Une erreur est survenue."))
        print(f"Erreur enrollment step1: {e}")
        return redirect('course_details', course_id=course_id)


@login_required
def course_enrollment_payment(request, payment_method):
    """Étape 2: Traiter le paiement selon la méthode choisie"""
    if request.method != 'POST':
        return redirect('courses')
    
    # Récupérer les données de session
    enrollment_data = request.session.get('enrollment_data')
    if not enrollment_data:
        messages.error(request, _("Session expirée. Veuillez recommencer."))
        return redirect('courses')
    
    course_id = enrollment_data['course_id']
    course_name = enrollment_data['course_name']
    course_price = Decimal(str(enrollment_data['course_price']))
    product_id = enrollment_data.get('product_id')
    thinkific_user_id = enrollment_data['thinkific_user_id']
    
    # Valider la méthode de paiement
    valid_methods = ['credit_card', 'moncash', 'natcash']
    if payment_method not in valid_methods:
        messages.error(request, _("Méthode de paiement invalide."))
        return redirect('course_details', course_id=course_id)
    
    try:
        # Créer la transaction
        transaction = Transaction.objects.create(
            user=request.user,
            price=course_price,
            currency=Transaction.Currencies.USD,
            status=Transaction.Status.PENDING,
            payment_method=payment_method,
            meta_data={
                "course": {
                    "course_id": course_id,
                    "course_name": course_name,
                    "product_id": product_id
                },
                "user": {
                    "id": request.user.pk,
                    "email": request.user.email,
                    "thinkific_user_id": thinkific_user_id
                }
            }
        )
        
        # Générer le lien de paiement selon la méthode
        redirect_url = generate_payment_link(request, transaction, payment_method)
        
        if redirect_url:
            # Nettoyer la session
            del request.session['enrollment_data']
            return redirect(redirect_url)
        else:
            transaction.status = Transaction.Status.FAILED
            transaction.save()
            messages.error(request, _("Impossible de générer le lien de paiement."))
            return redirect('course_details', course_id=course_id)
            
    except Exception as e:
        messages.error(request, _("Erreur lors du traitement du paiement."))
        print(f"Erreur payment: {e}")
        return redirect('course_details', course_id=course_id)


def generate_payment_link(request, transaction, payment_method):
    """Génère le lien de paiement selon la méthode choisie"""
    
    # Configuration des endpoints selon la méthode
    payment_configs = {
        'credit_card': {
            'endpoint': settings.PAYMENT['PAY_API_ENDPOINT'],
            'api_key': settings.PAYMENT['API_KEY']
        },
        'moncash': {
            'endpoint': settings.PAYMENT.get('MONCASH_API_ENDPOINT', settings.PAYMENT['PAY_API_ENDPOINT']),
            'api_key': settings.PAYMENT.get('MONCASH_API_KEY', settings.PAYMENT['API_KEY'])
        },
        'natcash': {
            'endpoint': settings.PAYMENT.get('NATCASH_API_ENDPOINT', settings.PAYMENT['PAY_API_ENDPOINT']),
            'api_key': settings.PAYMENT.get('NATCASH_API_KEY', settings.PAYMENT['API_KEY'])
        }
    }
    
    config = payment_configs.get(payment_method)
    if not config:
        return None
    
    # Construire le callback URL
    callback_url = request.build_absolute_uri('/payment/callback_url/')
    
    # Données de paiement
    data = {
        "amount": float(transaction.price),
        "currency": transaction.currency,
        "api_key": config['api_key'],
        "payment_method": payment_method,
        "callback_url": callback_url,
        "transaction_id": transaction.pk,
        "meta_data": {
            "transaction_number": transaction.transaction_number,
            "user_email": transaction.user.email,
            "course_name": transaction.course_name
        }
    }
    
    try:
        response = requests.post(
            config['endpoint'],
            json=data,
            timeout=30
        )
        response.raise_for_status()
        response_data = response.json()
        
        # Sauvegarder l'ID externe si fourni
        if 'transaction_id' in response_data:
            transaction.external_transaction_id = response_data['transaction_id']
            transaction.save()
        
        return response_data.get('pay_url')
        
    except requests.RequestException as e:
        print(f"Erreur génération lien paiement: {e}")
        return None


def enroll_user_free(request, course_id, thinkific_user_id, course_name):
    """Inscrit un utilisateur à un cours gratuit"""
    try:
        from django.utils import timezone as dj_timezone
        
        activated_at = dj_timezone.now()
        expiry_date = activated_at.replace(year=activated_at.year + 1)
        
        enrollment_data = {
            "course_id": course_id,
            "user_id": thinkific_user_id,
            "activated_at": activated_at.isoformat(),
            "expiry_date": expiry_date.isoformat()
        }
        
        enrollment_result = thinkific.enrollments.create_enrollment(enrollment_data)
        
        if enrollment_result:
            # Créer l'entrée locale
            Enrollment.objects.create(
                user=request.user,
                thinkific_user_id=thinkific_user_id,
                course_id=course_id,
                activated_at=activated_at,
                expiry_date=expiry_date,
            )
            
            messages.success(request, f"Vous êtes inscrit au cours {course_name}!")
            return redirect('course_details', course_id=course_id)
        else:
            messages.error(request, _("Erreur lors de l'inscription."))
            return redirect('course_details', course_id=course_id)
            
    except Exception as e:
        messages.error(request, _("Erreur lors de l'inscription."))
        print(f"Erreur enroll free: {e}")
        return redirect('course_details', course_id=course_id)


def payment_callback(request):
    """
    Traite le callback après paiement.
    Redirige vers la page du cours avec un message.
    """
    transaction_id = request.GET.get('transaction_id')
    status = request.GET.get('status', '').lower()
    
    if not transaction_id:
        messages.error(request, _("Transaction introuvable."))
        return redirect('courses')
    
    try:
        transaction = Transaction.objects.get(pk=transaction_id)
        course_id = transaction.course_id
        
        if status in ['success', 'completed'] and transaction.is_completed:
            messages.success(request, _("Paiement réussi ! Vous êtes maintenant inscrit au cours."))
            return redirect('course_details', course_id=course_id)
        elif status in ['failed', 'cancelled']:
            messages.error(request, _("Le paiement a échoué ou a été annulé."))
            return redirect('course_details', course_id=course_id)
        else:
            messages.info(request, _("Votre paiement est en cours de traitement."))
            return redirect('course_details', course_id=course_id)
            
    except Transaction.DoesNotExist:
        messages.error(request, _("Transaction introuvable."))
        return redirect('courses')
    except Exception as e:
        messages.error(request, _("Erreur lors du traitement."))
        print(f"Erreur callback: {e}")
        return redirect('courses')


def home(request):
    """Vue pour la page d'accueil avec statistiques et cours populaires"""
    stats = {
        'total_courses': 0,
        'total_users': 0,
        'local_enrollments': 0,
    }
    
    try:
        # Statistiques via l'API Thinkific
        courses_response = thinkific.courses.list(limit=1)
        stats['total_courses'] = courses_response.get('meta', {}).get('pagination', {}).get('total_items', 0)

        users_response = thinkific.users.list(limit=1)
        stats['total_users'] = users_response.get('meta', {}).get('pagination', {}).get('total_items', 0)
        
        stats['local_enrollments'] = Enrollment.objects.count()
        
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques: {e}")
    
    # Récupérer les cours populaires (top 6 pour la homepage)
    popular_courses = []
    top_course_ids_queryset = Enrollment.objects.values('course_id') \
                                             .annotate(num_enrollments=Count('course_id')) \
                                             .order_by('-num_enrollments')[:6]
    
    top_course_ids = [item['course_id'] for item in top_course_ids_queryset]
    
    # Récupérer les détails des produits
    try:
        product_response = thinkific.products.list()
        product_items = product_response.get('items', [])
    except Exception:
        product_items = []
    
    # Obtenir les détails de chaque cours populaire
    for course_id in top_course_ids:
        try:
            course_data = thinkific.courses.retrieve_course(id=course_id)
            enroll_count = next((item['num_enrollments'] for item in top_course_ids_queryset if item['course_id'] == course_id), 0)
            course_data['enrollment_count'] = enroll_count
            
            # Ajouter le prix
            course_data['price'] = None
            product_id = course_data.get('product_id')
            if product_id is not None:
                for p in product_items:
                    if p.get('productable_id') == course_id and p.get('price') is not None:
                        course_data['price'] = p['price']
                        break
            
            # Vérifier l'inscription
            course_data['enroll'] = False
            if request.user.is_authenticated:
                course_data['enroll'] = Enrollment.objects.filter(
                    user=request.user, 
                    course_id=course_id
                ).exists()
            
            popular_courses.append(course_data)
        except Exception as e:
            print(f"Erreur lors de la récupération du cours populaire {course_id}: {e}")
            continue
    
    return render(request, 'pages/home.html', {
        'stats': stats,
        'courses': popular_courses  # Changé de 'popular_courses' à 'courses' pour cohérence
    })


def courses(request):
    """Liste des cours avec pagination et filtres"""
    page_number = request.GET.get("page", 1)
    limit = 12  # Augmenté pour une meilleure grille
    
    # Cours populaires
    top_course_ids_queryset = Enrollment.objects.values('course_id') \
                                             .annotate(num_enrollments=Count('course_id')) \
                                             .order_by('-num_enrollments')[:5]
    
    top_course_ids = [item['course_id'] for item in top_course_ids_queryset]
    popular_courses = []
    
    for course_id in top_course_ids:
        try:
            course_data = thinkific.courses.retrieve_course(id=course_id)
            enroll_count = next((item['num_enrollments'] for item in top_course_ids_queryset if item['course_id'] == course_id), 0)
            course_data['enrollment_count'] = enroll_count
            popular_courses.append(course_data)
        except Exception as e:
            print(f"Erreur cours populaire {course_id}: {e}")
            continue

    # Cours paginés
    try:
        courses_response = thinkific.courses.list(page=page_number, limit=limit)
        courses_items = courses_response.get('items', [])
        pagination_meta = courses_response.get('meta', {}).get('pagination', {})
    except Exception:
        courses_items = []
        pagination_meta = {}
        
    # Produits et catégories
    try:
        product_response = thinkific.products.list()
        product_items = product_response.get('items', [])
    except Exception:
        product_items = []

    try:
        category_response = thinkific.collections.list_collections()
        category_items = category_response.get('items', [])
    except Exception:
        category_items = []
    
    # Fonction utilitaire pour traiter les cours
    def process_course_list(course_list, product_items, request_user):
        for c in course_list:
            c['price'] = None
            product_id = c.get('product_id')
            
            if product_id is not None:
                for p in product_items:
                    if p.get('productable_id') == c['id'] and p.get('price') is not None:
                        c['price'] = p['price']
                        break
            
            c['enroll'] = False
            if request_user.is_authenticated:
                c['enroll'] = Enrollment.objects.filter(
                    user=request_user, 
                    course_id=c.get('id')
                ).exists()
        return course_list

    courses_items = process_course_list(courses_items, product_items, request.user)
    popular_courses = process_course_list(popular_courses, product_items, request.user)
    
    # Gestion des filtres POST
    if request.method == "POST":
        q = request.POST.get('q', None)
        product_ids = request.POST.get('products', None)
        
        if product_ids:
            id_list = product_ids.strip("[]").split(", ")
            try:
                id_list = [int(id) for id in id_list]
            except ValueError:
                id_list = []
            
            matched_items = [item for item in courses_items if item.get('product_id') in id_list]
            return render(request, 'pages/courses.html', {
                'courses': matched_items,
                'category_items': category_items,
                'popular_courses': popular_courses
            })
        
        if q is None:
            return render(request, 'pages/courses.html', {
                'category_items': category_items,
                'popular_courses': popular_courses
            })
        
        list_found = [c for c in courses_items if q.lower() in c.get('name', '').lower()]
        return render(request, 'pages/courses.html', {
            'courses': list_found,
            'category_items': category_items,
            'q': q,
            'popular_courses': popular_courses
        })
    
    context = {
        'courses': courses_items,
        'category_items': category_items,
        'popular_courses': popular_courses,
        'pagination_meta': pagination_meta, 
    }
    
    return render(request, 'pages/courses.html', context)


def course_details(request, course_id):
    """Détails d'un cours avec contenu et instructeur"""
    try:
        course = thinkific.courses.retrieve_course(id=course_id)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Http404("Le cours demandé n'existe pas.")
        raise

    # Récupérer le prix
    course['price'] = None
    try:
        product_response = thinkific.products.list()
        product_items = product_response.get('items', [])
        product_id = course.get('product_id')
        
        if product_id is not None:
            for p in product_items:
                if p.get('productable_id') == course_id and p.get('price') is not None:
                    course['price'] = p['price']
                    break
    except Exception as e:
        print(f"Erreur récupération prix: {e}")

    # Vérifier l'inscription
    course['enroll'] = False
    if request.user.is_authenticated:
        course['enroll'] = Enrollment.objects.filter(
            user=request.user,
            course_id=course_id
        ).exists()

    # Contenu du cours
    course_content = []
    try:
        api_url = f"https://api.thinkific.com/api/v2/courses/{course_id}/content"
        headers = {
            "X-Auth-Token": settings.THINKIFIC['AUTH_TOKEN'],
            "X-Auth-Subdomain": settings.THINKIFIC['SITE_ID'],
            "Content-Type": "application/json"
        }
        
        content_response = requests.get(api_url, headers=headers)
        content_response.raise_for_status()
        course_content = content_response.json().get('items', [])
        
    except Exception as e:
        print(f"Erreur contenu du cours: {e}")
        course_content = []

    # Instructeur
    instructor_id = course.get('instructor_id')
    instructor = None

    if instructor_id:
        try:
            instructor = thinkific.instructors.retrieve_instructor(id=instructor_id)
        except requests.exceptions.HTTPError:
            instructor = {'first_name': 'Instructeur', 'last_name': 'Inconnu', 'bio': ''}
    else:
        instructor = {'first_name': 'Instructeur', 'last_name': 'Non Spécifié', 'bio': ''}
    
    return render(request, 'pages/course_details.html', {
        'course': course, 
        'instructor': instructor,
        'course_content': course_content,
    })