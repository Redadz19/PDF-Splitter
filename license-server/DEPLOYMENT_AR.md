# إعداد النشر — WARAKA License API

1. أنشئ مشروع PostgreSQL في Neon وخذ رابط الاتصال مع تفعيل SSL.
2. في Render اختر New > Blueprint واربط مستودع Redadz19/PDF-Splitter، وسيقرأ ملف render.yaml من جذر المستودع.
3. أدخل DATABASE_URL بصيغة postgresql+psycopg://... مع sslmode=require.
4. أنشئ مفتاح Ed25519 محلياً واحتفظ بالقيمة Base64 في LICENSE_PRIVATE_KEY داخل Render فقط.
5. أنشئ قيمة عشوائية طويلة لـ ADMIN_API_KEY واحفظها في مدير كلمات المرور، ثم أدخلها في Render.
6. لا تشارك القيم السرية في المحادثة أو GitHub.

لم يتم إنشاء خدمة Render أو قاعدة Neon بعد؛ يتطلب ذلك ربط الحسابين ومنح الصلاحيات. الخطة المجانية مناسبة للتجربة وليست ضمان توافر للإنتاج.
