# AmetsAI

AmetsAI es una plataforma de inteligencia comercial para la industria farmacéutica. Convertimos las interacciones de campo del delegado y del visitador médico en insights estratégicos y tácticos.

## Arquitectura

La plataforma se compone de tres partes principales:
1.  **Backend (FastAPI):** Procesa las solicitudes, gestiona la lógica de negocio y se comunica con los modelos de IA.
2.  **Frontend (Next.js):** Una interfaz de usuario web para interactuar con la plataforma.
3.  **Modelos de IA:** Modelos de transcripción y lenguaje para el análisis de las interacciones.

## Configuración y Ejecución

### 1. Backend (FastAPI)

El backend se encuentra en el directorio `@/restful`.

**Requisitos:**
- Python 3.9+
- CUDA (para la aceleración por GPU)

**Instalación:**
1.  Navega al directorio del backend:
    ```bash
    cd restful
    ```
2.  Crea un entorno virtual e instálalo:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  Instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```

**Ejecución:**
Para iniciar el servidor FastAPI, ejecuta el siguiente comando desde el directorio `restful`:
```bash
uvicorn main:app --reload
```
El servidor estará disponible en `http://127.0.0.1:8000`.

### 2. Frontend (Next.js)

El frontend se encuentra en el directorio `@/ui`.

**Requisitos:**
- Node.js 22+
- pnpm

**Instalación:**
1.  Instala `nvm` para gestionar las versiones de Node.js:
    ```bash
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    source ~/.bashrc  # O ~/.zshrc si usas Zsh
    ```
2.  Instala y usa la versión correcta de Node.js:
    ```bash
    nvm install 22
    nvm use 22
    ```
3.  Instala `pnpm` globalmente:
    ```bash
    npm install -g pnpm
    ```
4.  Navega al directorio del frontend e instala las dependencias:
    ```bash
    cd ui
    pnpm install
    ```

**Ejecución:**
Para iniciar la aplicación de desarrollo de Next.js:
```bash
pnpm run dev
```
La aplicación estará disponible en `http://localhost:3000`.

### 3. Servidor de Modelos (vLLM)

Para ejecutar los modelos de lenguaje de forma local, se utiliza `vLLM`.

**Ejecución:**
```bash
vllm serve --config config/server_vllm_config.yaml
```
Asegúrate de que la ruta al archivo de configuración sea la correcta.
