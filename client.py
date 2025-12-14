import sys
import socket
import threading
import json
import numpy as np
import sounddevice as sd
import queue
import noisereduce as nr
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                               QListWidget, QLabel, QDialog, QDialogButtonBox,
                               QSlider, QCheckBox, QTabWidget, QListWidgetItem,
                               QGroupBox, QComboBox, QMessageBox, QMenu, QStatusBar,
                               QSplitter, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QTextCursor, QAction, QColor, QPalette

# Темы приложения
THEMES = {
    'Светлая': {
        'bg': '#ffffff',
        'fg': '#000000',
        'chat_bg': '#f5f5f5',
        'input_bg': '#ffffff',
        'list_bg': '#fafafa',
        'list_hover': '#e3f2fd',
        'list_selected': '#2196F3',
        'accent': '#2196F3',
        'success': '#4CAF50',
        'error': '#f44336',
        'warning': '#FF9800',
        'border': '#ddd',
        'pm_bg': '#fffbf0',
    },
    'Темная': {
        'bg': '#1e1e1e',
        'fg': '#e0e0e0',
        'chat_bg': '#2d2d2d',
        'input_bg': '#3a3a3a',
        'list_bg': '#252525',
        'list_hover': '#3a3a3a',
        'list_selected': '#1976D2',
        'accent': '#2196F3',
        'success': '#66BB6A',
        'error': '#EF5350',
        'warning': '#FFA726',
        'border': '#404040',
        'pm_bg': '#2d2d2d',
    },
    'Синяя': {
        'bg': '#0d1117',
        'fg': '#c9d1d9',
        'chat_bg': '#161b22',
        'input_bg': '#21262d',
        'list_bg': '#161b22',
        'list_hover': '#30363d',
        'list_selected': '#388bfd',
        'accent': '#58a6ff',
        'success': '#3fb950',
        'error': '#f85149',
        'warning': '#d29922',
        'border': '#30363d',
        'pm_bg': '#161b22',
    },
    'Розовая': {
        'bg': '#fce4ec',
        'fg': '#000000',
        'chat_bg': '#f8bbd0',
        'input_bg': '#ffffff',
        'list_bg': '#f8bbd0',
        'list_hover': '#f06292',
        'list_selected': '#e91e63',
        'accent': '#e91e63',
        'success': '#66BB6A',
        'error': '#EF5350',
        'warning': '#FFA726',
        'border': '#f48fb1',
        'pm_bg': '#fce4ec',
    },
    'Фиолетовая': {
        'bg': '#2e1a47',
        'fg': '#e0e0e0',
        'chat_bg': '#3d2555',
        'input_bg': '#4a2c5e',
        'list_bg': '#3d2555',
        'list_hover': '#5e3775',
        'list_selected': '#7e57c2',
        'accent': '#9c27b0',
        'success': '#66BB6A',
        'error': '#EF5350',
        'warning': '#FFA726',
        'border': '#5e3775',
        'pm_bg': '#3d2555',
    },
    'Зеленая': {
        'bg': '#1b2e1f',
        'fg': '#e0e0e0',
        'chat_bg': '#243328',
        'input_bg': '#2d3f32',
        'list_bg': '#243328',
        'list_hover': '#365440',
        'list_selected': '#4caf50',
        'accent': '#4caf50',
        'success': '#66BB6A',
        'error': '#EF5350',
        'warning': '#FFA726',
        'border': '#365440',
        'pm_bg': '#243328',
    },
    'Оранжевая': {
        'bg': '#2b1d0e',
        'fg': '#e0e0e0',
        'chat_bg': '#3d2a1a',
        'input_bg': '#4a3321',
        'list_bg': '#3d2a1a',
        'list_hover': '#5e4430',
        'list_selected': '#ff6f00',
        'accent': '#ff9800',
        'success': '#66BB6A',
        'error': '#EF5350',
        'warning': '#FFA726',
        'border': '#5e4430',
        'pm_bg': '#3d2a1a',
    },
}

class Communicator(QObject):
    """Сигналы для обновления UI из потоков"""
    message_received = Signal(dict)
    connected = Signal()
    disconnected = Signal()
    friend_request = Signal(str)
    connection_error = Signal(str)

