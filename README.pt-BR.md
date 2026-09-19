*[English version](README.md)*

# mi-scale-garmin-bridge

Lê o peso de balanças Xiaomi Mi Scale via Bluetooth LE — sem precisar do
app oficial (Mi Fit / Zepp Life) — e, opcionalmente, sobe o resultado
direto para o Garmin Connect como um weigh-in manual.

Testado numa **Mi Smart Scale 2**. O protocolo usado (serviço Bluetooth
SIG padrão "Weight Scale", UUID `0x181D`) é comum a várias balanças
Xiaomi, mas o layout exato dos bytes pode variar entre modelos e
firmwares — não confirmado em outros aparelhos. Se não funcionar no seu,
rode com `--raw` e abra uma issue com a saída.

## Por que

A balança transmite o peso via *advertisement* BLE (broadcast, sem
pareamento) enquanto alguém está em cima dela. Isso significa que dá
para capturar a leitura direto pelo Bluetooth do computador, sem depender
do app do fabricante.

## Instalação

```bash
pip install -r requirements.txt
```

`garminconnect` só é necessário se você for usar `--upload`.

## Descobrir o MAC da sua balança

```bash
python mi_scale_reader.py --discover
```

Sobe na balança assim que o comando rodar — ele lista os dispositivos
próximos que anunciam o serviço Weight Scale.

## Uso

```bash
# só ler o peso
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF

# ler e subir pro Garmin Connect
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --upload

# esperar mais tempo (padrão: 60s)
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --timeout 90

# modo diagnóstico: dump bruto de todos os pacotes recebidos
python mi_scale_reader.py --mac AA:BB:CC:DD:EE:FF --raw
```

Para não digitar `--mac` toda vez, defina a variável de ambiente
`MI_SCALE_MAC` com o endereço da sua balança.

## Upload para o Garmin Connect

Usa a biblioteca [`garminconnect`](https://pypi.org/project/garminconnect/)
(não oficial). No primeiro `--upload`, o script pede email, senha e
código MFA (se sua conta usar) interativamente no terminal — nada é
salvo em texto puro. A sessão autenticada fica cacheada em
`~/.mi_scale_garmin_tokens`, fora deste repositório, e é reaproveitada
nas próximas execuções.

Se você usa [Intervals.icu](https://intervals.icu) com a conta Garmin
já sincronizada, o peso aparece lá automaticamente — não precisa de uma
segunda integração.

## Atalho no Windows

`weigh.bat` roda o upload com um clique. Edite o arquivo (ou defina
`MI_SCALE_MAC` como variável de ambiente do sistema) antes de usar.

## Protocolo (para quem quiser adaptar para outro modelo)

```
byte0        = controle (bit 0x20 = peso estabilizado/final)
bytes1-2     = peso, uint16 little-endian, unidade = raw / 200.0 (kg)
bytes3-9     = timestamp do RTC interno da balança (não usado aqui)
```

Confirmado comparando os valores decodificados contra uma pesagem real:
a leitura converge para o mesmo peso nos pacotes marcados como estáveis
pelo bit `0x20` do byte de controle.

## Aviso

Projeto não oficial, sem afiliação com a Xiaomi ou a Garmin. Protocolo
obtido por engenharia reversa das transmissões BLE públicas do
dispositivo — use por sua conta e risco.

## Licença

MIT — veja [LICENSE](LICENSE).
