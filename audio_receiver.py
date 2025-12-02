import sys
import os
from audio_protocol import AudioProtocol, PacketType

def receive_file(input_prefix, output_file, request_retransmit=True):
    """Recibe archivo desde paquetes de audio con soporte para retransmisión"""
    protocol = AudioProtocol()
    compressed = False
    
    # Recibir SYN
    print("Esperando SYN...")
    try:
        syn_packet = protocol.decode_from_audio(f"{input_prefix}_syn.wav")
        ptype, seq, data, valid = protocol.decode_packet(syn_packet)
        if ptype == PacketType.SYN and valid:
            compressed = data[0] == 1 if len(data) > 0 else False
            print(f"✓ SYN recibido (compresión: {'sí' if compressed else 'no'})")
        else:
            print("✗ Error en SYN")
            return False
    except Exception as e:
        print(f"✗ Error leyendo SYN: {e}")
        return False
    
    # Recibir paquetes de datos
    received_packets = {}
    expected_packets = None
    seq = 0
    
    # Primera pasada: recibir todos los paquetes disponibles
    print("\nRecibiendo paquetes...")
    while True:
        try:
            packet = protocol.decode_from_audio(f"{input_prefix}_data_{seq:04d}.wav")
            ptype, pkt_seq, data, valid = protocol.decode_packet(packet)
            
            if ptype == PacketType.DATA and valid:
                received_packets[pkt_seq] = data
                print(f"✓ Paquete {pkt_seq} recibido ({len(data)} bytes)")
            else:
                print(f"✗ Error en paquete {seq} (checksum inválido)")
            
            seq += 1
        except FileNotFoundError:
            break
        except Exception as e:
            print(f"⚠ Paquete {seq} no disponible")
            seq += 1
            if seq > 1000:  # Límite de seguridad
                break
    
    # Recibir FIN
    try:
        fin_packet = protocol.decode_from_audio(f"{input_prefix}_fin.wav")
        ptype, fin_seq, data, valid = protocol.decode_packet(fin_packet)
        if ptype == PacketType.FIN and valid:
            expected_packets = fin_seq
            print(f"✓ FIN recibido (esperados {expected_packets} paquetes)")
        else:
            print("✗ Error en FIN")
    except Exception as e:
        print(f"✗ Error leyendo FIN: {e}")
    
    # Verificar paquetes faltantes
    if expected_packets is not None:
        missing = []
        for i in range(expected_packets):
            if i not in received_packets:
                missing.append(i)
        
        if missing:
            print(f"\n⚠ Faltan {len(missing)} paquetes: {missing[:10]}{'...' if len(missing) > 10 else ''}")
            
            if request_retransmit:
                print("\nGenerando NACKs para solicitar retransmisión...")
                protocol.generate_nack(missing, "rx")
                print(f"\n📢 Reproduce los archivos rx_nack_*.wav en el emisor")
                print("   El emisor debe generar los paquetes faltantes con:")
                print(f"   python3 audio_retransmit.py {input_prefix} rx")
                return False
        else:
            print(f"\n✓ Todos los paquetes recibidos correctamente")
    
    # Reconstruir datos
    received_data = bytearray()
    for i in sorted(received_packets.keys()):
        received_data.extend(received_packets[i])
    
    # Descomprimir si es necesario
    if compressed:
        try:
            received_data = protocol.decompress_data(bytes(received_data))
            print(f"✓ Datos descomprimidos: {len(received_data)} bytes")
        except Exception as e:
            print(f"✗ Error descomprimiendo: {e}")
            return False
    
    # Guardar archivo
    with open(output_file, 'wb') as f:
        f.write(received_data)
    
    print(f"\n✓ Archivo guardado: {output_file} ({len(received_data)} bytes)")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python3 audio_receiver.py <prefijo_entrada> <archivo_salida> [--no-retransmit]")
        print("Ejemplo: python3 audio_receiver.py tx archivo_recuperado.txt")
        sys.exit(1)
    
    request_retransmit = '--no-retransmit' not in sys.argv
    receive_file(sys.argv[1], sys.argv[2], request_retransmit)
