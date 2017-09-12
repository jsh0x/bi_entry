from smtplib import SMTP
from email.message import EmailMessage
msg = EmailMessage()

usr, pwd = ('jredding',
            'JRSep17!')

me = 'Joshua.Reddington@bi.com'
subject = 'THIS_IS_A_SUBJECT'
to_recipients = ['Joshua.Reddington@bi.com', 'Joshua.Reddington@bi.com']
cc_recipients = ['Joshua.Reddington@bi.com']
msg['From'] = me
msg['To'] = ', '.join(to_recipients)
msg['Cc'] = ', '.join(to_recipients)
msg['Subject'] = subject
msg.set_content('Hi,\n This is content.')

# with SMTP('owa.bi.com', 587) as smtp:
with SMTP('smtp.outlook.com', 587) as smtp:
    smtp.set_debuglevel(1)
    smtp.ehlo()
    smtp.starttls()
    smtp.login(usr, pwd)
    smtp.send_message(msg)