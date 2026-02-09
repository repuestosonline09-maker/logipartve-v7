# services/password_recovery.py
# Servicio de recuperación de contraseña por email

import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any
from database.db_manager import DBManager

class PasswordRecoveryService:
    """
    Servicio para gestionar la recuperación de contraseña por email.
    """
    
    @staticmethod
    def send_recovery_email(email: str) -> Dict[str, Any]:
        """
        Envía un email de recuperación de contraseña.
        
        Args:
            email: Email del usuario
            
        Returns:
            Dict con 'success' (bool) y 'message' (str)
        """
        try:
            # Verificar si el email existe en la base de datos
            user = DBManager.get_user_by_email(email)
            
            if not user:
                return {
                    "success": False,
                    "message": "No existe ningún usuario registrado con ese email"
                }
            
            # Generar token único
            token = secrets.token_urlsafe(32)
            
            # Calcular fecha de expiración (1 hora)
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Guardar token en la base de datos
            if not DBManager.create_reset_token(user['id'], token, expires_at):
                return {
                    "success": False,
                    "message": "Error al generar el token de recuperación"
                }
            
            # Obtener configuración SMTP
            smtp_config = PasswordRecoveryService._get_smtp_config()
            
            if not smtp_config:
                return {
                    "success": False,
                    "message": "El sistema de email no está configurado. Contacta al administrador."
                }
            
            # Construir URL de reset
            # TODO: Obtener dominio desde configuración
            reset_url = f"https://www.logipartve.com/?reset_token={token}"
            
            # Enviar email
            result = PasswordRecoveryService._send_email(
                smtp_config=smtp_config,
                to_email=email,
                user_name=user['full_name'],
                reset_url=reset_url
            )
            
            if result['success']:
                return {
                    "success": True,
                    "message": "Email de recuperación enviado exitosamente"
                }
            else:
                return {
                    "success": False,
                    "message": f"Error al enviar el email: {result.get('error', 'Error desconocido')}"
                }
                
        except Exception as e:
            print(f"Error en send_recovery_email: {e}")
            return {
                "success": False,
                "message": f"Error inesperado: {str(e)}"
            }
    
    @staticmethod
    def _get_smtp_config() -> Dict[str, str]:
        """
        Obtiene la configuración SMTP desde la base de datos.
        
        Returns:
            Dict con configuración SMTP o None si no está configurado
        """
        try:
            config = {}
            
            # Obtener configuraciones SMTP
            smtp_server = DBManager.get_config('smtp_server')
            smtp_port = DBManager.get_config('smtp_port')
            smtp_username = DBManager.get_config('smtp_username')
            smtp_password = DBManager.get_config('smtp_password')
            smtp_from_email = DBManager.get_config('smtp_from_email')
            smtp_from_name = DBManager.get_config('smtp_from_name')
            
            if not all([smtp_server, smtp_port, smtp_username, smtp_password, smtp_from_email]):
                return None
            
            config['server'] = smtp_server
            config['port'] = int(smtp_port)
            config['username'] = smtp_username
            config['password'] = smtp_password
            config['from_email'] = smtp_from_email
            config['from_name'] = smtp_from_name or 'LogiPartVE'
            
            return config
            
        except Exception as e:
            print(f"Error al obtener configuración SMTP: {e}")
            return None
    
    @staticmethod
    def _send_email(smtp_config: Dict[str, str], to_email: str, user_name: str, reset_url: str) -> Dict[str, Any]:
        """
        Envía el email de recuperación.
        
        Args:
            smtp_config: Configuración SMTP
            to_email: Email del destinatario
            user_name: Nombre del usuario
            reset_url: URL para resetear contraseña
            
        Returns:
            Dict con 'success' (bool) y 'error' (str) si falla
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Recuperación de Contraseña - LogiPartVE'
            msg['From'] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
            msg['To'] = to_email
            
            # Cuerpo del email en HTML
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #1f77b4; color: white; padding: 20px; text-align: center; }}
                    .content {{ background-color: #f9f9f9; padding: 30px; }}
                    .button {{ display: inline-block; padding: 12px 30px; background-color: #1f77b4; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; font-size: 0.9rem; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>LogiPartVE Pro</h1>
                        <p>Cotizador Global de Repuestos</p>
                    </div>
                    <div class="content">
                        <h2>Hola, {user_name}</h2>
                        <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en LogiPartVE.</p>
                        <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
                        <p style="text-align: center;">
                            <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                        </p>
                        <p>O copia y pega este enlace en tu navegador:</p>
                        <p style="word-break: break-all; background-color: #eee; padding: 10px; border-radius: 3px;">
                            {reset_url}
                        </p>
                        <p><strong>Este enlace expirará en 1 hora.</strong></p>
                        <p>Si no solicitaste restablecer tu contraseña, puedes ignorar este email.</p>
                    </div>
                    <div class="footer">
                        <p>LogiPartVE Pro v7.0 © 2026</p>
                        <p>Este es un email automático, por favor no respondas a este mensaje.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Cuerpo del email en texto plano (fallback)
            text_body = f"""
            Hola, {user_name}
            
            Recibimos una solicitud para restablecer la contraseña de tu cuenta en LogiPartVE.
            
            Copia y pega este enlace en tu navegador para crear una nueva contraseña:
            {reset_url}
            
            Este enlace expirará en 1 hora.
            
            Si no solicitaste restablecer tu contraseña, puedes ignorar este email.
            
            LogiPartVE Pro v7.0 © 2026
            """
            
            # Adjuntar ambas versiones
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Conectar al servidor SMTP y enviar (con timeout de 30 segundos)
            with smtplib.SMTP(smtp_config['server'], smtp_config['port'], timeout=30) as server:
                server.set_debuglevel(0)  # Cambiar a 1 para debug
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            return {"success": True}
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Error de autenticación. Verifica la contraseña de aplicación (sin espacios)"
            print(f"SMTPAuthenticationError: {e}")
            return {"success": False, "error": error_msg}
        except smtplib.SMTPException as e:
            error_msg = f"Error SMTP: {str(e)}"
            print(f"SMTPException: {e}")
            return {"success": False, "error": error_msg}
        except TimeoutError as e:
            error_msg = "Timeout al conectar. Verifica el servidor y puerto SMTP"
            print(f"TimeoutError: {e}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Error inesperado: {error_msg}")
            return {"success": False, "error": error_msg}
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verifica si un token es válido.
        
        Args:
            token: Token de reset
            
        Returns:
            Dict con 'valid' (bool), 'user_id' (int) y 'message' (str)
        """
        try:
            # Obtener token de la base de datos
            token_data = DBManager.get_reset_token(token)
            
            if not token_data:
                return {
                    "valid": False,
                    "message": "Token inválido o ya utilizado"
                }
            
            # Verificar si expiró
            expires_at = datetime.fromisoformat(str(token_data['expires_at']))
            if datetime.now() > expires_at:
                return {
                    "valid": False,
                    "message": "El token ha expirado. Solicita uno nuevo."
                }
            
            return {
                "valid": True,
                "user_id": token_data['user_id'],
                "message": "Token válido"
            }
            
        except Exception as e:
            print(f"Error al verificar token: {e}")
            return {
                "valid": False,
                "message": f"Error al verificar token: {str(e)}"
            }
    
    @staticmethod
    def reset_password(token: str, new_password: str) -> Dict[str, Any]:
        """
        Restablece la contraseña usando un token válido.
        
        Args:
            token: Token de reset
            new_password: Nueva contraseña
            
        Returns:
            Dict con 'success' (bool) y 'message' (str)
        """
        try:
            # Verificar token
            token_verification = PasswordRecoveryService.verify_token(token)
            
            if not token_verification['valid']:
                return {
                    "success": False,
                    "message": token_verification['message']
                }
            
            user_id = token_verification['user_id']
            
            # Cambiar contraseña
            if DBManager.change_password(user_id, new_password):
                # Marcar token como usado
                DBManager.mark_token_as_used(token)
                
                return {
                    "success": True,
                    "message": "Contraseña restablecida exitosamente"
                }
            else:
                return {
                    "success": False,
                    "message": "Error al cambiar la contraseña"
                }
                
        except Exception as e:
            print(f"Error al restablecer contraseña: {e}")
            return {
                "success": False,
                "message": f"Error inesperado: {str(e)}"
            }
