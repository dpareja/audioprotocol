import sys
import pyaudio
import numpy as np
from audio_protocol_ultrasonic import AudioProtocolUltrasonic, PacketType

class AudioStreamSender:
    def __init__(self):
        self.protocol = AudioProtocolUltrasonic()
        self.audio = pyaudio.PyAudio()
        self.stream = None
    
    def send_file_stream(self, filename):
        """Envía archivo por stream de audio en tiempo real"""
        # Leer archivo
        with open(filename, 'rb') as f:
            data = f.read()
        
        original_size = len(data)
        
        # Comprimir
        data = self.protocol.compress_data(data)
        print(f"Compresión: {original_size} → {len(data)} bytes ({100*(1-len(data)/original_size):.1f}% reducción)")
        
        # Preparar nombre de archivo (máximo 32 bytes)
        import os
        file_basename = os.path.basename(filename)[:32]
        filename_bytes = file_basename.encode('utf-8')
        
        # Dividir en paquetes
        packets = []
        for i in range(0, len(data), self.protocol.packet_size):
            chunk = data[i:i+self.protocol.packet_size]
            packets.append(chunk)
        
        print(f"Enviando '{file_basename}' ({len(data)} bytes en {len(packets)} paquetes)...")
        
        # Abrir stream de audio
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.protocol.sample_rate,
            output=True
        )
        
        # Enviar SYN con nombre de archivo
        syn_data = bytes([1]) + bytes([len(filename_bytes)]) + filename_bytes
        syn_packet = self.protocol.encode_packet(PacketType.SYN, 0, syn_data)
        self._send_packet_audio(syn_packet)
        print(f"✓ SYN enviado con nombre: {file_basename}")
        
        # Enviar paquetes de datos
        for seq, chunk in enumerate(packets):
            data_packet = self.protocol.encode_packet(PacketType.DATA, seq, chunk)
            self._send_packet_audio(data_packet)
            print(f"✓ Paquete {seq+1}/{len(packets)} enviado")
        
        # Enviar FIN
        fin_packet = self.protocol.encode_packet(PacketType.FIN, len(packets), b'')
        self._send_packet_audio(fin_packet)
        print(f"✓ FIN enviado")
        
        # Cerrar stream
        self.stream.stop_stream()
        self.stream.close()
        
        print(f"\n✓ Transmisión completada")
    
    def _send_packet_audio(self, packet):
        """Envía un paquete como audio en tiempo real"""
        # Generar preámbulo
        audio = list(self.protocol.generate_preamble())
        
        # Convertir paquete a bits
        bits = []
        for byte in packet:
            for i in range(8):
                bits.append((byte >> (7-i)) & 1)
        
        # Convertir a símbolos
        symbols = self.protocol.bits_to_symbols(bits)
        
        # Generar audio
        for symbol in symbols:
            audio.extend(self.protocol.generate_tone(symbol))
        
        # Normalizar
        audio = np.array(audio)
        audio = (audio * 32767 * 0.9).astype(np.int16)
        
        # Enviar por stream
        self.stream.write(audio.tobytes())
    
    def close(self):
        if self.stream:
            self.stream.close()
        self.audio.terminate()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 audio_stream_sender.py <archivo>")
        sys.exit(1)
    
    sender = AudioStreamSender()
    try:
        sender.send_file_stream(sys.argv[1])
    finally:
        sender.close()
