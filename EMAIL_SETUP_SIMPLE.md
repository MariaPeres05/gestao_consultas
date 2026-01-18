# 📧 Email Notifications - Simple Setup (Threading + APScheduler)

## ✅ Super Simple - All Automatic!

This implementation uses:
- **Threading** for immediate emails (confirmation/cancellation)
- **APScheduler** for periodic reminders (runs automatically with Django)
- **No external services needed** - Redis, Celery, Task Scheduler, or cron!

---

## 🎯 Features

### 1. **Confirmation Emails** ✓
Sent automatically when consultation is confirmed:
- Patient confirms AND doctor already accepted → Email sent
- Doctor confirms AND patient already accepted → Email sent
- **Non-blocking**: Uses threading, user doesn't wait for email

### 2. **Cancellation Emails** ✗
Sent automatically when:
- Patient cancels consultation
- Doctor cancels consultation  
- Doctor refuses consultation
- Shows who cancelled and why

### 3. **Reminder Emails** 🔔 (Automatic!)
Scheduled automatically by APScheduler:
- **24-hour reminder**: Runs daily at 9:00 AM
- **2-hour reminder**: Runs every 30 minutes
- **Starts automatically** when you run Django server

---

## 🚀 How It Works

### **Immediate Emails** (Confirmation/Cancellation)
```python
# When user confirms/cancels:
consulta.estado = 'confirmada'
consulta.save()

# Background thread sends email
enviar_email_confirmacao(consulta.id_consulta)

# User sees success instantly!
```

### **Scheduled Reminders** (Automatic!)
```
Django Server Starts
    ↓
APScheduler Initializes (core/apps.py)
    ↓
Schedules 2 background jobs:
    • Daily at 9:00 AM → enviar_lembretes_24h()
    • Every 30 minutes → enviar_lembretes_2h()
    ↓
Jobs run automatically in background!
```

---

## 🔧 Setup (Just Run Django!)

### 1. **Dependencies** (Already installed)
```bash
pip install APScheduler django-apscheduler
```

### 2. **Start Django Server**
```bash
python manage.py runserver
```

**That's it!** APScheduler starts automatically and schedules the reminder tasks.

### 3. **Check Logs**
When Django starts, you'll see:
```
✓ Tarefa agendada: Lembretes 24h (diário às 9:00)
✓ Tarefa agendada: Lembretes 2h (a cada 30 minutos)
🚀 APScheduler iniciado com sucesso!
```

---

## 📁 Files Structure

```
core/
├── apps.py                      # APScheduler initialization
├── email_utils.py               # Email functions + scheduled tasks
└── views.py / views_medico.py   # Call email functions

templates/
└── emails/
    ├── confirmacao_consulta.html
    ├── cancelamento_consulta.html
    └── lembrete_consulta.html
```

---

## 🧪 Testing

### **Test Immediate Emails**
1. Book a consultation
2. Have it confirmed
3. Check console - email output appears immediately
4. ✅ Works!

### **Test Scheduled Reminders**
APScheduler runs automatically, but you can test manually:

```python
python manage.py shell

>>> from core.email_utils import enviar_lembretes_24h, enviar_lembretes_2h

# Test 24h reminder
>>> enviar_lembretes_24h()
# Output: "X lembretes de 24h enviados"

# Test 2h reminder
>>> enviar_lembretes_2h()
# Output: "X lembretes de 2h enviados"
```

---

## 📧 Email Configuration

### **Development** (emails to console)
Already configured in `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### **Production** (real SMTP)
Update `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@medipulse.com
```

---

## 🔍 How APScheduler Works

### **Initialization**
When Django starts, `core/apps.py` → `ready()` method runs:
1. Creates BackgroundScheduler
2. Adds 2 jobs (24h daily, 2h every 30min)
3. Starts scheduler in background
4. Scheduler runs until Django stops

### **Job Execution**
```
9:00 AM arrives
    ↓
APScheduler triggers enviar_lembretes_24h()
    ↓
Function queries database for tomorrow's consultations
    ↓
Sends email to each patient (threading)
    ↓
