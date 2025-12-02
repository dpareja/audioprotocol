import numpy as np
import wave
import zlib
from enum import Enum

class PacketType(Enum):
    DATA = 0
    ACK = 1
    NACK = 2
    SYN = 3
    FIN = 4

class AudioProtocol:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.bit_duration = 0.005  # 5ms por bit = 200 bits/seg
        self.samples_per_bit = int(sample_rate * self.bit_duration)
        
        # Frecuencias para 4 símbolos (2 bits por símbolo)
        self.freqs = {
            0: 1000,  # 00
            1: 1500,  # 01
            2: 2000,  # 10
            3: 2500   # 11
        }
        
        self.packet_size = 32  # bytes por paquete
        self.max_retries = 3
    
    def encode_packet(self, packet_type, seq_num, data):
        """Codifica un paquete: [tipo(1B)][seq(1B)][len(1B)][data][checksum(2B)]"""
        packet = bytearray()
        packet.append(packet_type.value)
        packet.append(seq_num & 0xFF)
        packet.append(len(data) & 0xFF)
        packet.extend(data)
        
        # Checksum
        checksum = sum(packet) & 0xFFFF
        packet.append((checksum >> 8) & 0xFF)
        packet.append(checksum & 0xFF)
        
        return bytes(packet)
    
    def decode_packet(self, packet):
        """Decodifica un paquete y verifica checksum"""
        if len(packet) < 5:
            return None, None, None, False
        
        packet_type = PacketType(packet[0])
        seq_num = packet[1]
        data_len = packet[2]
        data = packet[3:3+data_len]
        
        # Verificar checksum
        received_checksum = (packet[-2] << 8) | packet[-1]
        calculated_checksum = sum(packet[:-2]) & 0xFFFF
        
        valid = received_checksum == calculated_checksum
        return packet_type, seq_num, data, valid
    
    def bits_to_symbols(self, bits):
        """Convierte bits a símbolos de 2 bits"""
        symbols = []
        for i in range(0, len(bits), 2):
            if i+1 < len(bits):
                symbol = (bits[i] << 1) | bits[i+1]
            else:
                symbol = bits[i] << 1
            symbols.append(symbol)
        return symbols
    
    def symbols_to_bits(self, symbols):
        """Convierte símbolos a bits"""
        bits = []
        for symbol in symbols:
            bits.append((symbol >> 1) & 1)
            bits.append(symbol & 1)
        return bits
    
    def generate_tone(self, symbol):
        """Genera tono para un símbolo"""
        freq = self.freqs[symbol]
        t = np.linspace(0, self.bit_duration, self.samples_per_bit, False)
        return np.sin(2 * np.pi * freq * t)
    
    def encode_to_audio(self, packet, filename):
        """Codifica paquete a audio"""
        # Convertir a bits
        bits = []
        for byte in packet:
            for i in range(8):
                bits.append((byte >> (7-i)) & 1)
        
        # Convertir a símbolos
        symbols = self.bits_to_symbols(bits)
        
        # Generar audio
        audio = []
        for symbol in symbols:
            audio.extend(self.generate_tone(symbol))
        
        # Normalizar
        audio = np.array(audio)
        audio = (audio * 32767).astype(np.int16)
        
        # Guardar
        with wave.open(filename, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio.tobytes())
    
    def decode_from_audio(self, filename):
        """Decodifica audio a paquete"""
        # Leer audio
        with wave.open(filename, 'r') as wav:
            frames = wav.readframes(wav.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
        
        # Decodificar símbolos
        symbols = []
        for i in range(0, len(audio), self.samples_per_bit):
            chunk = audio[i:i+self.samples_per_bit]
            if len(chunk) < self.samples_per_bit // 2:
                break
            
            # FFT para detectar frecuencia
            fft = np.fft.fft(chunk)
            freqs = np.fft.fftfreq(len(chunk), 1/self.sample_rate)
            
            # Encontrar símbolo con mayor energía
            max_energy = 0
            detected_symbol = 0
            for symbol, freq in self.freqs.items():
                energy = np.abs(fft[np.abs(freqs - freq) < 100]).sum()
                if energy > max_energy:
                    max_energy = energy
                    detected_symbol = symbol
            
            symbols.append(detected_symbol)
        
        # Convertir a bits
        bits = self.symbols_to_bits(symbols)
        
        # Convertir a bytes
        packet = bytearray()
        for i in range(0, len(bits), 8):
            if i + 8 <= len(bits):
                byte = 0
                for j in range(8):
                    byte = (byte << 1) | bits[i+j]
                packet.append(byte)
        
        return bytes(packet)
    
    def compress_data(self, data):
        """Comprime datos con zlib"""
        return zlib.compress(data, level=9)
    
    def decompress_data(self, data):
        """Descomprime datos con zlib"""
        return zlib.decompress(data)
    
    def send_file(self, filename, output_prefix="tx", compress=True):
        """Envía archivo dividido en paquetes con compresión opcional"""
        with open(filename, 'rb') as f:
            data = f.read()
        
        original_size = len(data)
        
        # Comprimir si está habilitado
        if compress:
            data = self.compress_data(data)
            print(f"Compresión: {original_size} → {len(data)} bytes ({100*(1-len(data)/original_size):.1f}% reducción)")
        
        # Dividir en paquetes
        packets = []
        for i in range(0, len(data), self.packet_size):
            chunk = data[i:i+self.packet_size]
            packets.append(chunk)
        
        print(f"Enviando {len(data)} bytes en {len(packets)} paquetes...")
        
        # Enviar SYN con flag de compresión
        syn_data = bytes([1 if compress else 0])
        syn_packet = self.encode_packet(PacketType.SYN, 0, syn_data)
        self.encode_to_audio(syn_packet, f"{output_prefix}_syn.wav")
        print(f"✓ SYN generado: {output_prefix}_syn.wav")
        
        # Enviar paquetes de datos
        for seq, chunk in enumerate(packets):
            data_packet = self.encode_packet(PacketType.DATA, seq, chunk)
            self.encode_to_audio(data_packet, f"{output_prefix}_data_{seq:04d}.wav")
            print(f"✓ Paquete {seq+1}/{len(packets)}: {output_prefix}_data_{seq:04d}.wav")
        
        # Enviar FIN
        fin_packet = self.encode_packet(PacketType.FIN, len(packets), b'')
        self.encode_to_audio(fin_packet, f"{output_prefix}_fin.wav")
        print(f"✓ FIN generado: {output_prefix}_fin.wav")
        
        return len(packets)
    
    def generate_nack(self, missing_packets, output_prefix="rx"):
        """Genera paquetes NACK para solicitar retransmisión"""
        for seq in missing_packets:
            nack_packet = self.encode_packet(PacketType.NACK, seq, b'')
            self.encode_to_audio(nack_packet, f"{output_prefix}_nack_{seq:04d}.wav")
            print(f"✓ NACK generado para paquete {seq}: {output_prefix}_nack_{seq:04d}.wav")
    
    def generate_ack(self, seq, output_prefix="rx"):
        """Genera paquete ACK"""
        ack_packet = self.encode_packet(PacketType.ACK, seq, b'')
        self.encode_to_audio(ack_packet, f"{output_prefix}_ack_{seq:04d}.wav")
        print(f"✓ ACK generado para paquete {seq}: {output_prefix}_ack_{seq:04d}.wav")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 audio_protocol.py <archivo> [--no-compress]")
        sys.exit(1)
    
    compress = '--no-compress' not in sys.argv
    protocol = AudioProtocol()
    protocol.send_file(sys.argv[1], compress=compress)
