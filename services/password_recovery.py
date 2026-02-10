# services/password_recovery.py
# Servicio de recuperación de contraseña por email - VERSIÓN CON RESEND API

import secrets
from datetime import datetime, timedelta
from typing import Dict, Any
from database.db_manager import DBManager
from services.email_service import email_service

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
            
            # Verificar si hay un token reciente (menos de 5 minutos)
            recent_token = DBManager.get_recent_reset_token(user['id'], minutes=5)
            if recent_token:
                return {
                    "success": False,
                    "message": "Ya solicitaste un enlace recientemente. Por favor espera 5 minutos antes de solicitar uno nuevo."
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
            
            # Construir URL de reset
            reset_url = f"https://www.logipartve.com/?reset_token={token}"
            
            # Enviar email usando Resend API
            success, message = email_service.send_password_recovery_email(
                to_email=email,
                reset_link=reset_url,
                username=user['username']
            )
            
            if success:
                return {
                    "success": True,
                    "message": "Email de recuperación enviado exitosamente"
                }
            else:
                return {
                    "success": False,
                    "message": f"Error al enviar el email: {message}"
                }
                
        except Exception as e:
            print(f"Error en send_recovery_email: {e}")
            return {
                "success": False,
                "message": f"Error inesperado: {str(e)}"
            }
    
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
            expires_at = token_data['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            
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