Logs results
```

### **Advantages Over Task Scheduler**
- ✅ No manual setup needed
- ✅ Cross-platform (Windows/Linux/Mac)
- ✅ Starts automatically with Django
- ✅ Python-native (no external tools)
- ✅ Easy to test and debug
- ✅ Logs visible in Django console

---

## 🔧 Troubleshooting

### **APScheduler not starting?**
Check Django logs when server starts. You should see:
```
✓ Tarefa agendada: Lembretes 24h (diário às 9:00)
✓ Tarefa agendada: Lembretes 2h (a cada 30 minutos)
🚀 APScheduler iniciado com sucesso!
```

If not, check `core/apps.py` for errors.

### **Emails not sending?**
1. Check console for email output (development)
2. Check SMTP credentials (production)
3. Check Django logs for errors
4. Test manually in shell:
   ```python
   from core.email_utils import enviar_email_confirmacao
   enviar_email_confirmacao(1)  # Use real consulta ID
   ```

### **Reminders not running?**
1. Keep Django server running (APScheduler stops when Django stops)
2. Check scheduled jobs in database:
   ```python
   python manage.py shell
   >>> from django_apscheduler.models import DjangoJob
   >>> DjangoJob.objects.all()
   ```

---

## 📊 Comparison

| Feature | APScheduler | Task Scheduler | Celery |
|---------|-------------|----------------|--------|
| **Setup** | Automatic | Manual | Complex |
| **Dependencies** | 2 libraries | None | 3+ services |
| **Cross-platform** | Yes | Windows only | Yes |
| **Starts with Django** | Yes | No | No |
| **External services** | None | None | Redis |
| **For your project** | ✅ Perfect | ⚠️ Manual | ❌ Overkill |

---

## 🎉 Summary

**What you have:**
- ✅ Automatic confirmation emails (threading)
- ✅ Automatic cancellation emails (threading)
- ✅ **Automatic scheduled reminders** (APScheduler)
- ✅ All-in-one Django process
- ✅ No external services
- ✅ No manual setup
- ✅ Just run Django and it works!

**To use:**
1. Start Django: `python manage.py runserver`
2. APScheduler starts automatically
3. Reminders send at scheduled times
4. That's it! 🚀

---

## 🔗 Related Files

- **Scheduler Setup**: [core/apps.py](core/apps.py)
- **Email Functions**: [core/email_utils.py](core/email_utils.py)
- **Patient Views**: [core/views.py](core/views.py)
- **Doctor Views**: [core/views_medico.py](core/views_medico.py)
- **Templates**: [templates/emails/](templates/emails/)

**Everything just works automatically! 😊**

## ✅ Simple Implementation - No Extra Services!

This implementation uses **Python threading** instead of Celery, making it much simpler with no Redis or workers needed.

---

## 🎯 Features

### 1. **Confirmation Emails** ✓
Sent automatically when consultation is confirmed:
- Patient confirms AND doctor already accepted → Email sent
- Doctor confirms AND patient already accepted → Email sent
- **Non-blocking**: Uses threading, user doesn't wait for email

### 2. **Cancellation Emails** ✗
Sent automatically when:
- Patient cancels consultation
- Doctor cancels consultation  
- Doctor refuses consultation
- Shows who cancelled and why

### 3. **Reminder Emails** 🔔
Scheduled using Django management commands:
- **24-hour reminder**: For consultations tomorrow
- **2-hour reminder**: For consultations in 2 hours

---

## 📁 Files Structure

```
core/
├── email_utils.py                      # Email functions with threading
├── management/
│   └── commands/
│       └── enviar_lembretes.py        # Command for reminders
└── views.py / views_medico.py         # Call email functions

templates/
└── emails/
    ├── confirmacao_consulta.html      # Confirmation template
    ├── cancelamento_consulta.html     # Cancellation template
    └── lembrete_consulta.html         # Reminder template
```

---

## 🚀 How It Works

### **Immediate Emails** (Confirmation/Cancellation)

When a user confirms or cancels:
```python
# In views.py
consulta.estado = 'confirmada'
consulta.save()

# This starts a background thread and returns immediately
enviar_email_confirmacao(consulta.id_consulta)

