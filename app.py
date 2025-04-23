import sys
import os
import subprocess
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QSlider,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QTabWidget,
    QColorDialog,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QUrl, QDir
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import ffmpeg


class VideoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Video PyQt5 + FFmpeg")
        self.setGeometry(100, 100, 1200, 800)

        # Variables de estado
        self.current_video_path = None
        self.current_audio_path = None
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.resolution = (0, 0)
        self.temp_files = []
        self.cut_segments = []
        self.current_text_overlay = None
        self.text_overlay_position = "bottom"
        self.text_overlay_color = QColor(255, 255, 255)
        self.text_overlay_size = 24
        self.text_overlay_opacity = 1.0

        # Configurar el layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Crear las secciones de la interfaz
        self.create_video_preview_section()
        self.create_timeline_section()
        self.create_tools_section()
        self.create_export_section()

        # Desactivar controles hasta que se cargue un video
        self.toggle_controls(False)

        # Crear el reproductor multimedia
        self.setup_media_player()

        # Configurar temporizador para actualizaciones
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(50)  # 50ms
        self.update_timer.timeout.connect(self.update_ui)

    def create_video_preview_section(self):
        preview_group = QGroupBox("Vista previa")
        preview_layout = QVBoxLayout(preview_group)

        # Contenedor para la vista previa de video
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(self.video_widget)

        # Información del video
        info_layout = QHBoxLayout()
        self.video_info_label = QLabel("Ningún video cargado")
        info_layout.addWidget(self.video_info_label)
        preview_layout.addLayout(info_layout)

        # Controles de reproducción
        playback_layout = QHBoxLayout()

        self.play_button = QPushButton("Reproducir")
        self.play_button.clicked.connect(self.toggle_playback)
        playback_layout.addWidget(self.play_button)

        self.position_label = QLabel("00:00:00 / 00:00:00")
        playback_layout.addWidget(self.position_label)

        self.frame_label = QLabel("Frame: 0/0")
        playback_layout.addWidget(self.frame_label)

        preview_layout.addLayout(playback_layout)

        self.main_layout.addWidget(preview_group)

    def create_timeline_section(self):
        timeline_group = QGroupBox("Línea de tiempo")
        timeline_layout = QVBoxLayout(timeline_group)

        # Slider de navegación global
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(1000)
        self.timeline_slider.setTickInterval(100)
        self.timeline_slider.setTickPosition(QSlider.TicksBelow)
        self.timeline_slider.sliderMoved.connect(self.seek_position)
        self.timeline_slider.sliderPressed.connect(self.on_slider_pressed)
        self.timeline_slider.sliderReleased.connect(self.on_slider_released)
        timeline_layout.addWidget(self.timeline_slider)

        # Sliders para selección de inicio y fin (recorte)
        trim_layout = QHBoxLayout()
        trim_layout.addWidget(QLabel("Inicio:"))

        self.start_slider = QSlider(Qt.Horizontal)
        self.start_slider.setMinimum(0)
        self.start_slider.setMaximum(1000)
        self.start_slider.setValue(0)
        self.start_slider.sliderMoved.connect(self.update_trim_range)
        trim_layout.addWidget(self.start_slider)

        self.start_time_label = QLabel("00:00:00")
        trim_layout.addWidget(self.start_time_label)

        trim_layout.addWidget(QLabel("Fin:"))

        self.end_slider = QSlider(Qt.Horizontal)
        self.end_slider.setMinimum(0)
        self.end_slider.setMaximum(1000)
        self.end_slider.setValue(1000)
        self.end_slider.sliderMoved.connect(self.update_trim_range)
        trim_layout.addWidget(self.end_slider)

        self.end_time_label = QLabel("00:00:00")
        trim_layout.addWidget(self.end_time_label)

        timeline_layout.addLayout(trim_layout)

        # Botones para recorte y división
        cut_layout = QHBoxLayout()

        self.trim_button = QPushButton("Recortar selección")
        self.trim_button.clicked.connect(self.trim_video)
        cut_layout.addWidget(self.trim_button)

        self.split_button = QPushButton("Dividir en posición actual")
        self.split_button.clicked.connect(self.split_video)
        cut_layout.addWidget(self.split_button)

        self.remove_segment_button = QPushButton("Eliminar segmento actual")
        self.remove_segment_button.clicked.connect(self.remove_segment)
        cut_layout.addWidget(self.remove_segment_button)

        self.join_segments_button = QPushButton("Unir segmentos")
        self.join_segments_button.clicked.connect(self.join_segments)
        cut_layout.addWidget(self.join_segments_button)

        timeline_layout.addLayout(cut_layout)

        self.main_layout.addWidget(timeline_group)

    def create_tools_section(self):
        # Usar pestañas para organizar las herramientas
        tools_tabs = QTabWidget()

        # Pestaña 1: Edición de texto
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)

        # Agregar texto
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("Texto:"))
        self.text_input = QLineEdit()
        text_input_layout.addWidget(self.text_input)
        text_layout.addLayout(text_input_layout)

        # Posición del texto
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Posición:"))
        self.text_position_combo = QComboBox()
        self.text_position_combo.addItems(["Superior", "Centro", "Inferior"])
        self.text_position_combo.setCurrentIndex(2)  # Inferior por defecto
        position_layout.addWidget(self.text_position_combo)
        text_layout.addLayout(position_layout)

        # Propiedades del texto
        properties_layout = QHBoxLayout()

        properties_layout.addWidget(QLabel("Tamaño:"))
        self.text_size_spin = QSpinBox()
        self.text_size_spin.setRange(10, 72)
        self.text_size_spin.setValue(24)
        properties_layout.addWidget(self.text_size_spin)

        properties_layout.addWidget(QLabel("Opacidad:"))
        self.text_opacity_spin = QDoubleSpinBox()
        self.text_opacity_spin.setRange(0.1, 1.0)
        self.text_opacity_spin.setValue(1.0)
        self.text_opacity_spin.setSingleStep(0.1)
        properties_layout.addWidget(self.text_opacity_spin)

        self.text_color_button = QPushButton("Color del texto")
        self.text_color_button.clicked.connect(self.select_text_color)
        properties_layout.addWidget(self.text_color_button)

        text_layout.addLayout(properties_layout)

        # Botón para aplicar texto
        self.apply_text_button = QPushButton("Aplicar texto")
        self.apply_text_button.clicked.connect(self.apply_text_overlay)
        text_layout.addWidget(self.apply_text_button)

        # Pestaña 2: Audio
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)

        # Mute original audio
        self.mute_original_check = QCheckBox("Silenciar audio original")
        audio_layout.addWidget(self.mute_original_check)

        # Cargar audio nuevo
        audio_button_layout = QHBoxLayout()
        self.load_audio_button = QPushButton("Cargar audio nuevo")
        self.load_audio_button.clicked.connect(self.load_audio)
        audio_button_layout.addWidget(self.load_audio_button)

        self.audio_path_label = QLabel("Ningún audio cargado")
        audio_button_layout.addWidget(self.audio_path_label)

        audio_layout.addLayout(audio_button_layout)

        # Aplicar audio
        self.apply_audio_button = QPushButton("Aplicar cambios de audio")
        self.apply_audio_button.clicked.connect(self.apply_audio_changes)
        audio_layout.addWidget(self.apply_audio_button)

        # Pestaña 3: Herramientas técnicas
        tech_tab = QWidget()
        tech_layout = QVBoxLayout(tech_tab)

        # Cambiar resolución
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolución:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(
            ["Original", "1920x1080", "1280x720", "854x480", "640x360"]
        )
        resolution_layout.addWidget(self.resolution_combo)
        tech_layout.addLayout(resolution_layout)

        # Cambiar formato
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato de salida:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "AVI", "MKV", "MOV", "WebM"])
        format_layout.addWidget(self.format_combo)
        tech_layout.addLayout(format_layout)

        # Cambiar velocidad
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(
            ["0.25x", "0.5x", "0.75x", "1.0x (normal)", "1.25x", "1.5x", "2.0x"]
        )
        self.speed_combo.setCurrentIndex(3)  # 1.0x por defecto
        speed_layout.addWidget(self.speed_combo)
        tech_layout.addLayout(speed_layout)

        # Aplicar cambios técnicos
        self.apply_tech_button = QPushButton("Aplicar cambios técnicos")
        self.apply_tech_button.clicked.connect(self.apply_technical_changes)
        tech_layout.addWidget(self.apply_tech_button)

        # Agregar pestañas al widget
        tools_tabs.addTab(text_tab, "Texto")
        tools_tabs.addTab(audio_tab, "Audio")
        tools_tabs.addTab(tech_tab, "Herramientas técnicas")

        self.main_layout.addWidget(tools_tabs)

    def create_export_section(self):
        export_layout = QHBoxLayout()

        self.load_button = QPushButton("Cargar Video")
        self.load_button.clicked.connect(self.load_video)
        export_layout.addWidget(self.load_button)

        self.export_button = QPushButton("Exportar Video")
        self.export_button.clicked.connect(self.export_video)
        export_layout.addWidget(self.export_button)

        self.main_layout.addLayout(export_layout)

    def setup_media_player(self):
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.error.connect(self.handle_error)

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Video",
            QDir.homePath(),
            "Archivos de video (*.mp4 *.avi *.mov *.mkv *.wmv)",
        )

        if file_path:
            self.current_video_path = file_path
            self.load_media_file(file_path)
            self.analyze_video(file_path)
            self.toggle_controls(True)

            # Actualizar la interfaz
            self.video_info_label.setText(
                f"Video cargado: {os.path.basename(file_path)}"
            )

            # Reiniciar los controles de recorte
            self.start_slider.setValue(0)
            self.end_slider.setValue(1000)
            self.start_time = 0
            self.end_time = self.duration
            self.update_trim_labels()

            # Actualizar segmentos
            self.cut_segments = []
            self.cut_segments.append(
                {"path": file_path, "start": 0, "end": self.duration}
            )

    def load_media_file(self, file_path):
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.play_button.setText("Pausar")
        self.media_player.play()
        self.is_playing = True
        self.update_timer.start()

    def analyze_video(self, file_path):
        try:
            # Obtenemos la información del video usando ffmpeg
            probe = ffmpeg.probe(file_path)
            video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")

            # Extracción de metadatos
            self.fps = eval(video_info.get("r_frame_rate", "24/1"))
            if isinstance(self.fps, tuple) or isinstance(self.fps, list):
                self.fps = self.fps[0] / self.fps[1]

            self.total_frames = int(video_info.get("nb_frames", 0))
            if self.total_frames == 0:
                # Si no está disponible, calcular basado en duración y fps
                duration = float(video_info.get("duration", 0))
                self.total_frames = int(duration * self.fps)

            self.resolution = (
                int(video_info.get("width", 0)),
                int(video_info.get("height", 0)),
            )

            # Actualizar etiqueta de información
            info_str = f"Resolución: {self.resolution[0]}x{self.resolution[1]} | FPS: {self.fps:.2f} | Frames: {self.total_frames}"
            self.video_info_label.setText(f"{os.path.basename(file_path)} | {info_str}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo analizar el video: {str(e)}"
            )

    def toggle_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("Reproducir")
            self.is_playing = False
        else:
            self.media_player.play()
            self.play_button.setText("Pausar")
            self.is_playing = True

    def media_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("Pausar")
            self.is_playing = True
        else:
            self.play_button.setText("Reproducir")
            self.is_playing = False

    def position_changed(self, position):
        self.current_frame = int((position / 1000.0) * self.fps)
        self.timeline_slider.setValue(
            int(position * 1000 / self.duration) if self.duration > 0 else 0
        )

        # Actualizar etiquetas de tiempo y frame
        current_time = self.format_time(position)
        total_time = self.format_time(self.duration)
        self.position_label.setText(f"{current_time} / {total_time}")
        self.frame_label.setText(f"Frame: {self.current_frame}/{self.total_frames}")

    def duration_changed(self, duration):
        self.duration = duration
        self.timeline_slider.setRange(0, 1000)  # Usamos 1000 pasos para mayor precisión
        self.end_time = duration
        self.update_trim_labels()

    def seek_position(self, position):
        # Convertir posición relativa (0-1000) a milisegundos
        seek_pos = int(position * self.duration / 1000)
        self.media_player.setPosition(seek_pos)

    def on_slider_pressed(self):
        if self.is_playing:
            self.media_player.pause()

    def on_slider_released(self):
        if self.is_playing:
            self.media_player.play()

    def update_trim_range(self):
        # Actualizar tiempo de inicio y fin basados en los sliders
        self.start_time = int(self.start_slider.value() * self.duration / 1000)
        self.end_time = int(self.end_slider.value() * self.duration / 1000)

        # No permitir que el fin sea menor que el inicio
        if self.end_time < self.start_time:
            if self.sender() == self.start_slider:
                self.end_time = self.start_time
                self.end_slider.setValue(self.start_slider.value())
            else:
                self.start_time = self.end_time
                self.start_slider.setValue(self.end_slider.value())

        self.update_trim_labels()

    def update_trim_labels(self):
        self.start_time_label.setText(self.format_time(self.start_time))
        self.end_time_label.setText(self.format_time(self.end_time))

    def format_time(self, milliseconds):
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def handle_error(self):
        QMessageBox.critical(
            self, "Error de Media", f"Error: {self.media_player.errorString()}"
        )

    def update_ui(self):
        # Actualizar UI con información actual
        if self.media_player.state() == QMediaPlayer.PlayingState:
            # Si está reproduciendo, actualizar la posición actual
            position = self.media_player.position()
            self.position_changed(position)

    def trim_video(self):
        if not self.current_video_path:
            return

        # Crear archivo temporal para el recorte
        output_file = tempfile.mktemp(suffix=".mp4")
        self.temp_files.append(output_file)

        try:
            # Ejecutar el recorte con ffmpeg
            start_time_sec = self.start_time / 1000.0
            duration_sec = (self.end_time - self.start_time) / 1000.0

            # Crear el comando de recorte
            (
                ffmpeg.input(self.current_video_path, ss=start_time_sec)
                .output(output_file, t=duration_sec, c="copy")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Actualizar la ruta del video actual
            self.current_video_path = output_file

            # Cargar el nuevo video recortado
            self.load_media_file(output_file)

            # Actualizar los segmentos
            self.cut_segments = [
                {"path": output_file, "start": 0, "end": duration_sec * 1000}
            ]

            QMessageBox.information(self, "Éxito", "Video recortado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al recortar el video: {str(e)}")

    def split_video(self):
        if not self.current_video_path:
            return

        # Posición actual como punto de división
        split_point = self.media_player.position()

        if split_point <= 0 or split_point >= self.duration:
            QMessageBox.warning(self, "Advertencia", "Posición de división no válida.")
            return

        try:
            # Crear archivos temporales para las dos partes
            part1_file = tempfile.mktemp(suffix=".mp4")
            part2_file = tempfile.mktemp(suffix=".mp4")
            self.temp_files.extend([part1_file, part2_file])

            # Split en primera parte
            (
                ffmpeg.input(self.current_video_path)
                .output(part1_file, t=split_point / 1000, c="copy")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Split en segunda parte
            (
                ffmpeg.input(self.current_video_path, ss=split_point / 1000)
                .output(part2_file, c="copy")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Actualizar los segmentos
            self.cut_segments = [
                {"path": part1_file, "start": 0, "end": split_point},
                {"path": part2_file, "start": 0, "end": self.duration - split_point},
            ]

            # Cargar la primera parte
            self.current_video_path = part1_file
            self.load_media_file(part1_file)

            QMessageBox.information(self, "Éxito", "Video dividido en dos partes.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al dividir el video: {str(e)}")

    def remove_segment(self):
        if len(self.cut_segments) <= 1:
            QMessageBox.warning(self, "Advertencia", "No hay segmentos para eliminar.")
            return

        # Determinar qué segmento eliminar (por ahora, simplemente el actual)
        current_segment_index = 0  # Asumimos el primero

        # Eliminar el segmento actual
        self.cut_segments.pop(current_segment_index)

        # Cargar el siguiente segmento disponible
        if self.cut_segments:
            self.current_video_path = self.cut_segments[0]["path"]
            self.load_media_file(self.current_video_path)

            QMessageBox.information(self, "Éxito", "Segmento eliminado correctamente.")
        else:
            QMessageBox.warning(self, "Advertencia", "No quedan segmentos disponibles.")

    def join_segments(self):
        if len(self.cut_segments) <= 1:
            QMessageBox.warning(
                self, "Advertencia", "Se necesitan al menos dos segmentos para unir."
            )
            return

        try:
            # Crear un archivo temporal para la concatenación
            concat_file = tempfile.mktemp(suffix=".txt")
            output_file = tempfile.mktemp(suffix=".mp4")
            self.temp_files.append(output_file)

            # Crear el archivo de lista para ffmpeg
            with open(concat_file, "w") as f:
                for segment in self.cut_segments:
                    f.write(f"file '{segment['path']}'\n")

            # Concatenar los segmentos
            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_file,
                    "-c",
                    "copy",
                    output_file,
                ],
                check=True,
            )

            # Actualizar la ruta del video actual
            self.current_video_path = output_file

            # Cargar el nuevo video concatenado
            self.load_media_file(output_file)

            # Actualizar los segmentos
            self.cut_segments = [
                {"path": output_file, "start": 0, "end": self.duration}
            ]

            QMessageBox.information(self, "Éxito", "Segmentos unidos correctamente.")

            # Eliminar el archivo temporal de concatenación
            os.remove(concat_file)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al unir los segmentos: {str(e)}"
            )

    def load_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Audio",
            QDir.homePath(),
            "Archivos de audio (*.mp3 *.wav *.aac *.ogg)",
        )

        if file_path:
            self.current_audio_path = file_path
            self.audio_path_label.setText(f"Audio: {os.path.basename(file_path)}")

    def apply_audio_changes(self):
        if not self.current_video_path:
            return

        try:
            output_file = tempfile.mktemp(suffix=".mp4")
            self.temp_files.append(output_file)

            # Preparar el comando ffmpeg según las opciones
            if self.current_audio_path and self.mute_original_check.isChecked():
                # Reemplazar el audio original con el nuevo
                (
                    ffmpeg.input(self.current_video_path)
                    .output(output_file, acodec="copy", map="0:v")
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

                # Agregar el nuevo audio
                temp_file = output_file
                output_file = tempfile.mktemp(suffix=".mp4")
                self.temp_files.append(output_file)

                (
                    ffmpeg.input(temp_file)
                    .input(self.current_audio_path)
                    .output(output_file, acodec="aac", map=["0:v", "1:a"])
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif self.current_audio_path:
                # Mezclar el audio original con el nuevo
                (
                    ffmpeg.input(self.current_video_path)
                    .input(self.current_audio_path)
                    .output(output_file, map=["0:v", "0:a", "1:a"])
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            elif self.mute_original_check.isChecked():
                # Solo quitar el audio original
                (
                    ffmpeg.input(self.current_video_path)
                    .output(output_file, an=None, vcodec="copy")
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                QMessageBox.warning(
                    self, "Advertencia", "No se han seleccionado cambios de audio."
                )
                return

            # Actualizar la ruta del video actual
            self.current_video_path = output_file

            # Cargar el nuevo video con los cambios de audio
            self.load_media_file(output_file)

            QMessageBox.information(
                self, "Éxito", "Cambios de audio aplicados correctamente."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al aplicar cambios de audio: {str(e)}"
            )

    def select_text_color(self):
        color = QColorDialog.getColor(self.text_overlay_color, self)
        if color.isValid():
            self.text_overlay_color = color
            # Actualizar el botón con el color seleccionado
            style = f"background-color: {color.name()};"
            self.text_color_button.setStyleSheet(style)

    def apply_text_overlay(self):
        if not self.current_video_path:
            return

        text = self.text_input.text()
        if not text:
            QMessageBox.warning(self, "Advertencia", "Introduce un texto para agregar.")
            return

        try:
            output_file = tempfile.mktemp(suffix=".mp4")
            self.temp_files.append(output_file)

            # Obtener posición del texto
            position_index = self.text_position_combo.currentIndex()
            position_map = {
                0: "10:10",  # Superior
                1: "main_w/2-text_w/2:main_h/2-text_h/2",  # Centro
                2: "10:main_h-text_h-10",  # Inferior
            }
            position = position_map.get(position_index, "10:main_h-text_h-10")

            # Aplicar el texto con ffmpeg
            font_size = self.text_size_spin.value()
            opacity = self.text_opacity_spin.value()
            color = self.text_overlay_color.name().replace("#", "0x")

            # Crear el filtro de texto
            drawtext_filter = (
                f"drawtext=text='{text}':fontsize={font_size}:fontcolor={color}@{opacity}:"
                f"x={position.split(':')[0]}:y={position.split(':')[1]}:box=1:boxcolor=0x00000000@0.5"
            )

            # Aplicar el filtro al video
            (
                ffmpeg.input(self.current_video_path)
                .output(output_file, vf=drawtext_filter)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Actualizar la ruta del video actual
            self.current_video_path = output_file

            # Cargar el nuevo video con el texto agregado
            self.load_media_file(output_file)

            # Guardar el overlay actual para referencia
            self.current_text_overlay = {
                "text": text,
                "position": position_index,
                "font_size": font_size,
                "opacity": opacity,
                "color": self.text_overlay_color,
            }

            QMessageBox.information(self, "Éxito", "Texto agregado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al agregar texto: {str(e)}")

    def apply_technical_changes(self):
        if not self.current_video_path:
            return

        try:
            output_file = tempfile.mktemp(suffix=".mp4")
            self.temp_files.append(output_file)

            # Opciones base para ffmpeg
            stream = ffmpeg.input(self.current_video_path)

            # Verificar cambios de resolución
            resolution_text = self.resolution_combo.currentText()
            if resolution_text != "Original":
                width, height = map(int, resolution_text.split("x"))
                stream = ffmpeg.filter_(stream, "scale", width, height)

            # Verificar cambios de velocidad
            speed_text = self.speed_combo.currentText()
            if speed_text != "1.0x (normal)":
                speed = float(speed_text.replace("x", ""))

                # Para cambios de velocidad, necesitamos filtros diferentes
                if speed < 1.0:
                    # Cámara lenta
                    stream = ffmpeg.filter_(stream, "setpts", f"{1/speed}*PTS")
                    # Ajustar el audio también
                    audio_stream = ffmpeg.input(self.current_video_path).audio
                    audio_stream = ffmpeg.filter_(audio_stream, "atempo", speed)
                    # Combinar los streams
                    stream = ffmpeg.output(stream, audio_stream, output_file)
                else:
                    # Cámara rápida
                    stream = ffmpeg.filter_(stream, "setpts", f"{1/speed}*PTS")
                    # Ajustar el audio también
                    audio_stream = ffmpeg.input(self.current_video_path).audio
                    audio_stream = ffmpeg.filter_(audio_stream, "atempo", speed)
                    # Combinar los streams
                    stream = ffmpeg.output(stream, audio_stream, output_file)
            else:
                # Si no hay cambios de velocidad, solo aplicar otros cambios
                stream = ffmpeg.output(stream, output_file)

            # Ejecutar el comando
            stream.overwrite_output().run(capture_stdout=True, capture_stderr=True)

            # Actualizar la ruta del video actual
            self.current_video_path = output_file

            # Cargar el nuevo video con los cambios técnicos
            self.load_media_file(output_file)

            QMessageBox.information(
                self, "Éxito", "Cambios técnicos aplicados correctamente."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al aplicar cambios técnicos: {str(e)}"
            )

    def export_video(self):
        if not self.current_video_path:
            return

        # Seleccionar formato de salida
        output_format = self.format_combo.currentText().lower()

        # Diálogo para guardar archivo
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Video",
            QDir.homePath() + "/video_editado." + output_format,
            f"Archivos de video (*.{output_format})",
        )

        if not file_path:
            return

        try:
            # Si el formato es diferente al actual, convertir
            if not file_path.lower().endswith(output_format):
                file_path += f".{output_format}"

            # Copiar el archivo final
            (
                ffmpeg.input(self.current_video_path)
                .output(file_path)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            QMessageBox.information(
                self, "Éxito", f"Video exportado correctamente a {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar el video: {str(e)}")

    def toggle_controls(self, enabled):
        # Activar/desactivar controles de edición
        self.timeline_slider.setEnabled(enabled)
        self.start_slider.setEnabled(enabled)
        self.end_slider.setEnabled(enabled)
        self.play_button.setEnabled(enabled)
        self.trim_button.setEnabled(enabled)
        self.split_button.setEnabled(enabled)
        self.remove_segment_button.setEnabled(enabled)
        self.join_segments_button.setEnabled(enabled)
        self.apply_text_button.setEnabled(enabled)
        self.load_audio_button.setEnabled(enabled)
        self.apply_audio_button.setEnabled(enabled)
        self.apply_tech_button.setEnabled(enabled)
        self.export_button.setEnabled(enabled)

    def closeEvent(self, event):
        # Limpieza antes de cerrar
        self.media_player.stop()
        self.update_timer.stop()

        # Eliminar archivos temporales
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

        event.accept()


# Clase para manejar la extracción de frames del video para previsualización
class VideoFrameExtractor:
    def __init__(self, video_path):
        self.video_path = video_path
        self.frames_cache = {}

    def extract_frame(self, position_ms):
        # Verificar si el frame ya está en caché
        if position_ms in self.frames_cache:
            return self.frames_cache[position_ms]

        try:
            # Convertir posición a segundos
            position_sec = position_ms / 1000.0

            # Crear un archivo temporal para el frame
            frame_file = tempfile.mktemp(suffix=".jpg")

            # Extraer el frame con ffmpeg
            (
                ffmpeg.input(self.video_path, ss=position_sec)
                .output(frame_file, vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Cargar el frame como QPixmap
            pixmap = QPixmap(frame_file)

            # Almacenar en caché
            self.frames_cache[position_ms] = pixmap

            # Eliminar el archivo temporal
            os.remove(frame_file)

            return pixmap
        except Exception as e:
            print(f"Error al extraer frame: {str(e)}")
            return QPixmap()

    def clear_cache(self):
        self.frames_cache.clear()


# Función principal para iniciar la aplicación
def main():
    app = QApplication(sys.argv)
    editor = VideoEditor()
    editor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
