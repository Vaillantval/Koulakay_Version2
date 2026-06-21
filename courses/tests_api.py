"""Tests API — Catalogue & apprentissage (Phase 5)."""
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from courses.models import Enrollment

User = get_user_model()
DUMMY_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}

SAMPLE_COURSES = [{'id': 111, 'name': 'Cours A', 'slug': 'cours-a', 'description': 'desc',
                   'course_card_image_url': '', 'banner_image_url': ''}]
SAMPLE_PRODUCTS = [{'productable_id': 111, 'productable_type': 'Course', 'price': '10', 'days_until_expiry': 180}]


@override_settings(CACHES=DUMMY_CACHE)
class CatalogueAPITests(TestCase):
    def setUp(self):
        self.c = APIClient()

    @patch('courses.api_cache.products_list', return_value=SAMPLE_PRODUCTS)
    @patch('courses.api_cache.courses_list', return_value=SAMPLE_COURSES)
    def test_course_list_public(self, m_c, m_p):
        r = self.c.get('/api/v1/courses/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        item = r.data['results'][0]
        self.assertEqual(item['id'], 111)
        self.assertFalse(item['is_free'])
        self.assertEqual(item['access_duration'], '6 mois')
        self.assertFalse(item['enrolled'])  # anonyme

    def test_categories_public(self):
        r = self.c.get('/api/v1/categories/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('results', r.data)

    def test_my_enrollments_requires_auth(self):
        self.assertEqual(self.c.get('/api/v1/my/enrollments/').status_code, 401)

    def test_enroll_requires_auth(self):
        self.assertEqual(self.c.post('/api/v1/courses/111/enroll/').status_code, 401)

    def test_access_requires_auth(self):
        self.assertEqual(self.c.get('/api/v1/courses/111/access/').status_code, 401)

    def test_my_enrollments_fallback_db(self):
        u = User.objects.create_user(email='enr@b.com', password='SuperPass123!', first_name='E')
        from django.utils import timezone
        Enrollment.objects.create(user=u, thinkific_user_id=0, course_id=111,
                                  activated_at=timezone.now(), expiry_date=timezone.now())
        self.c.force_authenticate(u)
        with patch('courses.api_cache.courses_list', return_value=SAMPLE_COURSES), \
             patch('courses.api_cache.products_list', return_value=SAMPLE_PRODUCTS):
            r = self.c.get('/api/v1/my/enrollments/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['id'], 111)

    def test_enroll_already_enrolled(self):
        u = User.objects.create_user(email='already@b.com', password='SuperPass123!', first_name='A')
        from django.utils import timezone
        Enrollment.objects.create(user=u, thinkific_user_id=0, course_id=111,
                                  activated_at=timezone.now(), expiry_date=timezone.now())
        self.c.force_authenticate(u)
        r = self.c.post('/api/v1/courses/111/enroll/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data.get('already_enrolled'))

    def test_access_not_enrolled_forbidden(self):
        u = User.objects.create_user(email='noenr@b.com', password='SuperPass123!', first_name='N')
        self.c.force_authenticate(u)
        r = self.c.get('/api/v1/courses/999/access/')
        self.assertEqual(r.status_code, 403)
