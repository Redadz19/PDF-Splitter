# إعداد النشر — WARAKA License API

## الموارد
1. أنشئ قاعدة PostgreSQL في Neon وخذ رابط الاتصال مع SSL.
2. في Render اختر New > Blueprint واربط مستودع Redadz19/PDF-Splitter؛ سيقرأ ملف render.yaml من جذر المستودع.
3. أدخل DATABASE_URL بصيغة postgresql+psycopg://... مع sslmode=require.
4. أنشئ مفتاح Ed25519 محلياً وضع القيمة Base64 في LICENSE_PRIVATE_KEY داخل Render فقط.
5. أنشئ سرّين عشوائيين مستقلين: ADMIN_API_KEY وOTP_SECRET (الأخير 32 بايت عشوائية على الأقل).
6. جهّز حساب SMTP موثوقاً، ثم أدخل SMTP_HOST وSMTP_PORT وSMTP_USER وSMTP_PASSWORD وSMTP_FROM في Render.
7. لا تشارك القيم السرية في المحادثة أو GitHub.

## التحقق بعد النشر
- افتح /health وتأكد من ظهور status=ok.
- افتح /docs لمراجعة واجهة API.
- اختبر إرسال OTP إلى بريد تملكه باستخدام ترخيص تجريبي.
- لا تختبر تفعيل تراخيص حقيقية قبل التأكد من إعداد SMTP والمفتاح الخاص وقاعدة البيانات.

## تنبيهات
لم يتم إنشاء خدمة Render أو قاعدة Neon بعد؛ يتطلب ذلك ربط الحسابين ومنح الصلاحيات. الخطة المجانية مناسبة للتجربة وليست ضمان توافر للإنتاج. يجب إضافة Alembic migrations، اختبارات تكامل، rate limiting على مستوى التطبيق/الوكيل، سجل تدقيق، ولوحة إدارة قبل الإطلاق التجاري.
