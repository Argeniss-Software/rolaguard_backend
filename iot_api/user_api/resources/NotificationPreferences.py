from flask import request, render_template
from flask_restful import Resource
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_mail import Message
import boto3

import random
import string
import json
import iot_logging

from threading import Thread
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from iot_api import bcrypt, mail, app
from iot_api.user_api.model import User
#from iot_api.user_api.enums import WebUrl
from iot_api.user_api.models import (
    NotificationPreferences, NotificationAlertSettings,
    NotificationDataCollectorSettings, NotificationAdditionalEmail,
    NotificationAdditionalTelephoneNumber, DataCollector,
    NotificationAssetImportance
)
from iot_api.user_api import Error

from iot_api.user_api.schemas.notification_preferences_schema import NotificationPreferencesSchema

from iot_api.user_api.singletonURL import singletonURL
from iot_api import config 
import smtplib  
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


LOG = iot_logging.getLogger(__name__)

class NotificationPreferencesAPI(Resource):

    @jwt_required
    def get(self):
        user_identity = get_jwt_identity()
        user = User.find_by_username(user_identity)
        if not user: raise Error.Forbidden()

        preferences = NotificationPreferences.find_one(user.id)
        alert_settings = NotificationAlertSettings.find_one(user.id)
        asset_importance = NotificationAssetImportance.get_with(user.id)
        dc_settings = NotificationDataCollectorSettings.find(user.id)
        emails = NotificationAdditionalEmail.find(user.id)
        phones = NotificationAdditionalTelephoneNumber.find(user.id)

        emails = [item.to_dict() for item in emails]
        phones = [item.to_dict() for item in phones]
        preferences = preferences.to_dict(phones, emails)
        alert_settings = alert_settings.to_dict()
        dc_settings = [dc.to_dict() for dc in dc_settings]

        response = {
            'destinations': preferences,
            'risks': alert_settings,
            'asset_importance': {
                'high' : asset_importance.high,
                'medium' : asset_importance.medium,
                'low' : asset_importance.low,
            },
            'dataCollectors': dc_settings
        }
        return response, 200

    @jwt_required
    def put(self):
        user_identity = get_jwt_identity()
        user = User.find_by_username(user_identity)
        if not user: raise Error.Forbidden()

        body = json.loads(request.data)
        parsed_result = NotificationPreferencesSchema().load(body).data
        
        global activation_emails, activation_sms
        activation_emails = []
        activation_sms = []

        # Update destinations
        try:
            destinations = parsed_result.get('destinations')
            np = NotificationPreferences.find_one(user.id)
            for destination in destinations:
                attr = destination.get('destination')
                if attr not in ('sms', 'push', 'email'):
                    LOG.error('Destination must be one these: sms, push, email. It\'s: {0}'.format(attr))
                    return {'error': 'Destination must be one these: sms, push, email'}, 400
                setattr(np, attr, destination.get('enabled'))
                if attr == 'sms' and destination.get('enabled'):
                    existing_phones = NotificationAdditionalTelephoneNumber.find(user.id)
                    for phone in existing_phones:
                        if len(list(filter(lambda item: item.get('id') == phone.id, destination.get('additional')))) == 0:
                            phone.delete()

                    for phone in destination.get('additional'):
                        id = phone.get('id')
                        phone = phone.get('phone')
                        if id:
                            filtered_phones = list(filter(lambda item: id == item.id, existing_phones))
                            if len(filtered_phones) == 0:
                                NotificationPreferences.rollback()
                                LOG.error('Not exist phone id {0}'.format(id))
                                return {'error': 'not exist id'}, 400
                            elif filtered_phones[0].phone != phone:
                                filtered_phones[0].phone = phone
                                filtered_phones[0].active = False
                                token = random_string(10)
                                filtered_phones[0].token = quote_plus(token)
                                filtered_phones[0].creation_date = datetime.now()
                                activation_sms.append({'phone': phone, 'token': filtered_phones[0].token})

                        else:
                            token = random_string(10)
                            token = quote_plus(token)
                            activation_sms.append({'phone': phone, 'token': token})
                            NotificationAdditionalTelephoneNumber(phone=phone, creation_date=datetime.now(), token = token, active = False, user_id = user.id).save() # Then change it to False

                if attr == 'email' and destination.get('enabled'):
                    existing_emails = NotificationAdditionalEmail.find(user.id)
                    for email in existing_emails:
                        if len(list(filter(lambda item: item.get('id') == email.id, destination.get('additional')))) == 0:
                            email.delete()

                    for email in destination.get('additional'):
                        id = email.get('id')
                        email = email.get('email').lower()
                        if id:
                            filtered_emails = list(filter(lambda item: id == item.id, existing_emails))
                            if len(filtered_emails) == 0:
                                NotificationPreferences.rollback()
                                LOG.error('Not exist email id {0}'.format(id))
                                return {'error': 'not exist id'}, 400
                            elif filtered_emails[0].email != email:
                                filtered_emails[0].email = email
                                filtered_emails[0].active = False
                                token = random_string(10)
                                filtered_emails[0].token = quote_plus(token)
                                filtered_emails[0].creation_date = datetime.now()
                                activation_emails.append({'email': email, 'token': filtered_emails[0].token})

                        else:
                            token = random_string(10)
                            token = quote_plus(token)
                            activation_emails.append({'email': email, 'token': token})
                            NotificationAdditionalEmail(email=email, creation_date=datetime.now(), token = token, active = False, user_id = user.id).save()                

            # Update emails -> Delete removed, add new as pending, change to pending to updated
            # Update phones ->Delete removed, add new as pending, change to pending to updated

            # Update risks
            risks = parsed_result.get('risks')
            nas = NotificationAlertSettings.find_one(user.id)  
            for risk in risks:
                attr = risk.get('name')
                if attr not in ('high', 'medium', 'low', 'info'):
                    NotificationPreferences.rollback()
                    LOG.error('Risk must be one these: high, medium, low, info. But it\'s: {0}'.format(attr))
                    return {'error': 'Risk must be one these: high, medium, low, info'}, 400
                setattr(nas, attr, risk.get('enabled'))

            # Update asset importances
            nas = NotificationAssetImportance.get_with(user_id = user.id)  
            for pair in parsed_result['asset_importance']:
                if attr not in ('high', 'medium', 'low', 'info'):
                    NotificationPreferences.rollback()
                    LOG.error('Risk must be one these: high, medium, low, info. But it\'s: {0}'.format(attr))
                    return {'error': 'Risk must be one these: high, medium, low, info'}, 400
                setattr(nas, attr, risk.get('enabled'))

            # Update data collectors. Check if dc belongs to user organization
            data_collectors = parsed_result.get('data_collectors')
            for dcp in data_collectors:
                dc = DataCollector.find_by_id(dcp.get('data_collector_id'))
                if dc and dc.organization_id != user.organization_id:
                    NotificationPreferences.rollback()
                    return None, 403
                if dc:
                    settings = NotificationDataCollectorSettings.find_one(user_id = user.id, data_collector_id = dc.id)
                if dc and settings:
                    settings.enabled = dcp.get('enabled')

            NotificationPreferences.commit()
            
            thread = Thread(target = send_activation_emails)
            thread.setDaemon(True)
            thread.start()

            thread = Thread(target = send_activation_sms)
            thread.setDaemon(True)
            thread.start()

        except Exception as exc:
            NotificationPreferences.rollback()
            LOG.error(exc)
            return {'error': 'Something went wrong'}, 500


