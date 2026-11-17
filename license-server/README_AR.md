# خادم تراخيص WARAKA — الإصدار التأسيسي

خادم مستقل باستخدام FastAPI وPostgreSQL (Neon)، ومهيأ للنشر على Render.

## الوظائف المبدئية
- إصدار تراخيص Reader وPro من واجهة الإدارة البرمجية.
- تفعيل باستخدام الرقم التسلسلي والبريد المسجل معاً.
- حد أقصى ثلاثة أجهزة نشطة لكل ترخيص.
- التحقق من حالة الترخيص والجهاز، وإلغاء تفعيل الجهاز.
- إيقاف الترخيص من واجهة الإدارة.
- توقيع رموز الترخيص باستخدام Ed25519.

## إعداد البيئة
أنشئ قاعدة PostgreSQL في Neon، ثم اضبط DATABASE_URL وLICENSE_PRIVATE_KEY وADMIN_API_KEY كمتغيرات بيئة. لا تضع المفتاح الخاص أو مفتاح الإدارة في GitHub أو داخل تطبيق Windows.

توليد مفتاح Ed25519 محلياً:

```python
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
key = Ed25519PrivateKey.generate()
raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
print(base64.b64encode(raw).decode())
```

## التشغيل المحلي
pip install -r requirements.txt
uvicorn app.main:app --reload

## المسارات
GET /health
GET /v1/public-key
POST /v1/activate
POST /v1/validate
POST /v1/deactivate
POST /v1/admin/licenses
GET /v1/admin/licenses
POST /v1/admin/licenses/{id}/disable

وثائق API في /docs. تتطلب نقاط الإدارة ترويسة X-Admin-Key.

## ملاحظات أمنية وحالة الإنجاز
هذا هيكل Backend أولي وليس نظاماً جاهزاً للإنتاج. خيار البريد هنا يعني مطابقة البريد المسجل مع الرقم التسلسلي؛ لا يوجد إرسال رمز OTP أو إثبات ملكية البريد حتى الآن. يجب إضافة OTP عبر SMTP قبل البيع العام. كما يجب بناء لوحة إدارة رسومية، وإضافة اختبارات تلقائية وسجل تدقيق وحدود للطلبات وترحيلات قاعدة البيانات.

قبل إطلاق WARAKA Pro يجب دمج التحقق من توقيع Ed25519 في التطبيق نفسه، وربط كل عملية مدفوعة بحالة ترخيص صحيحة، مع سياسة تحقق دوري ومهلة عمل دون اتصال. لا تعتبر إخفاء الأزرار حماية كافية.
