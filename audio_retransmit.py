import sys
import os
from audio_protocol import AudioProtocol, PacketType

def retransmit_packets(tx_prefix, rx_prefix):
    """Lee NACKs y retransmite paquetes solicitados"""
    protocol = AudioProtocol()
    
    # Buscar archivos NACK
    nack_files = []
    seq = 0
    while os.path.exists(f"{rx_prefix}_nack_{seq:04d}.wav"):
        nack_files.append(f"{rx_prefix}_nack_{seq:04d}.wav")
        seq += 1
    
    if not nack_files:
        print("No se encontraron archivos NACK")
        return
    
    print(f"Encontrados {len(nack_files)} NACKs")
    
    # Procesar cada NACK
    missing_packets = []
    for nack_file in nack_files:
        try:
            packet = protocol.decode_from_audio(nack_file)
            ptype, seq, data, valid = protocol.decode_packet(packet)
            if ptype == PacketType.NACK and valid:
                missing_packets.append(seq)
                print(f"✓ NACK recibido para paquete {seq}")
        except Exception as e:
            print(f"✗ Error leyendo {nack_file}: {e}")
    
    if not missing_packets:
        print("No se pudieron decodificar los NACKs")
        return
    
    print(f"\nRetransmitiendo {len(missing_packets)} paquetes...")
    
    # Copiar paquetes solicitados con nuevo prefijo
    for seq in missing_packets:
        src = f"{tx_prefix}_data_{seq:04d}.wav"
        dst = f"{tx_prefix}_retx_{seq:04d}.wav"
        
        if os.path.exists(src):
            # Copiar archivo
            with open(src, 'rb') as f:
                data = f.read()
            with open(dst, 'wb') as f:
                f.write(data)
            print(f"✓ Retransmitiendo paquete {seq}: {dst}")
        else:
            print(f"✗ Paquete original {seq} no encontrado: {src}")
    
    print(f"\n📢 Reproduce los archivos {tx_prefix}_retx_*.wav en el receptor")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python3 audio_retransmit.py <prefijo_tx> <prefijo_rx>")
        print("Ejemplo: python3 audio_retransmit.py tx rx")
        sys.exit(1)
    
    retransmit_packets(sys.argv[1], sys.argv[2])
