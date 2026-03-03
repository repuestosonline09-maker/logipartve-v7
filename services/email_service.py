"""
Servicio de envío de emails usando Resend API
Reemplaza el sistema SMTP tradicional con API REST
"""

import os
import resend
from typing import Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails usando Resend API"""
    
    def __init__(self):
        """Inicializar el servicio de email con la API Key de Resend"""
        self.api_key = os.environ.get('RESEND_API_KEY')
        if self.api_key:
            resend.api_key = self.api_key
            logger.info("✅ Resend API inicializada correctamente")
        else:
            logger.warning("⚠️ RESEND_API_KEY no configurada en variables de entorno")
    
    def send_password_recovery_email(
        self, 
        to_email: str, 
        reset_link: str, 
        username: str
    ) -> tuple[bool, str]:
        """
        Enviar email de recuperación de contraseña
        
        Args:
            to_email: Email del destinatario
            reset_link: Link de recuperación de contraseña
            username: Nombre de usuario
            
        Returns:
            tuple: (éxito: bool, mensaje: str)
        """
        if not self.api_key:
            error_msg = "Error: RESEND_API_KEY no configurada"
            logger.error(error_msg)
            return False, error_msg
        
        try:
            # Crear el contenido HTML del email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #f9f9f9;
                        border-radius: 10px;
                        padding: 30px;
                        border: 1px solid #ddd;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .header h1 {{
                        color: #2c3e50;
                        margin: 0;
                    }}
                    .content {{
                        background-color: white;
                        padding: 20px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 12px 30px;
                        background-color: #3498db;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .button:hover {{
                        background-color: #2980b9;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 12px;
                        color: #666;
                        margin-top: 20px;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 10px;
                        margin: 15px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 LogiPartVE Pro</h1>
                        <p>Recuperación de Contraseña</p>
                    </div>
                    
                    <div class="content">
                        <p>Hola <strong>{username}</strong>,</p>
                        
                        <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en LogiPartVE Pro.</p>
                        
                        <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
                        
                        <div style="text-align: center;">
                            <a href="{reset_link}" class="button">Restablecer Contraseña</a>
                        </div>
                        
                        <p>O copia y pega este enlace en tu navegador:</p>
                        <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
                            {reset_link}
                        </p>
                        
                        <div class="warning">
                            <strong>⚠️ Importante:</strong> Este enlace expirará en 1 hora por razones de seguridad.
                        </div>
                        
                        <p>Si no solicitaste restablecer tu contraseña, puedes ignorar este correo de forma segura.</p>
                    </div>
                    
                    <div class="footer">
                        <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                        <p>&copy; 2026 LogiPartVE Pro - Cotizador Global de Repuestos v7.0</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Enviar email usando Resend API
            params = {
                "from": "LogiPartVE <noreply@logipartve.com>",  # Dominio verificado
                "to": [to_email],
                "subject": "🔐 Recuperación de Contraseña - LogiPartVE Pro",
                "html": html_content,
            }
            
            logger.info(f"📧 Enviando email de recuperación a: {to_email}")
            
            response = resend.Emails.send(params)
            
            logger.info(f"✅ Email enviado exitosamente. ID: {response.get('id', 'N/A')}")
            
            return True, "Email enviado exitosamente"
            
        except Exception as e:
            error_msg = f"Error al enviar email: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def send_test_email(self, to_email: str) -> tuple[bool, str]:
        """
        Enviar email de prueba
        
        Args:
            to_email: Email del destinatario
            
        Returns:
            tuple: (éxito: bool, mensaje: str)
        """
        if not self.api_key:
            return False, "RESEND_API_KEY no configurada"
        
        try:
            params = {
                "from": "LogiPartVE <noreply@logipartve.com>",
                "to": [to_email],
                "subject": "✅ Email de Prueba - LogiPartVE Pro",
                "html": "<h1>¡Hola!</h1><p>Este es un email de prueba desde LogiPartVE Pro.</p>",
            }
            
            response = resend.Emails.send(params)
            return True, f"Email de prueba enviado. ID: {response.get('id', 'N/A')}"
            
        except Exception as e:
            return False, f"Error: {str(e)}"


    @staticmethod
    def send_approval_email(
        from_name: str,
        from_email: str,
        to_email: str,
        cc_list: list,
        reply_to: str,
        subject: str,
        html_body: str,
        attachments: list,
    ) -> dict:
        """
        Enviar correo de Orden Aprobada con adjuntos PNG.
        Retorna {'success': True} o {'success': False, 'error': str}
        """
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'RESEND_API_KEY no configurada en Railway'}

        resend.api_key = api_key

        try:
            params = {
                "from":        f"{from_name} <{from_email}>",
                "to":          [to_email],
                "subject":     subject,
                "html":        html_body,
                "reply_to":    reply_to,
            }

            if cc_list:
                params["cc"] = cc_list

            if attachments:
                params["attachments"] = attachments

            logger.info(f"📧 Enviando Orden Aprobada a: {to_email} | CC: {cc_list}")
            response = resend.Emails.send(params)
            logger.info(f"✅ Correo enviado. ID: {response.get('id', 'N/A')}")
            return {'success': True, 'id': response.get('id', 'N/A')}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error enviando Orden Aprobada: {error_msg}")
            return {'success': False, 'error': error_msg}


# Instancia global del servicio
email_service = EmailService()
