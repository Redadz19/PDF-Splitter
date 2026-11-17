# خادم تراخيص WARAKA

خادم FastAPI وPostgreSQL مهيأ مبدئياً لـ Render وNeon.

## الوظائف
- إصدار تراخيص Reader وPro عبر API الإدارة.
- تفعيل الترخيص بالرقم التسلسلي والبريد المسجل مع إثبات ملكية البريد برمز OTP.
- رمز OTP من 6 أرقام، صلاحيته 10 دقائق، بحد أقصى 5 محاولات، وفاصل 60 ثانية بين الطلبات.
- حد أقصى ثلاثة أجهزة نشطة لكل ترخيص.
- التحقق من الترخيص والجهاز وإيقاف الترخيص وإلغاء تفعيل الجهاز إدارياً.
- توقيع رموز الترخيص باستخدام Ed25519.
- إدارة بنية قاعدة البيانات عبر Alembic migrations؛ ينفذ Docker ترقية المخطط قبل تشغيل API.

## متغيرات البيئة
- DATABASE_URL: رابط Neon بصيغة postgresql+psycopg://... مع SSL.
- LICENSE_PRIVATE_KEY: مفتاح Ed25519 الخاص بصيغة Base64؛ يبقى على الخادم.
- ADMIN_API_KEY: مفتاح طويل عشوائي لنقاط الإدارة.
- OTP_SECRET: سر عشوائي مستقل لا يقل عن 32 حرفاً.
- SMTP_HOST وSMTP_PORT وSMTP_USER وSMTP_PASSWORD وSMTP_FROM: بيانات SMTP.
- LICENSE_ISSUER: اسم مصدر الترخيص.

لا تضع أي قيمة سرية في GitHub أو داخل تطبيق Windows.

## مسار التفعيل
1. POST /v1/activation/request-code مع serial وemail.
2. يصل رمز OTP إلى البريد المسجل.
3. POST /v1/activate مع serial وemail وcode وdevice_id وdevice_name.
4. يعيد الخادم رمز ترخيص موقعاً؛ يجب على تطبيق WARAKA التحقق من توقيعه محلياً بمفتاح Ed25519 العام.

## المسارات
- GET /health
- GET /v1/public-key
- POST /v1/activation/request-code
- POST /v1/activate
- POST /v1/validate
- POST /v1/deactivate (إداري)
- POST /v1/admin/licenses (إداري)
- GET /v1/admin/licenses (إداري)
- POST /v1/admin/licenses/{id}/disable (إداري)

تتطلب نقاط الإدارة ترويسة X-Admin-Key. وثائق API في /docs.

## التشغيل المحلي
من مجلد license-server:
```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## حالة المشروع
مرحلة تأسيسية قيد التطوير وليست جاهزة للبيع أو الإنتاج. لم يتم نشر الخدمة على Render أو إنشاء Neon أو ربط تطبيق Windows. يلزم استكمال اختبارات التكامل، rate limiting، سجل التدقيق، لوحة الإدارة، والتحقق الدوري والعمل دون اتصال.
