"""
Le o peso de balancas Xiaomi Mi Scale via Bluetooth LE (servico Bluetooth
SIG "Weight Scale", UUID 0x181D) e, opcionalmente, sobe o resultado como
um weigh-in no Garmin Connect - sem depender do app oficial (Mi Fit /
Zepp Life).

Protocolo confirmado empiricamente numa Mi Smart Scale 2 (setembro/2026):
uma pesagem real convergiu para o mesmo valor nos pacotes marcados como
"estaveis" pelo byte de controle. Deve funcionar em qualquer balanca
Xiaomi que anuncie pelo servico Bluetooth SIG padrao 0x181D, mas o layout
exato pode variar entre modelos/firmwares - nao testado em outros
aparelhos. Se o seu nao bater, rode com --raw e --discover pra investigar,
e abra uma issue com o que encontrar.

    byte0        = controle (bit 0x20 = peso estabilizado/final)
    bytes1-2     = peso, uint16 little-endian, unidade = raw / 200.0 (kg)
    bytes3-9     = timestamp do RTC interno da balanca (nao usado aqui)

Instalacao:
    pip install -r requirements.txt

Descobrir o endereco MAC da sua balanca:
    python mi_scale_reader.py --discover

Uso:
    python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF
    python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --timeout 90
    python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --raw
    python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --upload

Ou defina a variavel de ambiente MI_SCALE_MAC para nao precisar passar
--mac toda vez.

--upload requer `pip install garminconnect` e, na primeira execucao, pede
email/senha (e codigo MFA, se sua conta usar) do Garmin - digitados por
voce, no seu terminal, nunca ficam salvos em texto puro. A sessao fica
cacheada em ~/.mi_scale_garmin_tokens.
"""
import argparse
import asyncio
import getpass
import os
from datetime import datetime

from bleak import BleakScanner

WEIGHT_SCALE_SERVICE = "0000181d-0000-1000-8000-00805f9b34fb"
STABLE_BIT = 0x20
MIN_PLAUSIBLE_KG = 30.0
MAX_PLAUSIBLE_KG = 200.0

GARMIN_TOKEN_DIR = os.path.expanduser("~/.mi_scale_garmin_tokens")


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def parse_weight(data: bytes):
    if len(data) < 3:
        return None
    ctrl = data[0]
    raw = int.from_bytes(data[1:3], byteorder="little")
    return {
        "weight_kg": raw / 200.0,
        "stabilized": bool(ctrl & STABLE_BIT),
        "ctrl": ctrl,
    }


