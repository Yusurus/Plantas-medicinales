class FaceRecognitionLogin {
    constructor() {
        this.video = document.getElementById('video');
        this.cameraContainer = document.getElementById('cameraContainer');
        this.faceLoginBtn = document.getElementById('faceLoginBtn');
        this.captureBtn = document.getElementById('captureBtn');
        this.cancelBtn = document.getElementById('cancelBtn');
        this.loginForm = document.getElementById('loginForm');
        this.statusMessage = document.getElementById('statusMessage');
        this.loginSpinner = document.getElementById('loginSpinner');
        this.captureSpinner = document.getElementById('captureSpinner');
        this.stream = null;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.faceLoginBtn.addEventListener('click', () => this.startFaceRecognition());
        this.captureBtn.addEventListener('click', () => this.captureAndVerify());
        this.cancelBtn.addEventListener('click', () => this.stopCamera());
        this.loginForm.addEventListener('submit', (e) => this.handleTraditionalLogin(e));
    }

    showStatus(message, type = 'info', duration = 5000) {
        this.statusMessage.textContent = message;
        this.statusMessage.className = `status-message status-${type}`;
        this.statusMessage.style.display = 'block';
        
        if (duration > 0) {
            setTimeout(() => {
                this.statusMessage.style.display = 'none';
            }, duration);
        }
    }

    async startFaceRecognition() {
        try {
            this.faceLoginBtn.disabled = true;
            this.showStatus('Iniciando cámara...', 'info');
            
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                } 
            });
            
            this.video.srcObject = this.stream;
            this.cameraContainer.classList.add('active');
            this.showStatus('Cámara lista. Posiciona tu rostro frente a la cámara y presiona "Capturar".', 'success');
            
        } catch (error) {
            console.error('Error al acceder a la cámara:', error);
            let errorMessage = 'Error: No se pudo acceder a la cámara.';
            
            if (error.name === 'NotAllowedError') {
                errorMessage = 'Permisos de cámara denegados. Por favor, permite el acceso a la cámara.';
            } else if (error.name === 'NotFoundError') {
                errorMessage = 'No se encontró una cámara en este dispositivo.';
            } else if (error.name === 'NotReadableError') {
                errorMessage = 'La cámara está siendo usada por otra aplicación.';
            }
            
            this.showStatus(errorMessage, 'error');
            this.faceLoginBtn.disabled = false;
        }
    }

    async captureAndVerify() {
        this.captureSpinner.style.display = 'inline-block';
        this.captureBtn.disabled = true;
        this.showStatus('Capturando y verificando rostro...', 'info', 0);

        try {
            // Capturar frame del video
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            context.drawImage(this.video, 0, 0);
            
            // Convertir a base64
            const imageBase64 = canvas.toDataURL('image/jpeg', 0.8);
            
            // Enviar al servidor
            const response = await fetch('/api/verify-face', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageBase64
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showStatus(
                    `${result.message} (Confianza: ${result.confidence || 'N/A'}%)`, 
                    'success'
                );
                this.captureBtn.classList.add('success');
                this.stopCamera();
                
                // Redireccionar después de 2 segundos
                setTimeout(() => {
                    this.redirectToDashboard(result.user);
                }, 2000);
            } else {
                this.showStatus(result.message, 'error');
                this.captureBtn.classList.add('error');
                setTimeout(() => {
                    this.captureBtn.classList.remove('error');
                }, 2000);
            }
            
        } catch (error) {
            console.error('Error en la captura:', error);
            this.showStatus('Error de conexión. Verifica tu conexión a internet.', 'error');
            this.captureBtn.classList.add('error');
            setTimeout(() => {
                this.captureBtn.classList.remove('error');
            }, 2000);
        } finally {
            this.captureSpinner.style.display = 'none';
            this.captureBtn.disabled = false;
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.cameraContainer.classList.remove('active');
        this.faceLoginBtn.disabled = false;
        this.captureBtn.classList.remove('success', 'error');
    }

    async handleTraditionalLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showStatus('Por favor, completa todos los campos.', 'error');
            return;
        }
        
        this.loginSpinner.style.display = 'inline-block';
        this.loginForm.querySelector('button[type="submit"]').disabled = true;
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showStatus(result.message, 'success');
                this.loginForm.querySelector('button[type="submit"]').classList.add('success');
                
                setTimeout(() => {
                    this.redirectToDashboard(result.user);
                }, 1500);
            } else {
                this.showStatus(result.message, 'error');
                this.loginForm.querySelector('button[type="submit"]').classList.add('error');
                setTimeout(() => {
                    this.loginForm.querySelector('button[type="submit"]').classList.remove('error');
                }, 2000);
            }
            
        } catch (error) {
            console.error('Error en login:', error);
            this.showStatus('Error de conexión. Verifica tu conexión a internet.', 'error');
        } finally {
            this.loginSpinner.style.display = 'none';
            this.loginForm.querySelector('button[type="submit"]').disabled = false;
        }
    }

    redirectToDashboard(username) {
        // Crear página de éxito
        document.body.innerHTML = `
            <div style="
                background: linear-gradient(135deg,rgb(234, 172, 102) 0%,rgb(162, 127, 75) 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                text-align: center;
                padding: 20px;
            ">
                <div style="
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    padding: 60px 40px;
                    border-radius: 20px;
                    box-shadow: 0 25px 45px rgba(0, 0, 0, 0.1);
                    max-width: 500px;
                    width: 100%;
                    animation: successEntry 0.6s ease-out;
                ">
                    <div style="font-size: 4em; margin-bottom: 20px; animation: bounce 1s ease-infinite;">🎉</div>
                    <h2 style="margin-bottom: 20px; font-size: 2.5em; font-weight: 300;">¡Acceso Concedido!</h2>
                    <p style="font-size: 1.3em; margin-bottom: 10px; opacity: 0.9;">Bienvenido,</p>
                    <p style="font-size: 1.8em; margin-bottom: 30px; font-weight: 600; color: #ffd700;">${username}</p>
                    <p style="opacity: 0.8; margin-bottom: 40px; font-size: 1.1em;">Has accedido exitosamente al sistema</p>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                        <button onclick="location.reload()" style="
                            padding: 15px 30px;
                            background: rgba(255, 255, 255, 0.2);
                            border: 2px solid rgba(255, 255, 255, 0.3);
                            color: white;
                            border-radius: 12px;
                            cursor: pointer;
                            font-size: 1em;
                            font-weight: 500;
                            transition: all 0.3s ease;
                            backdrop-filter: blur(5px);
                        " onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'; this.style.transform='translateY(-2px)'" 
                           onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'; this.style.transform='translateY(0)'">
                            🔄 Volver al Login
                        </button>
                        <a href="/registrar_planta" style="
                            display: inline-block;
                            padding: 15px 30px;
                            background: linear-gradient(135deg, #11998e, #38ef7d);
                            border: none;
                            color: white;
                            border-radius: 12px;
                            cursor: pointer;
                            font-size: 1em;
                            font-weight: 500;
                            text-decoration: none;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 10px 25px rgba(17, 153, 142, 0.3)'" 
                           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none'">
                            📊 Ingresar al sistema
                        </a>
                    </div>
                </div>
                <style>
                    @keyframes successEntry {
                        from {
                            opacity: 0;
                            transform: scale(0.8) translateY(20px);
                        }
                        to {
                            opacity: 1;
                            transform: scale(1) translateY(0);
                        }
                    }
                    @keyframes bounce {
                        0%, 20%, 60%, 100% {
                            transform: translateY(0);
                        }
                        40% {
                            transform: translateY(-10px);
                        }
                        80% {
                            transform: translateY(-5px);
                        }
                    }
                </style>
            </div>
        `;
    }
}

// Inicializar la aplicación cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    new FaceRecognitionLogin();
    
    // Mostrar información de desarrollo en consola
    console.log(`
    =====================================
    🚀 SISTEMA DE RECONOCIMIENTO FACIAL
    =====================================
    
    Estado: Conectado al servidor Flask
    
    Usuarios de prueba:
    - admin / password123
    - usuario / 12345  
    - test / test
    
    Funciones disponibles:
    ✅ Login tradicional
    ✅ Reconocimiento facial con DeepFace
    ✅ Integración con backend Python
    ✅ Manejo de errores
    ✅ Interfaz responsive
    
    Para probar el reconocimiento facial:
    1. Asegúrate de tener rostros en 'rostros_conocidos/'
    2. Permite acceso a la cámara
    3. Posiciona tu rostro y captura
    `);
});