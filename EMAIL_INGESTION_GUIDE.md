# 📧 Email Recipe Ingestion Guide

## 🎯 Overview

The Email Recipe Ingestion feature allows approved email addresses to send recipe photos to a dedicated system email address, which are automatically processed and added to the Plenary Pantry database. This is perfect for sharing recipes with family members, friends, or team members who can send recipe photos from their phones or computers.

## 🚀 Features

### **Approved Sender System**
- Centralized approved sender list for the entire system
- Any email on the approved list can send recipe photos
- Senders can be activated/deactivated as needed
- Optional sender names for better identification

### **Automatic Processing**
- Emails are automatically polled and processed
- Image attachments are extracted and processed with OCR
- Recipes are automatically normalized and saved to the database
- Duplicate detection prevents recipe conflicts

### **Comprehensive Tracking**
- Full email history with sender information
- Attachment processing status and error tracking
- Detailed processing logs for debugging
- Admin interface for monitoring and management

## 🛠️ Setup & Configuration

### **1. Email Server Configuration**

Add the following environment variables to your `.env` file:

```env
# Email Ingestion Settings
EMAIL_INGESTION_IMAP_SERVER=imap.gmail.com
EMAIL_INGESTION_IMAP_PORT=993
EMAIL_INGESTION_EMAIL=your-recipe-email@domain.com
EMAIL_INGESTION_PASSWORD=your-app-password
EMAIL_INGESTION_USE_SSL=True
EMAIL_INGESTION_FOLDER=INBOX
EMAIL_INGESTION_POLL_INTERVAL=300
EMAIL_INGESTION_RECIPIENT_ALIAS=recipes@yourdomain.com
EMAIL_INGESTION_MAX_ATTACHMENT_SIZE=10485760
EMAIL_INGESTION_DEFAULT_USER="julia.guimiot@gmail.com"
```

### **2. Gmail Setup (Recommended)**

For Gmail, you'll need to:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password in `EMAIL_INGESTION_PASSWORD`

3. **Configure IMAP**:
   - Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP access

### **3. Other Email Providers**

The system supports any IMAP-compatible email provider:

- **Outlook/Hotmail**: `outlook.office365.com:993`
- **Yahoo**: `imap.mail.yahoo.com:993`
- **Custom IMAP**: Configure your server details

## 📱 Usage Instructions

### **For Recipe Senders**

1. **Take Photos**: Capture clear photos of recipe cards, cookbook pages, or printed recipes
2. **Send Email**: Compose an email to the configured recipe email address (the `EMAIL_INGESTION_RECIPIENT_ALIAS`)
3. **Attach Photos**: Add the recipe photos as attachments
4. **Send**: The system will automatically process the images

**Important**: The email must be addressed to the exact recipient alias configured in `EMAIL_INGESTION_RECIPIENT_ALIAS`. This ensures only emails intended for recipe ingestion are processed.

**Tips for Better Results:**
- Use good lighting and avoid shadows
- Take photos from directly above the recipe
- Ensure text is clear and readable
- Use high resolution photos
- Avoid blurry or angled shots

### **For System Administrators**

1. **Set Up Approved Senders**:
   ```bash
   # Add approved email senders
   uv run python manage.py manage_approved_senders --add "friend@example.com"
   uv run python manage.py manage_approved_senders --add "John Doe <john@example.com>"
   ```

2. **Start Email Polling**:
   ```bash
   # Run once (test)
   uv run python manage.py poll_emails --once
   
   # Run continuously (recommended for production)
   uv run python manage.py poll_emails --interval 300
   ```

3. **Monitor Processing**:
   - Check the Django admin for email sources and attachments
   - View approved sender list and status
   - Review processing logs for any issues

## 🔧 Management Commands

### **Email Polling**

```bash
# Poll emails once and exit
uv run python manage.py poll_emails --once

# Poll emails continuously with custom interval
uv run python manage.py poll_emails --interval 300 --verbose

# Default: polls every 5 minutes (300 seconds)
uv run python manage.py poll_emails
```

### **Approved Senders Management**

```bash
# List all approved senders
uv run python manage.py manage_approved_senders --list

# Add a new approved sender
uv run python manage.py manage_approved_senders --add "john@example.com"
uv run python manage.py manage_approved_senders --add "Jane Smith <jane@example.com>"

# Activate an approved sender
uv run python manage.py manage_approved_senders --activate "john@example.com"

# Deactivate an approved sender
uv run python manage.py manage_approved_senders --deactivate "john@example.com"

# Remove an approved sender
uv run python manage.py manage_approved_senders --remove "john@example.com"
```

## 🌐 Web Interface