class SettingsDialog(QDialog):
    """Диалог настроек"""
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle('⚙️ Настройки')
        self.setFixedSize(550, 500)
        
        self.settings = current_settings or {
            'noise_reduction': True,
            'noise_reduction_strength': 0.2,
            'voice_gate_enabled': True,
            'voice_gate_threshold': 0.01,
            'input_gain': 1.0,
            'output_volume': 1.0,
            'theme': 'Светлая'
        }
        
        layout = QVBoxLayout()
        
        # Вкладки
        tabs = QTabWidget()
        
        # === Аудио настройки ===
        audio_tab = QWidget()
        audio_layout = QVBoxLayout()
        
        # Шумоподавление
        noise_group = QGroupBox('🎚️ Шумоподавление')
        noise_layout = QVBoxLayout()
        
        self.noise_enabled = QCheckBox('Включить шумоподавление (рекомендуется)')
        self.noise_enabled.setChecked(self.settings['noise_reduction'])
        noise_layout.addWidget(self.noise_enabled)
        
        noise_strength_layout = QHBoxLayout()
        noise_strength_layout.addWidget(QLabel('Сила:'))
        self.noise_strength_slider = QSlider(Qt.Horizontal)
        self.noise_strength_slider.setRange(0, 100)
        self.noise_strength_slider.setValue(int(self.settings['noise_reduction_strength'] * 100))
        self.noise_strength_label = QLabel(f"{int(self.settings['noise_reduction_strength'] * 100)}%")
        self.noise_strength_slider.valueChanged.connect(
            lambda v: self.noise_strength_label.setText(f"{v}%")
        )
        noise_strength_layout.addWidget(self.noise_strength_slider)
        noise_strength_layout.addWidget(self.noise_strength_label)
        noise_layout.addLayout(noise_strength_layout)
        
        noise_hint = QLabel('💡 Уменьшает фоновый шум и шипение')
        noise_hint.setStyleSheet('color: gray; font-size: 9px;')
        noise_layout.addWidget(noise_hint)
        
        noise_group.setLayout(noise_layout)
        audio_layout.addWidget(noise_group)
        
        # Voice Gate
        gate_group = QGroupBox('🚪 Шумовые ворота')
        gate_layout = QVBoxLayout()
        
        self.gate_enabled = QCheckBox('Включить (передавать только при превышении порога)')
        self.gate_enabled.setChecked(self.settings['voice_gate_enabled'])
        gate_layout.addWidget(self.gate_enabled)
        
        gate_threshold_layout = QHBoxLayout()
        gate_threshold_layout.addWidget(QLabel('Порог активации:'))
        self.gate_threshold_slider = QSlider(Qt.Horizontal)
        self.gate_threshold_slider.setRange(1, 50)
        self.gate_threshold_slider.setValue(int(self.settings['voice_gate_threshold'] * 1000))
        self.gate_threshold_label = QLabel(f"{int(self.settings['voice_gate_threshold'] * 1000)}")
        self.gate_threshold_slider.valueChanged.connect(
            lambda v: self.gate_threshold_label.setText(f"{v}")
        )
        gate_threshold_layout.addWidget(self.gate_threshold_slider)
        gate_threshold_layout.addWidget(self.gate_threshold_label)
        gate_layout.addLayout(gate_threshold_layout)
        
        gate_hint = QLabel('💡 Увеличьте если передается фоновый шум, уменьшите если голос обрывается')
        gate_hint.setStyleSheet('color: gray; font-size: 9px;')
        gate_hint.setWordWrap(True)
        gate_layout.addWidget(gate_hint)
        
        gate_group.setLayout(gate_layout)
        audio_layout.addWidget(gate_group)
        
        # Громкость
        volume_group = QGroupBox('🔊 Громкость')
        volume_layout = QVBoxLayout()
        
        input_gain_layout = QHBoxLayout()
        input_gain_layout.addWidget(QLabel('Микрофон:'))
        self.input_gain_slider = QSlider(Qt.Horizontal)
        self.input_gain_slider.setRange(10, 300)
        self.input_gain_slider.setValue(int(self.settings['input_gain'] * 100))
        self.input_gain_label = QLabel(f"{int(self.settings['input_gain'] * 100)}%")
        self.input_gain_slider.valueChanged.connect(
            lambda v: self.input_gain_label.setText(f"{v}%")
        )
        input_gain_layout.addWidget(self.input_gain_slider)
        input_gain_layout.addWidget(self.input_gain_label)
        volume_layout.addLayout(input_gain_layout)
        
        output_volume_layout = QHBoxLayout()
        output_volume_layout.addWidget(QLabel('Динамики:'))
        self.output_volume_slider = QSlider(Qt.Horizontal)
        self.output_volume_slider.setRange(10, 200)
        self.output_volume_slider.setValue(int(self.settings['output_volume'] * 100))
        self.output_volume_label = QLabel(f"{int(self.settings['output_volume'] * 100)}%")
        self.output_volume_slider.valueChanged.connect(
            lambda v: self.output_volume_label.setText(f"{v}%")
        )
        output_volume_layout.addWidget(self.output_volume_slider)
        output_volume_layout.addWidget(self.output_volume_label)
        volume_layout.addLayout(output_volume_layout)
        
        volume_group.setLayout(volume_layout)
        audio_layout.addWidget(volume_group)
        
        audio_layout.addStretch()
        audio_tab.setLayout(audio_layout)
        tabs.addTab(audio_tab, '🎤 Аудио')
        
        # === Внешний вид ===
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout()
        
        theme_group = QGroupBox('🎨 Тема оформления')
        theme_layout = QVBoxLayout()
        
        theme_select_layout = QHBoxLayout()
        theme_select_layout.addWidget(QLabel('Выберите тему:'))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.settings['theme'])
        theme_select_layout.addWidget(self.theme_combo)
        theme_layout.addLayout(theme_select_layout)
        
        theme_hint = QLabel('💡 Тема будет применена после нажатия "OK"')
        theme_hint.setStyleSheet('color: gray; font-size: 9px;')
        theme_layout.addWidget(theme_hint)
        
        theme_group.setLayout(theme_layout)
        appearance_layout.addWidget(theme_group)
        
        # Информация
        info_group = QGroupBox('ℹ️ О программе')
        info_layout = QVBoxLayout()
        
        info_text = QLabel(
            '<b>PyMessenger Pro</b><br>'
            'Версия: 2.0.0<br>'
            'Функции:<br>'
            '• Регистрация и авторизация<br>'
            '• Текстовый чат с историей<br>'
            '• Голосовая связь с шумоподавлением<br>'
            '• Личные сообщения<br>'
            '• Система друзей<br>'
            '• 7 тем оформления<br>'
            '• База данных SQLite'
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        appearance_layout.addWidget(info_group)
        
        appearance_layout.addStretch()
        appearance_tab.setLayout(appearance_layout)
        tabs.addTab(appearance_tab, '🎨 Внешний вид')
        
        layout.addWidget(tabs)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_settings(self):
        """Получить настройки"""
        return {
            'noise_reduction': self.noise_enabled.isChecked(),
            'noise_reduction_strength': self.noise_strength_slider.value() / 100.0,
            'voice_gate_enabled': self.gate_enabled.isChecked(),
            'voice_gate_threshold': self.gate_threshold_slider.value() / 1000.0,
            'input_gain': self.input_gain_slider.value() / 100.0,
            'output_volume': self.output_volume_slider.value() / 100.0,
            'theme': self.theme_combo.currentText()
        }

class LoginDialog(QDialog):
    """Диалог входа/регистрации с темой"""
    def __init__(self, parent=None, theme_name='Светлая'):
        super().__init__(parent)
        self.setWindowTitle('🔐 PyMessenger Pro')
        self.setFixedSize(450, 600)
        self.current_theme = theme_name
        self.is_login = True
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок с иконкой
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        self.icon_label = QLabel('💬')
        self.icon_label.setFont(QFont('Arial', 52))
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        self.title = QLabel('PyMessenger Pro')
        self.title.setFont(QFont('Arial', 22, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        
        self.subtitle = QLabel('Войдите в аккаунт или зарегистрируйтесь')
        self.subtitle.setFont(QFont('Arial', 10))
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet('color: gray; margin-bottom: 15px;')
        
        title_layout.addWidget(self.icon_label)
        title_layout.addWidget(self.title)
        title_layout.addWidget(self.subtitle)
        
        layout.addLayout(title_layout)
        
        # Выбор режима (Вход / Регистрация)
        mode_group = QGroupBox('Выберите действие')
        mode_layout = QHBoxLayout()
        
        self.login_radio = QRadioButton('Вход')
        self.register_radio = QRadioButton('Регистрация')
        self.login_radio.setChecked(True)
        
        self.login_radio.toggled.connect(self.toggle_mode)
        
        mode_layout.addWidget(self.login_radio)
        mode_layout.addWidget(self.register_radio)
        mode_group.setLayout(mode_layout)
        
        layout.addWidget(mode_group)
        
        # Поля ввода
        username_layout = QVBoxLayout()
        username_layout.setSpacing(6)
        username_label = QLabel('👤 Имя пользователя')
        username_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Введите имя пользователя')
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        password_layout = QVBoxLayout()
        password_layout.setSpacing(6)
        password_label = QLabel('🔒 Пароль')
        password_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        host_layout = QVBoxLayout()
        host_layout.setSpacing(6)
        host_label = QLabel('🌐 Адрес сервера')
        host_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.host_input = QLineEdit('127.0.0.1')
        self.host_input.setPlaceholderText('IP адрес сервера')
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_input)
        layout.addLayout(host_layout)
        
        port_layout = QVBoxLayout()
        port_layout.setSpacing(6)
        port_label = QLabel('🔌 Порт')
        port_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.port_input = QLineEdit('5555')
        self.port_input.setPlaceholderText('Порт сервера')
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Выбор темы
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(6)
        theme_label = QLabel('🎨 Тема оформления')
        theme_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(theme_name)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton('❌ Отмена')
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setFixedHeight(48)
        
        self.action_button = QPushButton('✅ Войти')
        self.action_button.clicked.connect(self.validate_and_accept)
        self.action_button.setFixedHeight(48)
        self.action_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.action_button)
        
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Применяем начальную тему
        self.apply_dialog_theme(theme_name)
        
        # Фокус на поле имени
        self.username_input.setFocus()
    
    def toggle_mode(self):
        """Переключение режима Вход/Регистрация"""
        self.is_login = self.login_radio.isChecked()
        if self.is_login:
            self.action_button.setText('✅ Войти')
            self.subtitle.setText('Войдите в аккаунт или зарегистрируйтесь')
        else:
            self.action_button.setText('✅ Зарегистрироваться')
            self.subtitle.setText('Создайте новый аккаунт')
    
    def validate_and_accept(self):
        """Валидация перед принятием"""
        if not self.username_input.text().strip():
            QMessageBox.warning(self, '⚠️ Ошибка', 'Пожалуйста, введите имя пользователя!')
            self.username_input.setFocus()
            return
        
        if not self.password_input.text().strip():
            QMessageBox.warning(self, '⚠️ Ошибка', 'Пожалуйста, введите пароль!')
            self.password_input.setFocus()
            return
        
        if len(self.password_input.text()) < 4:
            QMessageBox.warning(self, '⚠️ Ошибка', 'Пароль должен быть не менее 4 символов!')
            self.password_input.setFocus()
            return
        
        if not self.host_input.text().strip():
            QMessageBox.warning(self, '⚠️ Ошибка', 'Пожалуйста, введите адрес сервера!')
            self.host_input.setFocus()
            return
        
        try:
            port = int(self.port_input.text().strip())
            if port < 1 or port > 65535:
                raise ValueError()
        except:
            QMessageBox.warning(self, '⚠️ Ошибка', 'Порт должен быть числом от 1 до 65535!')
            self.port_input.setFocus()
            return
        
        self.accept()
    
    def change_theme(self, theme_name):
        """Изменить тему диалога"""
        self.current_theme = theme_name
        self.apply_dialog_theme(theme_name)
    
    def apply_dialog_theme(self, theme_name):
        """Применить тему к диалогу"""
        theme = THEMES.get(theme_name, THEMES['Светлая'])
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            QLabel {{
                color: {theme['fg']};
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['fg']};
                border: 2px solid {theme['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {theme['accent']};
            }}
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['list_selected']};
            }}
            QPushButton:pressed {{
                background-color: {theme['border']};
            }}
            QComboBox {{
                background-color: {theme['input_bg']};
                color: {theme['fg']};
                border: 2px solid {theme['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }}
            QComboBox:focus {{
                border: 2px solid {theme['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme['input_bg']};
                color: {theme['fg']};
                selection-background-color: {theme['accent']};
                selection-color: white;
                border: 1px solid {theme['border']};
                padding: 5px;
            }}
            QRadioButton {{
                color: {theme['fg']};
                font-size: 12px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
            }}
            QGroupBox {{
                border: 2px solid {theme['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: {theme['fg']};
                font-weight: bold;
            }}
            QGroupBox::title {{
                color: {theme['accent']};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        # Обновляем цвет заголовка
        self.title.setStyleSheet(f'color: {theme["accent"]}; margin: 0;')
    
    def get_credentials(self):
        """Получить данные для входа"""
        return (
            self.username_input.text().strip(),
            self.password_input.text().strip(),
            self.host_input.text().strip(),
            int(self.port_input.text().strip()),
            self.current_theme,
            self.is_login
        )

class VoiceChat:
    """Голосовой чат с обработкой аудио"""
    def __init__(self, host, port, username, settings):
        self.host = host
        self.port = port
        self.username = username
        self.voice_socket = None
        self.is_active = False
        self.settings = settings
        
        # Параметры аудио
        self.sample_rate = 16000
        self.channels = 1
        self.blocksize = 512
        
        # Очереди
        self.audio_send_queue = queue.Queue(maxsize=10)
        self.audio_play_queue = queue.Queue(maxsize=20)
        
    def start(self):
        """Запуск голосового чата"""
        try:
            self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.voice_socket.connect((self.host, self.port))
            
            join_message = json.dumps({
                'type': 'voice_join',
                'username': self.username
            })
            self.voice_socket.send(join_message.encode('utf-8'))
            
            self.is_active = True
            
            threading.Thread(target=self.send_audio_worker, daemon=True).start()
            threading.Thread(target=self.receive_audio, daemon=True).start()
            
            self.input_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                callback=self.input_callback,
                blocksize=self.blocksize
            )
            
            self.output_stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                callback=self.output_callback,
                blocksize=self.blocksize
            )
            
            self.input_stream.start()
            self.output_stream.start()
            
            print('[ГОЛОС] Подключено')
            return True
        except Exception as e:
            print(f'[ОШИБКА ГОЛОСА] {e}')
            return False
    
    def apply_gain(self, audio, gain):
        """Применить усиление"""
        return np.clip(audio * gain, -1.0, 1.0)
    
    def apply_noise_reduction(self, audio):
        """Применить шумоподавление"""
        if not self.settings['noise_reduction']:
            return audio
        
        try:
            reduced = nr.reduce_noise(
                y=audio,
                sr=self.sample_rate,
                prop_decrease=self.settings['noise_reduction_strength'],
                stationary=True
            )
            return reduced
        except:
            return audio
    
    def is_above_threshold(self, audio_data):
        """Проверка превышения порога"""
        if not self.settings['voice_gate_enabled']:
            return True
        
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > self.settings['voice_gate_threshold']
    
    def input_callback(self, indata, frames, time, status):
        """Callback для захвата аудио"""
        if status:
            print(f'[АУДИО ВХОД] {status}')
        
        try:
            audio_1d = indata.flatten()
            
            # Применяем усиление
            audio_1d = self.apply_gain(audio_1d, self.settings['input_gain'])
            
            # Применяем шумоподавление
            audio_1d = self.apply_noise_reduction(audio_1d)
            
            # Проверяем порог
            if self.is_above_threshold(audio_1d):
                self.audio_send_queue.put_nowait(audio_1d.copy())
        except queue.Full:
            pass
        except Exception as e:
            pass
    
    def output_callback(self, outdata, frames, time, status):
        """Callback для воспроизведения"""
        if status:
            print(f'[АУДИО ВЫХОД] {status}')
        
        try:
            data = self.audio_play_queue.get_nowait()
            
            # Применяем громкость
            data = self.apply_gain(data, self.settings['output_volume'])
            
            if len(data) < frames:
                padded = np.zeros(frames, dtype='float32')
                padded[:len(data)] = data
                outdata[:] = padded.reshape(-1, 1)
            else:
                outdata[:] = data[:frames].reshape(-1, 1)
                
        except queue.Empty:
            outdata.fill(0)
    
    def send_audio_worker(self):
        """Отправка аудио"""
        while self.is_active:
            try:
                audio_data = self.audio_send_queue.get(timeout=0.1)
                audio_bytes = audio_data.tobytes()
                length = len(audio_bytes).to_bytes(4, 'big')
                self.voice_socket.sendall(length + audio_bytes)
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_active:
                    print(f'[ОШИБКА ОТПРАВКИ] {e}')
                break
    
    def receive_audio(self):
        """Получение аудио"""
        while self.is_active:
            try:
                length_bytes = self.recv_exact(4)
                if not length_bytes:
                    break
                    
                length = int.from_bytes(length_bytes, 'big')
                audio_data = self.recv_exact(length)
                if not audio_data:
                    break
                
                audio_array = np.frombuffer(audio_data, dtype='float32')
                
                try:
                    self.audio_play_queue.put_nowait(audio_array)
                except queue.Full:
                    try:
                        self.audio_play_queue.get_nowait()
                        self.audio_play_queue.put_nowait(audio_array)
                    except:
                        pass
                
            except Exception as e:
                if self.is_active:
                    print(f'[ОШИБКА ПОЛУЧЕНИЯ] {e}')
                break
    
    def recv_exact(self, num_bytes):
        """Получить точное количество байт"""
        data = b''
        while len(data) < num_bytes:
            try:
                packet = self.voice_socket.recv(num_bytes - len(data))
                if not packet:
                    return None
                data += packet
            except:
                return None
        return data
    
    def update_settings(self, settings):
        """Обновить настройки на лету"""
        self.settings = settings
    
    def stop(self):
        """Остановка"""
        self.is_active = False
        
        if hasattr(self, 'input_stream') and self.input_stream:
            try:
                self.input_stream.stop()
                self.input_stream.close()
            except:
                pass
            
        if hasattr(self, 'output_stream') and self.output_stream:
            try:
                self.output_stream.stop()
                self.output_stream.close()
            except:
                pass
            
        if self.voice_socket:
            try:
                self.voice_socket.shutdown(socket.SHUT_RDWR)
                self.voice_socket.close()
            except:
                pass
                
        while not self.audio_send_queue.empty():
            try:
                self.audio_send_queue.get_nowait()
            except:
                pass
                
        while not self.audio_play_queue.empty():
            try:
                self.audio_play_queue.get_nowait()
            except:
                pass
                
        print('[ГОЛОС] Отключено')

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('💬 PyMessenger Pro')
        self.setGeometry(100, 100, 1100, 700)
        
        self.socket = None
        self.username = None
        self.voice_chat = None
        self.friends = []
        self.private_chats = {}
        self.is_connected = False
        
        self.settings = {
            'noise_reduction': True,
            'noise_reduction_strength': 0.5,
            'voice_gate_enabled': True,
            'voice_gate_threshold': 0.02,
            'input_gain': 1.0,
            'output_volume': 1.0,
            'theme': 'Светлая'
        }
        
        self.communicator = Communicator()
        self.communicator.message_received.connect(self.handle_message)
        self.communicator.friend_request.connect(self.handle_friend_request)
        self.communicator.connection_error.connect(self.handle_connection_error)
        
        self.init_ui()
        self.show_login_dialog()
    
    def apply_theme(self, theme_name):
        """Применить тему"""
        if theme_name not in THEMES:
            theme_name = 'Светлая'
        
        theme = THEMES[theme_name]
        
        # Основной стиль приложения
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            QWidget {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            QTextEdit {{
                background-color: {theme['chat_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['fg']};
                border: 2px solid {theme['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {theme['accent']};
            }}
            QListWidget {{
                background-color: {theme['list_bg']};
                color: {theme['fg']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 5px;
                margin: 2px;
                color: {theme['fg']};
            }}
            QListWidget::item:hover {{
                background-color: {theme['list_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {theme['list_selected']};
                color: white;
            }}
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['list_selected']};
            }}
            QPushButton:pressed {{
                background-color: {theme['border']};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['border']};
                background-color: {theme['bg']};
                border-radius: 5px;
            }}
            QTabBar::tab {{
                background-color: {theme['list_bg']};
                color: {theme['fg']};
                padding: 10px 20px;
                border: 1px solid {theme['border']};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['accent']};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {theme['list_hover']};
            }}
            QLabel {{
                color: {theme['fg']};
            }}
            QGroupBox {{
                border: 2px solid {theme['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: {theme['fg']};
                font-weight: bold;
            }}
            QGroupBox::title {{
                color: {theme['accent']};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QStatusBar {{
                background-color: {theme['list_bg']};
                color: {theme['fg']};
                border-top: 1px solid {theme['border']};
            }}
            QDialog {{
                background-color: {theme['bg']};
                color: {theme['fg']};
            }}
            QScrollBar:vertical {{
                background-color: {theme['bg']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # === Левая панель - чат ===
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(10)
        
        # Вкладки чатов
        self.chat_tabs = QTabWidget()
        self.chat_tabs.setTabsClosable(True)
        self.chat_tabs.tabCloseRequested.connect(self.close_chat_tab)
        
        # Основной чат
        main_chat_widget = QWidget()
        main_chat_layout = QVBoxLayout()
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Arial', 10))
        
        main_chat_layout.addWidget(self.chat_display)
        main_chat_widget.setLayout(main_chat_layout)
        
        self.chat_tabs.addTab(main_chat_widget, '💬 Общий чат')
        
        chat_layout.addWidget(self.chat_tabs)
        
        # Кнопки управления
        voice_layout = QHBoxLayout()
        voice_layout.setSpacing(10)
        
        self.voice_button = QPushButton('🎤 Включить голос')
        self.voice_button.clicked.connect(self.toggle_voice)
        self.voice_button.setFixedHeight(45)
        
        self.settings_button = QPushButton('⚙️ Настройки')
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setFixedHeight(45)
        self.settings_button.setFixedWidth(130)
        
        voice_layout.addWidget(self.voice_button)
        voice_layout.addWidget(self.settings_button)
        chat_layout.addLayout(voice_layout)
        
        # Панель ввода
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText('Введите сообщение...')
        self.message_input.setFont(QFont('Arial', 11))
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setFixedHeight(45)
        
        self.send_button = QPushButton('📤 Отправить')
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(120)
        self.send_button.setFixedHeight(45)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        
        # === Правая панель - пользователи и друзья ===
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        # Вкладки
        user_tabs = QTabWidget()
        
        # Вкладка онлайн пользователей
        online_widget = QWidget()
        online_layout = QVBoxLayout()
        
        online_label = QLabel('👥 Онлайн пользователи')
        online_label.setAlignment(Qt.AlignCenter)
        online_label.setFont(QFont('Arial', 12, QFont.Bold))
        
        self.users_list = QListWidget()
        self.users_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.users_list.customContextMenuRequested.connect(self.show_user_context_menu)
        
        online_layout.addWidget(online_label)
        online_layout.addWidget(self.users_list)
        online_widget.setLayout(online_layout)
        
        # Вкладка друзей
        friends_widget = QWidget()
        friends_layout = QVBoxLayout()
        
        friends_label = QLabel('⭐ Друзья')
        friends_label.setAlignment(Qt.AlignCenter)
        friends_label.setFont(QFont('Arial', 12, QFont.Bold))
        
        self.friends_list = QListWidget()
        self.friends_list.itemDoubleClicked.connect(self.open_private_chat)
        
        friends_layout.addWidget(friends_label)
        friends_layout.addWidget(self.friends_list)
        friends_widget.setLayout(friends_layout)
        
        user_tabs.addTab(online_widget, '👥 Онлайн')
        user_tabs.addTab(friends_widget, '⭐ Друзья')
        
        right_layout.addWidget(user_tabs)
        right_panel.setLayout(right_layout)
        right_panel.setMaximumWidth(270)
        right_panel.setMinimumWidth(250)
        
        # Сборка
        main_layout.addLayout(chat_layout, 3)
        main_layout.addWidget(right_panel, 1)
        
        central_widget.setLayout(main_layout)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('⚠️ Не подключено')
    
    def close_chat_tab(self, index):
        """Закрытие вкладки чата"""
        if index > 0:  # Не закрываем основной чат
            tab_name = self.chat_tabs.tabText(index)
            username = tab_name.replace('🔒 ', '')
            if username in self.private_chats:
                del self.private_chats[username]
            self.chat_tabs.removeTab(index)
    
    def show_user_context_menu(self, position):
        """Контекстное меню для пользователей"""
        item = self.users_list.itemAt(position)
        if item:
            username = item.text().replace('👤 ', '')
            if username != self.username:
                menu = QMenu()
                menu.setStyleSheet("""
                    QMenu {
                        padding: 5px;
                    }
                    QMenu::item {
                        padding: 8px 20px;
                    }
                """)
                
                add_friend_action = menu.addAction('➕ Добавить в друзья')
                pm_action = menu.addAction('💬 Личное сообщение')
                
                action = menu.exec(self.users_list.mapToGlobal(position))
                
                if action == add_friend_action:
                    self.send_friend_request(username)
                elif action == pm_action:
                    self.open_private_chat_by_username(username)
    
    def send_json(self, data):
        """Вспомогательный метод для отправки JSON с разделителем"""
        try:
            message = json.dumps(data) + '\n###END###\n'
            self.socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f'Ошибка отправки: {e}')
            self.communicator.connection_error.emit(str(e))
    
    def send_friend_request(self, username):
        """Отправить запрос в друзья"""
        try:
            self.send_json({
                'type': 'friend_request',
                'to': username
            })
            self.add_system_message(f'Запрос в друзья отправлен: {username}')
        except Exception as e:
            self.add_system_message(f'Ошибка: {e}')
    
    def handle_friend_request(self, from_user):
        """Обработка запроса в друзья"""
        reply = QMessageBox.question(
            self,
            '👋 Запрос в друзья',
            f'<b>{from_user}</b> хочет добавить вас в друзья.<br><br>Принять запрос?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        try:
            self.send_json({
                'type': 'friend_response',
                'to': from_user,
                'accepted': reply == QMessageBox.Yes
            })
        except Exception as e:
            print(f'Ошибка: {e}')
    
    def open_private_chat_by_username(self, username):
        """Открыть ЛС по имени пользователя"""
        # Проверяем, есть ли уже вкладка
        for i in range(self.chat_tabs.count()):
            if self.chat_tabs.tabText(i) == f'🔒 {username}':
                self.chat_tabs.setCurrentIndex(i)
                return
        
        # Создаем новую вкладку
        pm_widget = QWidget()
        pm_layout = QVBoxLayout()
        
        pm_display = QTextEdit()
        pm_display.setReadOnly(True)
        pm_display.setFont(QFont('Arial', 10))
        
        pm_layout.addWidget(pm_display)
        pm_widget.setLayout(pm_layout)
        
        self.private_chats[username] = pm_display
        
        index = self.chat_tabs.addTab(pm_widget, f'🔒 {username}')
        self.chat_tabs.setCurrentIndex(index)
    
    def open_private_chat(self, item):
        """Открыть ЛС через двойной клик"""
        username = item.text().replace('👤 ', '')
        self.open_private_chat_by_username(username)
    
    def show_settings(self):
        """Показать настройки"""
        old_theme = self.settings['theme']
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec():
            self.settings = dialog.get_settings()
            
            # Применяем тему если изменилась
            if old_theme != self.settings['theme']:
                self.apply_theme(self.settings['theme'])
            
            if self.voice_chat and self.voice_chat.is_active:
                self.voice_chat.update_settings(self.settings)
            self.add_system_message('✅ Настройки обновлены')
    
    def show_login_dialog(self):
        """Диалог входа"""
        dialog = LoginDialog(self, self.settings['theme'])
        if dialog.exec():
            username, password, host, port, theme, is_login = dialog.get_credentials()
            self.username = username
            self.host = host
            self.port = port
            self.settings['theme'] = theme
            self.setWindowTitle(f'💬 PyMessenger Pro - {username}')
            self.apply_theme(theme)
            self.connect_to_server(host, port, username, password, is_login)
        else:
            self.close()
    
    def connect_to_server(self, host, port, username, password, is_login):
        """Подключение к серверу"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((host, port))
            self.socket.settimeout(None)
            
            # Отправляем login или register
            if is_login:
                self.send_json({
                    'type': 'login',
                    'username': username,
                    'password': password
                })
            else:
                self.send_json({
                    'type': 'register',
                    'username': username,
                    'password': password
                })
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            self.is_connected = True
            self.status_bar.showMessage(f'✅ Подключено к {host}:{port}')
            self.add_system_message(f'✅ Успешно подключено к серверу {host}:{port}')
        except Exception as e:
            self.is_connected = False
            self.status_bar.showMessage(f'❌ Ошибка подключения: {e}')
            self.add_system_message(f'❌ Ошибка подключения: {e}')
            QMessageBox.critical(
                self, 
                '❌ Ошибка подключения', 
                f'Не удалось подключиться к серверу:\n\n{e}\n\nПроверьте:\n• Запущен ли сервер\n• Правильность IP адреса\n• Правильность порта\n• Правильность логина/пароля'
            )
            self.close()
    
    def handle_connection_error(self, error):
        """Обработка ошибки соединения"""
        self.is_connected = False
        self.status_bar.showMessage(f'❌ Ошибка: {error}')
        self.add_system_message(f'❌ Соединение потеряно: {error}')
        
        if self.voice_chat and self.voice_chat.is_active:
            self.voice_chat.stop()
            self.voice_button.setText('🎤 Включить голос')
    
    def toggle_voice(self):
        """Переключение голоса"""
        if not self.is_connected:
            QMessageBox.warning(self, '⚠️ Ошибка', 'Сначала подключитесь к серверу!')
            return
            
        if self.voice_chat is None or not self.voice_chat.is_active:
            voice_port = self.port + 1
            self.voice_chat = VoiceChat(self.host, voice_port, self.username, self.settings)
            if self.voice_chat.start():
                self.voice_button.setText('🔇 Выключить голос')
                self.add_system_message('🎤 Голосовой чат включен')
                self.status_bar.showMessage('🎤 Голосовой чат активен')
            else:
                QMessageBox.warning(
                    self,
                    '⚠️ Ошибка голоса',
                    'Не удалось подключиться к голосовому серверу.\nПроверьте настройки аудио.'
                )
        else:
            self.voice_chat.stop()
            self.voice_button.setText('🎤 Включить голос')
            self.add_system_message('🔇 Голосовой чат выключен')
            self.status_bar.showMessage(f'✅ Подключено к {self.host}:{self.port}')
    
    def receive_messages(self):
        """Получение сообщений с разделителем"""
        buffer = b""
        separator = b'\n###END###\n'
        
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.communicator.connection_error.emit('Соединение закрыто сервером')
                    break
                
                buffer += data
                
                while separator in buffer:
                    message_data, buffer = buffer.split(separator, 1)
                    
                    try:
                        message = json.loads(message_data.decode('utf-8'))
                        self.communicator.message_received.emit(message)
                    except json.JSONDecodeError as e:
                        print(f'Ошибка JSON: {e}')
                        
            except Exception as e:
                self.communicator.connection_error.emit(str(e))
                print(f'Ошибка получения: {e}')
                break
    
    def handle_message(self, message):
        """Обработка сообщений"""
        if message['type'] == 'login_response' or message['type'] == 'register_response':
            if not message['success']:
                QMessageBox.critical(self, '❌ Ошибка', message['message'])
                self.close()
        elif message['type'] == 'message':
            self.add_message(message['username'], message['message'], message.get('timestamp', ''))
        elif message['type'] == 'private_message':
            self.handle_private_message(message)
        elif message['type'] == 'private_message_sent':
            self.handle_sent_private_message(message)
        elif message['type'] == 'system':
            self.add_system_message(message['message'])
        elif message['type'] == 'users':
            self.update_users_list(message['users'])
        elif message['type'] == 'friend_request':
            self.communicator.friend_request.emit(message['from'])
        elif message['type'] == 'friend_added':
            self.add_friend(message['friend'])
        elif message['type'] == 'friends_list':
            self.update_friends_list(message['friends'])
    
    def handle_private_message(self, message):
        """Обработка личных сообщений"""
        sender = message['from']
        
        if sender not in self.private_chats:
            self.open_private_chat_by_username(sender)
        
        pm_display = self.private_chats[sender]
        pm_display.append(
            f'<div style="margin: 8px 0; padding: 8px; background-color: rgba(33, 150, 243, 0.1); border-radius: 8px;">'
            f'<span style="color: #2196F3; font-weight: bold; font-size: 11px;">{sender}</span> '
            f'<span style="color: #999; font-size: 9px;">[{message.get("timestamp", "")}]</span><br>'
            f'<span style="font-size: 11px; margin-top: 5px;">{message["message"]}</span>'
            f'</div>'
        )
        pm_display.moveCursor(QTextCursor.End)
        
        self.add_system_message(f'💬 Новое ЛС от {sender}')
    
    def handle_sent_private_message(self, message):
        """Обработка истории отправленных ЛС"""
        recipient = message['to']
        
        if recipient not in self.private_chats:
            self.open_private_chat_by_username(recipient)
        
        pm_display = self.private_chats[recipient]
        pm_display.append(
            f'<div style="margin: 8px 0; padding: 8px; background-color: rgba(76, 175, 80, 0.1); border-radius: 8px; text-align: right;">'
            f'<span style="color: #4CAF50; font-weight: bold; font-size: 11px;">Вы</span><br>'
            f'<span style="font-size: 11px; margin-top: 5px;">{message["message"]}</span>'
            f'</div>'
        )
        pm_display.moveCursor(QTextCursor.End)
    
    def send_message(self):
        """Отправка сообщения"""
        text = self.message_input.text().strip()
        if not text:
            return
            
        if not self.socket or not self.is_connected:
            QMessageBox.warning(self, '⚠️ Ошибка', 'Нет подключения к серверу!')
            return
        
        try:
            current_tab = self.chat_tabs.tabText(self.chat_tabs.currentIndex())
            
            if current_tab.startswith('🔒'):
                to_user = current_tab.replace('🔒 ', '')
                self.send_json({
                    'type': 'private_message',
                    'to': to_user,
                    'message': text
                })
                
                if to_user in self.private_chats:
                    pm_display = self.private_chats[to_user]
                    pm_display.append(
                        f'<div style="margin: 8px 0; padding: 8px; background-color: rgba(76, 175, 80, 0.1); border-radius: 8px; text-align: right;">'
                        f'<span style="color: #4CAF50; font-weight: bold; font-size: 11px;">Вы</span><br>'
                        f'<span style="font-size: 11px; margin-top: 5px;">{text}</span>'
                        f'</div>'
                    )
                    pm_display.moveCursor(QTextCursor.End)
            else:
                self.send_json({
                    'type': 'message',
                    'message': text
                })
            
            self.message_input.clear()
        except Exception as e:
            self.add_system_message(f'❌ Ошибка отправки: {e}')
    
    def add_message(self, username, text, timestamp):
        """Добавить сообщение в общий чат"""
        color = '#2196F3' if username == self.username else '#4CAF50'
        self.chat_display.append(
            f'<div style="margin: 8px 0; padding: 8px; background-color: rgba({self.get_rgb_from_hex(color)}, 0.1); border-radius: 8px;">'
            f'<span style="color: {color}; font-weight: bold; font-size: 11px;">{username}</span> '
            f'<span style="color: #999; font-size: 9px;">[{timestamp}]</span><br>'
            f'<span style="font-size: 11px; margin-top: 5px;">{text}</span>'
            f'</div>'
        )
        self.chat_display.moveCursor(QTextCursor.End)
    
    def get_rgb_from_hex(self, hex_color):
        """Конвертация HEX в RGB строку для rgba"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'{r}, {g}, {b}'
    
    def add_system_message(self, text):
        """Системное сообщение"""
        self.chat_display.append(
            f'<div style="margin: 8px 0; padding: 8px; background-color: rgba(255, 152, 0, 0.1); border-radius: 8px; text-align: center;">'
            f'<span style="color: #FF9800; font-style: italic; font-size: 10px;">⚙️ {text}</span>'
            f'</div>'
        )
        self.chat_display.moveCursor(QTextCursor.End)
    
    def update_users_list(self, users):
        """Обновить список пользователей"""
        self.users_list.clear()
        for user in users:
            item = QListWidgetItem(f'👤 {user}')
            if user == self.username:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.users_list.addItem(item)
    
    def add_friend(self, friend):
        """Добавить друга"""
        if friend not in self.friends:
            self.friends.append(friend)
            self.friends_list.addItem(f'👤 {friend}')
            self.add_system_message(f'⭐ {friend} добавлен в друзья')
    
    def update_friends_list(self, friends):
        """Обновить список друзей"""
        self.friends = friends
        self.friends_list.clear()
        for friend in friends:
            self.friends_list.addItem(f'👤 {friend}')
    
    def closeEvent(self, event):
        """Закрытие окна"""
        if self.voice_chat:
            self.voice_chat.stop()
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
