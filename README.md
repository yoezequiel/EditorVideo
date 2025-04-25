# EditorVideo

EditorVideo es una aplicación de edición de video desarrollada con PyQt5 y FFmpeg. Permite realizar tareas avanzadas de edición directamente desde una interfaz gráfica de usuario.

## Características
- **Edición de video**: Recorte, división, unión de segmentos y aplicación de texto.
- **Audio**: Silenciar audio original, agregar nuevos audios y mezclar pistas.
- **Herramientas técnicas**: Cambiar resolución, formato de salida y velocidad del video.
- **Vista previa**: Reproducción de video con controles interactivos.

## Requisitos
- Python 3.x
- PyQt5
- FFmpeg

## Instalación
1. Clona este repositorio:
   ```bash
   git clone https://github.com/yoezequiel/EditorVideo.git
   ```
2. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
3. Asegúrate de tener FFmpeg instalado y accesible desde la línea de comandos.

## Uso
Ejecuta la aplicación con el siguiente comando:
```bash
python app.py
```

## Funcionalidades principales
### Edición de video
- **Recorte**: Selecciona un rango de tiempo para recortar el video.
- **División**: Divide el video en segmentos en la posición actual.
- **Unión**: Combina múltiples segmentos en un solo archivo.

### Audio
- **Silenciar**: Elimina el audio original del video.
- **Agregar audio**: Reemplaza o mezcla el audio original con una nueva pista.

### Texto
- **Superposición de texto**: Agrega texto personalizado al video con opciones de posición, tamaño, color y opacidad.

### Exportación
- Cambia la resolución, formato y velocidad del video antes de exportarlo.

## Contribuciones
¡Las contribuciones son bienvenidas! Si deseas colaborar, por favor abre un issue o envía un pull request.

## Licencia
Este proyecto está bajo la Licencia MIT.