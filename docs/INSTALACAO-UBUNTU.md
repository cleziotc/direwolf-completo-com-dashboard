# Instalação no Ubuntu

## Plataformas recomendadas

O instalador foi preparado para Ubuntu Server/Desktop moderno em arquitetura x86_64 ou ARM64.

Uma VM também funciona, desde que a placa de áudio USB e a interface serial sejam entregues corretamente ao guest.

## Antes de começar

Tenha em mãos:

- indicativo APRS com SSID;
- latitude e longitude em graus decimais;
- altitude;
- altura e ganho aproximados da antena;
- potência do transmissor;
- interface de áudio conectada;
- interface serial/PTT, caso pretenda transmitir.

Para começar somente como iGate RX, a serial não é obrigatória.

## Instalação automática

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-ubuntu.sh | sudo bash
```

O assistente pergunta os dados da estação e detecta o hardware.

## Instalação a partir de clone

```bash
git clone https://github.com/cleziotc/direwolf-completo-com-dashboard.git
cd direwolf-completo-com-dashboard
sudo bash install-ubuntu.sh
```

## O que será criado

Usuário:

```text
aprs
```

Arquivos principais:

```text
/home/aprs/direwolf.conf
/home/aprs/.config/aprs-dashboard.env
/home/aprs/aprs-dashboard/
```

Serviços:

```text
direwolf.service
aprs-dashboard.service
aprs-hardware-watchdog.service
```

## Instalação não interativa

Exemplo RX-only:

```bash
sudo env \
  APRS_NONINTERACTIVE=1 \
  APRS_CALLSIGN=PY1ABC-10 \
  APRS_LOCATION_LABEL="São Paulo-SP" \
  APRS_TIMEZONE=America/Sao_Paulo \
  APRS_LATITUDE=-23.5505 \
  APRS_LONGITUDE=-46.6333 \
  APRS_ALTITUDE_M=760 \
  APRS_ANTENNA_HEIGHT_M=20 \
  APRS_ANTENNA_GAIN_DBI=3 \
  APRS_POWER_W=5 \
  APRS_FILTER_RADIUS_KM=100 \
  APRS_ENABLE_TX=N \
  bash install-ubuntu.sh
```

## Verificação após instalação

```bash
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
```

Confira o áudio:

```bash
arecord -l
```

Confira serial:

```bash
ls -l /dev/serial/by-id/ /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Abra:

```text
http://IP-DO-SERVIDOR:8088/
```

## VM / Proxmox

Ao utilizar passthrough USB:

- prefira entregar o dispositivo inteiro à VM;
- confirme no guest com `lsusb`;
- confirme a captura com `arecord -l`;
- confirme a serial com `ls -l /dev/serial/by-id`;
- verifique o host e o guest quando houver `USB disconnect` ou `error -71`.

Um erro de enumeração já presente no host não pode ser corrigido pelo Direwolf.

## Firewall

Se UFW estiver ativo e o painel precisar ser acessado pela LAN:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8088 proto tcp
```

Ajuste a rede conforme seu ambiente. Não exponha a página de configuração diretamente à Internet.

## Atualização

```bash
sudo -u aprs aprs-update
```

O script se recusa a atualizar quando há arquivos modificados dentro do clone, evitando perda acidental.
