import sys
import pyaudio
import numpy as np
from audio_protocol_ultrasonic import AudioProtocolUltrasonic, PacketType
import time

class AudioStreamReceiver:
    def __init__(self):
        self.protocol = AudioProtocolUltrasonic()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.buffer = np.array([], dtype=np.float32)
        self.receiving = False
        self.filename = None
        self.compressed = False
        self.packets = {}
        self.expected_packets = None
    
    def listen_continuous(self, output_dir="."):
        """Escucha continuamente por transmisiones"""
        print("🎧 Escuchando transmisiones ultrasónicas...")
        print("   Presiona Ctrl+C para detener\n")
        
        # Abrir stream de audio
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.protocol.sample_rate,
            input=True,
            frames_per_buffer=self.protocol.samples_per_bit * 4
        )
        
        try:
            while True:
                # Leer audio
                data = self.stream.read(self.protocol.samples_per_bit * 4, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
                
                # Agregar al buffer
                self.buffer = np.append(self.buffer, audio_chunk)
                
                # Intentar decodificar si hay suficientes datos
                if len(self.buffer) >= self.protocol.samples_per_bit * 10:
                    self._process_buffer(output_dir)
                    
                    # Limpiar buffer viejo
                    if len(self.buffer) > self.protocol.samples_per_bit * 100:
                        self.buffer = self.buffer[-self.protocol.samples_per_bit * 50:]
        
        except KeyboardInterrupt:
            print("\n\n✓ Escucha detenida")
        finally:
            self.close()
    
    def _process_buffer(self, output_dir):
        """Procesa el buffer buscando paquetes"""
        # Buscar preámbulo
        preamble_pattern = [0, 7, 0, 7]
        
        # Intentar decodificar símbolos
        if len(self.buffer) < self.protocol.samples_per_bit * 20:
            return
        
        # Decodificar símbolos del buffer
        symbols = []
        for i in range(0, min(len(self.buffer), self.protocol.samples_per_bit * 50), self.protocol.samples_per_bit):
            chunk = self.buffer[i:i+self.protocol.samples_per_bit]
            if len(chunk) < self.protocol.samples_per_bit:
                break
            
            symbol = self._detect_symbol(chunk)
            symbols.append(symbol)
        
        # Buscar patrón de preámbulo
        for i in range(len(symbols) - 4):
            if symbols[i:i+4] == preamble_pattern:
                # Encontrado preámbulo, intentar decodificar paquete
                packet_start = (i + 4) * self.protocol.samples_per_bit
                packet_audio = self.buffer[packet_start:]
                
                if len(packet_audio) >= self.protocol.samples_per_bit * 10:
                    packet = self._decode_packet_from_buffer(packet_audio)
                    if packet:
                        self._handle_packet(packet, output_dir)
                        # Limpiar buffer hasta después del paquete
                        self.buffer = self.buffer[packet_start + self.protocol.samples_per_bit * 20:]
                        return
    
    def _detect_symbol(self, chunk):
        """Detecta símbolo usando Goertzel"""
        max_energy = 0
        detected_symbol = 0
        
        for symbol, target_freq in self.protocol.freqs.items():
            k = int(0.5 + (len(chunk) * target_freq) / self.protocol.sample_rate)
            omega = (2.0 * np.pi * k) / len(chunk)
            coeff = 2.0 * np.cos(omega)
            
            q0 = 0.0
            q1 = 0.0
            q2 = 0.0
            
            for sample in chunk:
                q0 = coeff * q1 - q2 + sample
                q2 = q1
                q1 = q0
            
            real = q1 - q2 * np.cos(omega)
            imag = q2 * np.sin(omega)
            energy = real * real + imag * imag
            
            if energy > max_energy:
                max_energy = energy
                detected_symbol = symbol
        
        return detected_symbol
    
    def _decode_packet_from_buffer(self, audio):
        """Decodifica paquete desde buffer de audio"""
        symbols = []
        for i in range(0, min(len(audio), self.protocol.samples_per_bit * 30), self.protocol.samples_per_bit):
            chunk = audio[i:i+self.protocol.samples_per_bit]
            if len(chunk) < self.protocol.samples_per_bit:
                break
            symbols.append(self._detect_symbol(chunk))
        
        # Convertir a bits
        bits = self.protocol.symbols_to_bits(symbols)
        
        # Convertir a bytes
        packet = bytearray()
        for i in range(0, len(bits), 8):
            if i + 8 <= len(bits):
                byte = 0
                for j in range(8):
                    byte = (byte << 1) | bits[i+j]
                packet.append(byte)
        
        return bytes(packet)
    
    def _handle_packet(self, packet, output_dir):
        """Maneja un paquete recibido"""
        ptype, seq, data, valid = self.protocol.decode_packet(packet)
        
        if not valid:
            return
        
        if ptype == PacketType.SYN:
            self.compressed = data[0] == 1 if len(data) > 0 else False
            filename_len = data[1] if len(data) > 1 else 0
            self.filename = data[2:2+filename_len].decode('utf-8', errors='ignore')
            self.packets = {}
            self.expected_packets = None
            self.receiving = True
            print(f"\n📥 Recibiendo: {self.filename} (compresión: {'sí' if self.compressed else 'no'})")
        
        elif ptype == PacketType.DATA and self.receiving:
            self.packets[seq] = data
            print(f"   Paquete {seq} recibido ({len(data)} bytes)")
        
        elif ptype == PacketType.FIN and self.receiving:
            self.expected_packets = seq
            print(f"   FIN recibido (esperados {self.expected_packets} paquetes)")
            self._save_file(output_dir)
    
    def _save_file(self, output_dir):
        """Guarda el archivo recibido"""
        if not self.filename:
            return
        
        # Verificar paquetes faltantes
        missing = []
        for i in range(self.expected_packets):
            if i not in self.packets:
                missing.append(i)
        
        if missing:
            print(f"   ⚠ Faltan {len(missing)} paquetes: {missing[:5]}{'...' if len(missing) > 5 else ''}")
            self.receiving = False
            return
        
        # Reconstruir datos
        received_data = bytearray()
        for i in sorted(self.packets.keys()):
            received_data.extend(self.packets[i])
        
        # Descomprimir si es necesario
        if self.compressed:
            try:
                received_data = self.protocol.decompress_data(bytes(received_data))
            except Exception as e:
                print(f"   ✗ Error descomprimiendo: {e}")
                self.receiving = False
                return
        
        # Guardar archivo
        import os
        output_path = os.path.join(output_dir, self.filename)
        with open(output_path, 'wb') as f:
            f.write(received_data)
        
        print(f"   ✓ Archivo guardado: {output_path} ({len(received_data)} bytes)\n")
        self.receiving = False
    
    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

if __name__ == '__main__':
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    receiver = AudioStreamReceiver()
    receiver.listen_continuous(output_dir)
