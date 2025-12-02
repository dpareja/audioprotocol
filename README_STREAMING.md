# AudioProtocol Streaming Mode

Modo de transmisión en tiempo real con escucha continua. El receptor permanece escuchando y guarda automáticamente los archivos que detecta.

## Características

- ✓ **Escucha continua**: El receptor está siempre escuchando
- ✓ **Nombre de archivo incluido**: Se transmite el nombre junto con los datos
- ✓ **Múltiples archivos**: Puedes enviar varios archivos consecutivamente
- ✓ **Detección automática**: El receptor detecta y guarda automáticamente
- ✓ **Ultrasónico**: Usa frecuencias 17-20.4 kHz (casi silencioso)
- ✓ **Compresión**: Reduce tamaño 30-70%

## Instalación

```bash
pip3 install -r requirements.txt
```

Requiere:
- numpy
- pyaudio

### Instalar PyAudio en Linux

```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip3 install pyaudio
```

## Uso

### Receptor (Escucha Continua)

Inicia el receptor en modo escucha:

```bash
python3 audio_stream_receiver.py [directorio_salida]
```

El receptor:
- Escucha continuamente por transmisiones
- Detecta automáticamente cuando llega un archivo
- Guarda el archivo con su nombre original
- Continúa escuchando por más archivos

Ejemplo:
```bash
# Guardar en directorio actual
python3 audio_stream_receiver.py

# Guardar en carpeta específica
python3 audio_stream_receiver.py ./recibidos/
```

### Emisor (Enviar Archivo)

En otro computador (o terminal), envía archivos:

```bash
python3 audio_stream_sender.py archivo.txt
```

El emisor:
- Lee el archivo
- Lo comprime
- Transmite el nombre y los datos
- Envía todo por audio en tiempo real

## Ejemplo de Uso

**Terminal 1 (Receptor):**
```bash
$ python3 audio_stream_receiver.py ./recibidos/
🎧 Escuchando transmisiones ultrasónicas...
   Presiona Ctrl+C para detener

📥 Recibiendo: documento.txt (compresión: sí)
   Paquete 0 recibido (64 bytes)
   Paquete 1 recibido (41 bytes)
   FIN recibido (esperados 2 paquetes)
   ✓ Archivo guardado: ./recibidos/documento.txt (459 bytes)

📥 Recibiendo: imagen.jpg (compresión: sí)
   Paquete 0 recibido (64 bytes)
   ...
```

**Terminal 2 (Emisor):**
```bash
$ python3 audio_stream_sender.py documento.txt
Compresión: 459 → 105 bytes (77.1% reducción)
Enviando 'documento.txt' (105 bytes en 2 paquetes)...
✓ SYN enviado con nombre: documento.txt
✓ Paquete 1/2 enviado
✓ Paquete 2/2 enviado
✓ FIN enviado
✓ Transmisión completada

$ python3 audio_stream_sender.py imagen.jpg
...
```

## Ventajas

✓ **Sin intervención manual**: El receptor guarda automáticamente
✓ **Múltiples archivos**: Envía varios archivos sin reiniciar el receptor
✓ **Nombre preservado**: El archivo se guarda con su nombre original
✓ **Silencioso**: Usa frecuencias ultrasónicas
✓ **Rápido**: 750 bits/seg

## Casos de Uso

- **Transferencia continua**: Mantén el receptor escuchando y envía archivos cuando necesites
- **Backup automático**: El receptor guarda todo lo que detecta
- **Múltiples emisores**: Varios computadores pueden enviar al mismo receptor
- **Monitoreo**: El receptor muestra en tiempo real qué está recibiendo

## Limitaciones

⚠ **Half-duplex**: Solo un emisor a la vez
⚠ **Sin ACK automático**: No hay confirmación de recepción en tiempo real
⚠ **Requiere PyAudio**: Dependencia adicional para audio en tiempo real
⚠ **Paquetes perdidos**: Si faltan paquetes, el archivo no se guarda

## Comparación con Modo Archivo

| Característica | Modo Archivo | Modo Streaming |
|----------------|--------------|----------------|
| Escucha | Manual | Continua |
| Nombre archivo | No incluido | Incluido |
| Múltiples archivos | Reiniciar | Automático |
| Intervención | Manual | Automática |
| Dependencias | numpy | numpy + pyaudio |

## Próximas Mejoras

- [ ] ACK automático en tiempo real
- [ ] Retransmisión automática de paquetes perdidos
- [ ] Full-duplex (envío y recepción simultáneos)
- [ ] Cola de archivos pendientes
- [ ] Interfaz gráfica

## Licencia

MIT
