# Instalação no Raspberry Pi

## Sistemas suportados

O objetivo é suportar Raspberry Pi OS baseado em Debian, tanto 32-bit quanto 64-bit.

O mesmo projeto pode ser usado em modelos pequenos, mas compilação e mapas offline exigem mais tempo e armazenamento.

## Preparação

Atualize o sistema:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Depois conecte:

- interface de áudio USB;
- interface serial/PTT, se houver;
- rede Ethernet ou Wi-Fi.

## Instalação

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

O instalador limita automaticamente o paralelismo de compilação em Raspberry com pouca memória, reduzindo a chance de OOM durante a construção do Direwolf.

## Clone manual

```bash
git clone https://github.com/cleziotc/direwolf-completo-com-dashboard.git
cd direwolf-completo-com-dashboard
sudo bash install-raspberry.sh
```

## Raspberry Pi Zero

Em modelos com pouca RAM:

- a compilação pode demorar;
- prefira Raspberry Pi OS Lite;
- evite outros processos pesados durante a instalação;
- reduza o raio/zoom de mapas offline;
- mantenha espaço livre no cartão.

O instalador escolhe um número conservador de jobs de compilação.

## Áudio

```bash
arecord -l
cat /proc/asound/cards
```

O instalador usa o primeiro dispositivo de captura detectado, a menos que as variáveis `APRS_ALSA_CARD` e `APRS_ALSA_DEVICE_INDEX` sejam informadas.

## Serial / PTT

Prefira:

```text
/dev/serial/by-id/...
```

Esses nomes costumam ser mais estáveis que `/dev/ttyUSB0`.

Para descobrir:

```bash
ls -l /dev/serial/by-id/
```

## Fonte de alimentação

Em Raspberry, alimentação ruim pode produzir sintomas parecidos com falha USB. Verifique:

```bash
vcgencmd get_throttled
```

Quando disponível, `0x0` indica que não há flags atuais ou históricas de undervoltage/throttling.

## Serviço 24/7

Os três serviços são habilitados no boot:

```bash
systemctl is-enabled direwolf
systemctl is-enabled aprs-dashboard
systemctl is-enabled aprs-hardware-watchdog
```

## Operação sem Internet

O dashboard pode utilizar mapas previamente baixados, mas APRS-IS naturalmente requer conexão de rede. Um digipeater RF pode continuar funcionando sem APRS-IS conforme sua configuração do Direwolf.