### **Approved Senders Management**

Access: Django Admin → Approved Email Senders

Features:
- Add new email addresses that can send recipes
- Activate/deactivate approved senders
- Delete approved senders
- View sender status and creation dates
- Optional sender names for identification

### **Email History**

Access: Django Admin → Email Ingestion Sources

Features:
- View all processed emails
- See attachment details and processing status
- Track sender information and timestamps
- Monitor processing errors and success rates
- Check if senders were on approved list

## 🔍 Admin Interface

The Django admin provides comprehensive management tools:

### **Approved Email Senders**
- Manage the centralized approved sender list
- View sender status and activity
- Search by email address or sender name

### **Email Ingestion Sources**
- View all processed emails
- Track sender information and subjects
- Monitor attachment counts and processing status

### **Email Attachments**
- Individual attachment tracking
- Processing status and error messages
- File size and content type information

## 📊 Monitoring & Troubleshooting

### **Processing Logs**

Check processing logs in the Django admin:
- **ProcessingLog**: Detailed step-by-step processing information
- **IngestionJob**: Overall job status and results
- **EmailAttachment**: Individual attachment processing status

### **Common Issues**

1. **No Emails Processed**:
   - Check IMAP server configuration
   - Verify email credentials
   - Ensure approved senders are active
   - Check polling service is running

2. **OCR Quality Issues**:
   - Request better quality photos
   - Ensure good lighting and clear text
   - Check image file formats are supported

3. **Duplicate Recipes**:
   - System automatically detects duplicates
   - Keeps the recipe with more ingredients
   - Updates existing recipes with better data

### **Performance Monitoring**

Monitor these metrics:
- Email processing frequency
- Attachment processing success rate
- Recipe creation success rate
- Processing time per email

## 🔒 Security Considerations

### **Email Security**
- Use app-specific passwords (not account passwords)
- Enable 2-factor authentication on email accounts
- Regularly rotate email credentials
- Monitor email access logs

### **Access Control**
- Only approved email addresses can send recipes
- Approved senders can be deactivated instantly
- All processing is logged and auditable
- Centralized system with single default user

### **Data Protection**
- Email content is stored securely
- Attachments are processed and stored locally
- Raw email data can be purged after processing
- All recipes are stored under the default user account

## 🚀 Production Deployment

### **Email Polling Service**

For production, run the email polling service as a background process:

```bash
# Using systemd (Linux)
sudo systemctl enable plenary-pantry-email-polling
sudo systemctl start plenary-pantry-email-polling

# Using supervisor
[program:email-polling]
command=/path/to/venv/bin/python manage.py poll_emails
directory=/path/to/project
autostart=true
autorestart=true
user=www-data
```

### **Monitoring**

Set up monitoring for:
- Email polling service status
- Processing success rates
- Error rates and types
- Storage usage for attachments

### **Backup Strategy**

Include in backups:
- Email attachment files
- Processing logs
- Approved sender list
- Recipe data

## 📈 Scaling Considerations

### **High Volume Processing**

For high email volumes:
- Increase polling frequency
- Use multiple email accounts
- Implement email queue processing
- Add horizontal scaling for processing

### **Storage Management**

- Implement attachment cleanup policies
- Compress old email data
- Archive processed emails
- Monitor disk usage

## 🔮 Future Enhancements

### **Planned Features**
- **Email Templates**: Pre-configured email templates for senders
- **Batch Processing**: Process multiple emails simultaneously
- **Smart Routing**: Route emails to specific users based on content
- **Email Notifications**: Notify users when recipes are processed
- **Advanced OCR**: Support for handwritten recipes
- **Multi-language**: Support for non-English recipes

### **Integration Opportunities**
- **Calendar Integration**: Schedule recipe processing
- **Social Sharing**: Share processed recipes via email
- **Recipe Validation**: AI-powered recipe validation
- **Nutritional Analysis**: Extract nutritional information

## 📞 Support

### **Getting Help**

1. **Check Logs**: Review processing logs in Django admin
2. **Test Configuration**: Use `--once` flag to test email polling
3. **Verify Approved Senders**: Ensure approved senders are active
4. **Check Permissions**: Verify email account permissions

### **Common Commands**

```bash
# Test email polling once
uv run python manage.py poll_emails --once --verbose

# Check approved senders
uv run python manage.py manage_approved_senders --list

# View recent processing logs
# (Check Django admin → ProcessingLog)

# Test email configuration
# (Send a test email with recipe photos)
```

---

**Happy Recipe Ingestion! 📧🍳**

For more information, see the main [Recipe Ingestion README](RECIPE_INGESTION_README.md).