class NotificationEmailActivationAPI(Resource):

    def put(self, token):
        email = NotificationAdditionalEmail.find_one_by_token(token)

        if not email:
            return None, 404
        
        if email.active:
            return {'code': 'EMAIL_ALREADY_ACTIVE'}, 400

        if email.creation_date + timedelta(hours=24) < datetime.now():
            return {'code': 'DISABLED_TOKEN'}

        email.active = True
        email.update()
        return {'email': email.email}, 200


class NotificationPhoneActivationAPI(Resource):

    def put(self, token):
        phone = NotificationAdditionalTelephoneNumber.find_one_by_token(token)

        if not phone:
            return None, 404
        
        if phone.active:
            return {'code': 'PHONE_ALREADY_ACTIVE'}, 400

        if phone.creation_date + timedelta(hours=24) < datetime.now():
            return {'code': 'DISABLED_TOKEN'}

        phone.active = True
        phone.update()
        return {'phone': phone.phone}, 200        

def send_activation_emails():
    with app.app_context():
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
        #server.set_debuglevel(1)
        server.ehlo()
        server.starttls()
        #stmplib docs recommend calling ehlo() before & after starttls()
        server.ehlo()
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        single = singletonURL()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "RoLaGuard Email Confirmation"
        msg['From'] = email.utils.formataddr((config.SMTP_SENDER_NAME, config.SMTP_SENDER))

        for item in activation_emails:
            token = item.get('token')
            email_user = item.get('email')
            full_url = single.getParam() + "notifications/email_activation/" + str(token)
            print('init email sending')
            msg['To'] = email_user
            part = MIMEText(render_template(
                'notification_activation.html', full_url=full_url),'html')
            msg.attach(part)
            server.sendmail(config.SMTP_SENDER,email_user, msg.as_string())
            print("finished email sending")
        server.close()    

def send_activation_sms():
    if config.SEND_SMS:
        sns = boto3.client('sns')
        for item in activation_sms:
            token = item.get('token')
            phone = item.get('phone')
            single = singletonURL()
            full_url = single.getParam() + "notifications/phone_activation/" + str(token)
            sns.publish(
                PhoneNumber=phone,
                Message='Please activate this phone to receive RoLaGuard notifications by clicking the link below. ' + full_url,
            )

def random_string(length):
    """Generate a random string with the combination of lowercase and uppercase letters """
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))