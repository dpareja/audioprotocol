# AudioProtocol

Protocolo de comunicación bidireccional por audio similar a TCP/IP, con paquetes, checksums, compresión y retransmisión de paquetes perdidos.

## Versiones Disponibles

### 🔊 Versión Audible (Estándar)
- Velocidad: 400 bits/seg (50 bytes/seg)
- Frecuencias: 1-2.5 kHz (audible)
- Confiabilidad: 95-99%
- Hardware: Cualquiera

### 🔇 Versión Ultrasónica (Silenciosa)
- Velocidad: 750 bits/seg (93.75 bytes/seg) - **2x más rápido**
- Frecuencias: 17-20.4 kHz (casi silencioso)
- Confiabilidad: 100% (probado)
- Hardware: Moderno (>17 kHz)
- Ver: [README_ULTRASONIC.md](README_ULTRASONIC.md)

### 📡 Modo Streaming (Escucha Continua) ⭐ NUEVO
- **Escucha permanente**: Receptor siempre activo
- **Nombre de archivo incluido**: Se guarda con nombre original
- **Múltiples archivos**: Envía varios sin reiniciar
- **Detección automática**: Sin intervención manual
- Ver: [README_STREAMING.md](README_STREAMING.md)

## Características

- ✓ Protocolo orientado a paquetes
- ✓ Handshake SYN/FIN
- ✓ Checksums para verificación de integridad
- ✓ Números de secuencia
- ✓ **Compresión zlib** (reduce tamaño 30-70%)
- ✓ **Retransmisión de paquetes perdidos** (NACK)
- ✓ Modulación FSK (4-FSK audible, 8-FSK ultrasónico)

## Uso Rápido

### Versión Audible (Estándar)

**Enviar:**
```bash
python3 audio_protocol.py archivo.txt
```

**Recibir:**
```bash
python3 audio_receiver.py tx archivo_recuperado.txt
```

### Versión Ultrasónica (Silenciosa)

**Enviar:**
```bash
python3 audio_protocol_ultrasonic.py archivo.txt
```

**Recibir:**
```bash
python3 audio_receiver_ultrasonic.py tx_ultra archivo_recuperado.txt
```

**Test de hardware:**
```bash
python3 test_ultrasonic_simple.py
```

### Modo Streaming (Escucha Continua)

**Receptor (mantener corriendo):**
```bash
python3 audio_stream_receiver.py ./recibidos/
```

**Emisor (enviar cuando quieras):**
```bash
python3 audio_stream_sender.py documento.txt
python3 audio_stream_sender.py imagen.jpg
```

El receptor detecta automáticamente los archivos y los guarda con su nombre original.

### 3. Retransmitir paquetes perdidos

En el emisor:
```bash
python3 audio_retransmit.py tx rx
```

Genera archivos `tx_retx_*.wav` con los paquetes faltantes.

### 4. Recibir paquetes retransmitidos

Renombra los archivos retransmitidos:
```bash
# Copiar paquetes retransmitidos a la secuencia original
cp tx_retx_0005.wav tx_data_0005.wav
```

Luego vuelve a ejecutar el receptor.

## Ejemplo Completo

```bash
# Emisor: Enviar archivo
python3 audio_protocol.py documento.pdf

# Receptor: Recibir (detecta paquetes faltantes)
python3 audio_receiver.py tx documento_recuperado.pdf
# Output: ⚠ Faltan 2 paquetes: [5, 12]
# Genera: rx_nack_0000.wav, rx_nack_0001.wav

# Emisor: Retransmitir paquetes perdidos
python3 audio_retransmit.py tx rx
# Genera: tx_retx_0005.wav, tx_retx_0012.wav

# Receptor: Copiar y recibir de nuevo
cp tx_retx_*.wav tx_data_*.wav  # Ajustar nombres
python3 audio_receiver.py tx documento_recuperado.pdf
# Output: ✓ Todos los paquetes recibidos correctamente
```

## Compresión

Por defecto, los archivos se comprimen con zlib nivel 9:

```bash
# Con compresión (por defecto)
python3 audio_protocol.py archivo.txt

# Sin compresión
python3 audio_protocol.py archivo.txt --no-compress
```

Reducción típica:
- Texto: 60-70%
- Código: 50-60%
- Imágenes: 10-30%
- Ya comprimidos (zip, jpg): 0-5%

## Verificación

```bash
md5sum archivo_original archivo_recuperado
```

## Requisitos

```bash
pip3 install numpy
```

## Especificaciones Técnicas

- Sample rate: 44100 Hz
- Duración de bit: 5ms
- Frecuencias: 1000, 1500, 2000, 2500 Hz
- Modulación: 4-FSK (2 bits/símbolo)
- Velocidad: 400 bits/seg (50 bytes/seg)
- Compresión: zlib nivel 9
- Tamaño de paquete: 32 bytes

## Ventajas sobre AudioTransfer

- 4x más rápido (400 vs 100 bits/seg)
- Compresión integrada (30-70% reducción)
- Detección de paquetes perdidos
- Retransmisión selectiva
- Verificación de integridad por paquete

## Licencia

MIT
