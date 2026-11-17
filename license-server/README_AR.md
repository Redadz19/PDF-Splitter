# خادم تراخيص WARAKA

خادم FastAPI وPostgreSQL مهيأ مبدئياً لـ Render وNeon.

## الوظائف
- إصدار تراخيص Reader وPro عبر API الإدارة.
- تفعيل الترخيص بالرقم التسلسلي والبريد المسجل مع إثبات ملكية البريد برمز OTP.
- رمز OTP من 6 أرقام، صلاحيته 10 دقائق، بحد أقصى 5 محاولات، وفاصل 60 ثانية بين الطلبات.
- حد أقصى ثلاثة أجهزة نشطة لكل ترخيص.
- التحقق من الترخيص والجهاز وإيقاف الترخيص وإلغاء تفعيل الجهاز إدارياً.
- توقيع رموز الترخيص باستخدام Ed25519.

## متغيرات البيئة
اضبط المتغيرات التالية في Render أو ملف بيئة محلي:
- DATABASE_URL: رابط Neon بصيغة postgresql+psycopg://... مع SSL.
- LICENSE_PRIVATE_KEY: مفتاح Ed25519 الخاص بصيغة Base64؛ يبقى على الخادم.
- ADMIN_API_KEY: مفتاح طويل عشوائي لنقاط الإدارة.
- OTP_SECRET: سر عشوائي مستقل لا يقل عن 32 حرفاً.
- SMTP_HOST وSMTP_PORT وSMTP_USER وSMTP_PASSWORD وSMTP_FROM: بيانات SMTP لإرسال رموز التحقق.
- LICENSE_ISSUER: اسم مصدر الترخيص.

لا تضع أي قيمة سرية في GitHub أو داخل تطبيق Windows. ملف .env.example لا يحتوي أسراراً فعلية.

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
uvicorn app.main:app --reload
```

يلزم ضبط DATABASE_URL قبل تشغيل التطبيق. ينشئ الإصدار التأسيسي الجداول تلقائياً عند بدء التشغيل. قبل الإنتاج ينبغي اعتماد Alembic migrations بدلاً من create_all، وإضافة اختبارات تلقائية ومحددات معدل على مستوى الشبكة وسجل تدقيق ولوحة إدارة.

## حالة المشروع
هذه مرحلة تأسيسية وليست جاهزة للبيع أو الإنتاج بعد. لم يتم حتى الآن نشر الخدمة على Render أو إنشاء قاعدة Neon أو ربط تطبيق Windows. كما أن سياسة التحقق الدوري والعمل دون اتصال وعميل التحقق من Ed25519 داخل WARAKA Pro لم تدمج بعد.