async def discover_scales(timeout: int):
    log(f"Escaneando dispositivos BLE que anunciam o servico Weight Scale (0x181D) por {timeout}s...")
    log("Suba na balanca para ela comecar a transmitir.")
    found = set()

    def callback(device, advertisement_data):
        if WEIGHT_SCALE_SERVICE not in advertisement_data.service_data:
            return
        if device.address in found:
            return
        found.add(device.address)
        print(f"  {device.address}  (RSSI={advertisement_data.rssi}, nome={device.name or '?'})")

    scanner = BleakScanner(callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    if not found:
        print("Nenhum dispositivo com o servico Weight Scale foi encontrado nesse intervalo.")
        print("Tente de novo subindo na balanca assim que o scan comecar.")


async def wait_for_stable_weight(mac: str, timeout: int):
    log(f"Escutando {mac} por ate {timeout}s. Suba na balanca agora...")
    result = {}
    done = asyncio.Event()

    def callback(device, advertisement_data):
        if device.address.upper() != mac.upper() or done.is_set():
            return
        raw = advertisement_data.service_data.get(WEIGHT_SCALE_SERVICE)
        if not raw:
            return
        parsed = parse_weight(raw)
        if not parsed:
            return
        if not parsed["stabilized"]:
            print(f"    medindo... {parsed['weight_kg']:.2f} kg")
            return
        if not (MIN_PLAUSIBLE_KG <= parsed["weight_kg"] <= MAX_PLAUSIBLE_KG):
            print(f"    leitura estavel descartada por estar fora da faixa plausivel: {parsed['weight_kg']:.2f} kg")
            return
        result.update(parsed)
        done.set()

    scanner = BleakScanner(callback)
    await scanner.start()
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    finally:
        await scanner.stop()

    if not result:
        print()
        print(f"Nenhuma leitura estavel em {timeout}s. Tente de novo e fique parado na balanca ate ela travar o valor.")
        return None

    log(f"Peso capturado: {result['weight_kg']:.2f} kg [ESTAVEL]")
    return result["weight_kg"]


async def raw_dump(mac: str, timeout: int):
    log(f"[--raw] Escaneando anuncios BLE de {mac} por {timeout}s...")
    seen = set()

    def callback(device, advertisement_data):
        if device.address.upper() != mac.upper():
            return
        key = tuple(sorted(advertisement_data.service_data.items()))
        if key in seen:
            return
        seen.add(key)
        log(f"RSSI={advertisement_data.rssi}")
        for uuid, raw in advertisement_data.service_data.items():
            print(f"    service_data[{uuid}] = {raw.hex()}")
            if uuid.lower() == WEIGHT_SCALE_SERVICE:
                parsed = parse_weight(raw)
                estab = "ESTAVEL" if parsed["stabilized"] else "medindo..."
                print(f"    -> {parsed['weight_kg']:.2f} kg [{estab}] ctrl=0x{parsed['ctrl']:02x}")
        for cid, raw in advertisement_data.manufacturer_data.items():
            print(f"    manufacturer_data[{cid}] = {raw.hex()}")

    scanner = BleakScanner(callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()


def upload_to_garmin(weight_kg: float):
    import garminconnect

    def prompt_mfa():
        return input("Codigo MFA do Garmin (se pedido): ").strip()

    os.makedirs(GARMIN_TOKEN_DIR, exist_ok=True)

    client = garminconnect.Garmin(prompt_mfa=prompt_mfa)
    try:
        client.login(tokenstore=GARMIN_TOKEN_DIR)
    except Exception:
        log("Sessao Garmin nao encontrada ou expirada, fazendo login com email/senha...")
        email = input("Email Garmin: ").strip()
        password = getpass.getpass("Senha Garmin: ")
        client = garminconnect.Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
        client.login(tokenstore=GARMIN_TOKEN_DIR)
        log(f"Sessao salva em {GARMIN_TOKEN_DIR} para as proximas execucoes.")

    timestamp = datetime.now().isoformat()
    try:
        client.add_weigh_in(weight=weight_kg, unitKey="kg", timestamp=timestamp)
    except Exception as exc:
        log(f"Falha ao enviar peso ao Garmin Connect: {exc}")
        return
    log(f"Peso de {weight_kg:.2f} kg enviado ao Garmin Connect.")


def main():
    parser = argparse.ArgumentParser(description="Leitor BLE de balancas Xiaomi Mi Scale, com upload opcional ao Garmin Connect")
    parser.add_argument("--mac", default=os.environ.get("MI_SCALE_MAC"), help="Endereco MAC da balanca (ou defina a env var MI_SCALE_MAC)")
    parser.add_argument("--discover", action="store_true", help="Lista dispositivos BLE proximos que anunciam o servico Weight Scale, para descobrir o MAC da sua balanca")
    parser.add_argument("--raw", action="store_true", help="Modo diagnostico: dump bruto de todos os pacotes recebidos")
    parser.add_argument("--upload", action="store_true", help="Apos capturar o peso estavel, sobe para o Garmin Connect")
    parser.add_argument("--timeout", type=int, default=60, help="Segundos de escuta (padrao 60)")
    args = parser.parse_args()

    if args.discover:
        asyncio.run(discover_scales(args.timeout))
        return

    if not args.mac:
        parser.error("--mac e obrigatorio (ou defina a env var MI_SCALE_MAC). Use --discover para encontrar o MAC da sua balanca.")

    if args.raw:
        asyncio.run(raw_dump(args.mac, args.timeout))
        return

    weight = asyncio.run(wait_for_stable_weight(args.mac, args.timeout))
    if weight is not None and args.upload:
        upload_to_garmin(weight)


if __name__ == "__main__":
    main()
