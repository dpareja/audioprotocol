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

class AudioProtocolUltrasonic:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.bit_duration = 0.004  # 4ms por símbolo = 250 símbolos/seg
        self.samples_per_bit = int(sample_rate * self.bit_duration)
        
        # 8 frecuencias ultrasónicas (17-20.4 kHz, espaciadas cada 485 Hz)
        # 8 frecuencias = 3 bits por símbolo
        self.freqs = {}
        base_freq = 17000
        for i in range(8):
            self.freqs[i] = base_freq + (i * 485)
        
        # 3 bits/símbolo * 250 símbolos/seg = 750 bits/seg = 93.75 bytes/seg
        
        self.packet_size = 64  # bytes por paquete (aumentado)
        self.max_retries = 3
        
        print(f"AudioProtocol Ultrasónico inicializado:")
        print(f"  Rango de frecuencias: {self.freqs[0]}-{self.freqs[7]} Hz")
        print(f"  Velocidad: 750 bits/seg (93.75 bytes/seg)")
        print(f"  Bits por símbolo: 3")
    
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
        """Convierte bits a símbolos de 3 bits"""
        symbols = []
        for i in range(0, len(bits), 3):
            symbol = 0
            for j in range(3):
                if i+j < len(bits):
                    symbol = (symbol << 1) | bits[i+j]
                else:
                    symbol = symbol << 1
            symbols.append(symbol)
        return symbols
    
    def symbols_to_bits(self, symbols):
        """Convierte símbolos a bits"""
        bits = []
        for symbol in symbols:
            for i in range(2, -1, -1):
                bits.append((symbol >> i) & 1)
        return bits
    
    def generate_tone(self, symbol):
        """Genera tono ultrasónico para un símbolo"""
        freq = self.freqs[symbol]
        t = np.linspace(0, self.bit_duration, self.samples_per_bit, False)
        # Sin ventana para mejor detección
        tone = np.sin(2 * np.pi * freq * t)
        return tone
    
    def generate_preamble(self):
        """Genera preámbulo de sincronización (patrón conocido)"""
        # Patrón: 0, 7, 0, 7 (frecuencias extremas para sincronización)
        preamble = []
        for symbol in [0, 7, 0, 7]:
            preamble.extend(self.generate_tone(symbol))
        return np.array(preamble)
    
    def encode_to_audio(self, packet, filename):
        """Codifica paquete a audio ultrasónico con preámbulo"""
        # Generar preámbulo
        audio = list(self.generate_preamble())
        
        # Convertir a bits
        bits = []
        for byte in packet:
            for i in range(8):
                bits.append((byte >> (7-i)) & 1)
        
        # Convertir a símbolos
        symbols = self.bits_to_symbols(bits)
        
        # Generar audio de datos
        for symbol in symbols:
            audio.extend(self.generate_tone(symbol))
        
        # Normalizar
        audio = np.array(audio)
        audio = (audio * 32767 * 0.9).astype(np.int16)
        
        # Guardar
        with wave.open(filename, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio.tobytes())
    
    def decode_from_audio(self, filename):
        """Decodifica audio ultrasónico a paquete con detección de preámbulo"""
        # Leer audio
        with wave.open(filename, 'r') as wav:
            frames = wav.readframes(wav.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
        
        # Saltar preámbulo (4 símbolos)
        preamble_samples = 4 * self.samples_per_bit
        audio = audio[preamble_samples:]
        
        # Decodificar símbolos usando Goertzel algorithm (más eficiente que FFT)
        symbols = []
        for i in range(0, len(audio), self.samples_per_bit):
            chunk = audio[i:i+self.samples_per_bit]
            if len(chunk) < self.samples_per_bit:
                break
            
            # Calcular energía para cada frecuencia usando Goertzel
            max_energy = 0
            detected_symbol = 0
            
            for symbol, target_freq in self.freqs.items():
                # Goertzel algorithm
                k = int(0.5 + (len(chunk) * target_freq) / self.sample_rate)
                omega = (2.0 * np.pi * k) / len(chunk)
                coeff = 2.0 * np.cos(omega)
                
                q0 = 0.0
                q1 = 0.0
                q2 = 0.0
                
                for sample in chunk:
                    q0 = coeff * q1 - q2 + sample
                    q2 = q1
                    q1 = q0
                
                # Calcular magnitud
                real = q1 - q2 * np.cos(omega)
                imag = q2 * np.sin(omega)
                energy = real * real + imag * imag
                
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
    
    def send_file(self, filename, output_prefix="tx_ultra", compress=True):
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
        
        # Calcular tiempo estimado
        total_bytes = sum(len(self.encode_packet(PacketType.DATA, i, p)) for i, p in enumerate(packets))
        total_bytes += len(syn_packet) + len(fin_packet)
        estimated_time = (total_bytes * 8) / 750  # 750 bits/seg
        print(f"\n⏱ Tiempo estimado de transmisión: {estimated_time:.1f} segundos")
        
        return len(packets)
    
    def generate_nack(self, missing_packets, output_prefix="rx_ultra"):
        """Genera paquetes NACK para solicitar retransmisión"""
        for seq in missing_packets:
            nack_packet = self.encode_packet(PacketType.NACK, seq, b'')
            self.encode_to_audio(nack_packet, f"{output_prefix}_nack_{seq:04d}.wav")
            print(f"✓ NACK generado para paquete {seq}: {output_prefix}_nack_{seq:04d}.wav")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 audio_protocol_ultrasonic.py <archivo> [--no-compress]")
        sys.exit(1)
    
    compress = '--no-compress' not in sys.argv
    protocol = AudioProtocolUltrasonic()
    protocol.send_file(sys.argv[1], compress=compress)
