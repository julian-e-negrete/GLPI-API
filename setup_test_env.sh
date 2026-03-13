#!/bin/bash
set -e

echo "=== GLPI API Proxy - Setup Test Environment ==="

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 no está instalado"
    exit 1
fi

# Crear entorno virtual
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "⚠️  IMPORTANTE: Edita .env con tus credenciales reales"
fi

# Crear directorio de logs
mkdir -p logs

# Ejecutar tests
echo ""
echo "=== Ejecutando Tests ==="
pytest app/tests/test_proxy.py -v --tb=short

echo ""
echo "✅ Entorno de testing configurado correctamente"
echo ""
echo "Para activar el entorno virtual manualmente:"
echo "  source venv/bin/activate"
echo ""
echo "Para ejecutar tests:"
echo "  pytest app/tests/test_proxy.py -v"
echo ""
echo "Para iniciar el servidor:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"