# User sees success message instantly - email sends in background
```

**Advantages:**
- ✅ No extra processes needed
- ✅ Non-blocking (user doesn't wait)
- ✅ Simple to understand
- ✅ No Redis, no Celery, no complexity

**Limitations:**
- ⚠️ If server crashes before email sends, email is lost
- ⚠️ No automatic retries (but works 99% of the time)

---

## ⏰ Scheduled Reminders

### **24-Hour Reminder** (Run daily at 9 AM)

```bash
python manage.py enviar_lembretes --tipo=24h
```

Finds all consultations scheduled for tomorrow and sends reminder emails.

### **2-Hour Reminder** (Run every 30 minutes)

```bash
python manage.py enviar_lembretes --tipo=2h
```

Finds consultations in the next 2 hours and sends reminder emails.

---

## 🔧 Setup Instructions

### 1. **Email Configuration** (Already Done)

In `.env` file:
```env
# Development - emails to console
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Production - real SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@medipulse.com
```

### 2. **Test Immediate Emails**

Just use the application normally:
1. Patient books consultation
2. Doctor confirms → Email sent automatically!
3. Check console for email output (development mode)

### 3. **Schedule Periodic Reminders**

#### **Option A: Windows Task Scheduler** (Recommended for Windows)

**24-hour reminder (daily at 9 AM):**
1. Open Task Scheduler
2. Create Basic Task: "MediPulse Lembrete 24h"
3. Trigger: Daily at 9:00 AM
4. Action: Start a program
   - Program: `C:\Users\marti\Documents\Trabalhos_IPV\IA\gestao_consultas\venv\Scripts\python.exe`
   - Arguments: `manage.py enviar_lembretes --tipo=24h`
   - Start in: `C:\Users\marti\Documents\Trabalhos_IPV\IA\gestao_consultas`

**2-hour reminder (every 30 minutes):**
1. Create Basic Task: "MediPulse Lembrete 2h"
2. Trigger: Daily, repeat every 30 minutes
3. Same action as above but with `--tipo=2h`

#### **Option B: Manual Testing**

Test the commands manually:
```bash
# Test 24h reminder
python manage.py enviar_lembretes --tipo=24h

# Test 2h reminder
python manage.py enviar_lembretes --tipo=2h
```

#### **Option C: Linux/Mac (crontab)**

```bash
crontab -e
```

Add these lines:
```bash
# 24h reminder at 9 AM daily
0 9 * * * cd /path/to/project && /path/to/venv/bin/python manage.py enviar_lembretes --tipo=24h

# 2h reminder every 30 minutes
*/30 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py enviar_lembretes --tipo=2h
```

---

## 🧪 Testing

### **Test Confirmation Email**
1. Create a consultation as patient
2. Have doctor confirm it (or vice versa)
3. Check console - you should see email output

### **Test Cancellation Email**
1. Cancel a confirmed consultation (>24h notice)
2. Check console for cancellation email

### **Test Reminder Commands**
```bash
# Create a test consultation for tomorrow
# Then run:
python manage.py enviar_lembretes --tipo=24h

# You should see:
# 🔔 Enviando lembretes de 24h...
#   ✓ Lembrete enviado para consulta X
# ✅ Total: 1 lembretes de 24h enviados
```

---

## 📊 Email Templates

All templates are in `templates/emails/`:

### **Confirmation** (`confirmacao_consulta.html`)
- Blue header with checkmark
- All consultation details
- Important reminders for patients

### **Reminder** (`lembrete_consulta.html`)
- Orange/yellow alert styling
- "Your consultation is tomorrow / in 2 hours"
- Checklist of what to bring

### **Cancellation** (`cancelamento_consulta.html`)
- Red header with X
- Shows who cancelled
- Rebooking information

---

## 🔍 Troubleshooting

### **Emails not appearing in console?**
Check your `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### **Production emails not sending?**
1. Check SMTP credentials in `.env`
2. For Gmail, use an "App Password" not your regular password
3. Check Django logs for errors

### **Reminders not sending?**
1. Make sure consultations are in `confirmada` state
2. Check the date/time windows match
3. Run command manually to see errors:
   ```bash
   python manage.py enviar_lembretes --tipo=24h
   ```

---

## 📈 Comparison: Threading vs Celery

| Feature | Threading (Current) | Celery |
|---------|-------------------|--------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐⭐⭐ Complex |
| **Extra Services** | None | Redis required |
| **Extra Processes** | None | Worker + Beat |
| **Reliability** | 99% (lost if crash) | 99.9% (persistent) |
| **Retries** | No | Yes (automatic) |
| **Monitoring** | Django logs | Flower, logs |
| **Scalability** | Good for <1000/day | Unlimited |
| **Best For** | Small-medium apps | Enterprise |

**For your project**: Threading is perfect! ✅

---

## 🎉 Summary

**You now have:**
- ✅ Automatic confirmation emails (threading)
- ✅ Automatic cancellation emails (threading)
- ✅ Scheduled reminder commands (management commands)
- ✅ Beautiful HTML email templates
- ✅ **NO Redis, NO Celery, NO complexity!**

**To use reminders:**
- Set up Windows Task Scheduler (or cron)
- Schedule the two commands
- Done! 🚀

---

## 🔗 Related Files

- **Email Functions**: [core/email_utils.py](core/email_utils.py)
- **Reminder Command**: [core/management/commands/enviar_lembretes.py](core/management/commands/enviar_lembretes.py)
- **Patient Views**: [core/views.py](core/views.py)
- **Doctor Views**: [core/views_medico.py](core/views_medico.py)
- **Templates**: [templates/emails/](templates/emails/)

**Need help?** Check the code - it's simple and well-commented! 😊
