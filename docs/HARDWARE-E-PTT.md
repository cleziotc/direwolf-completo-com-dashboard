# Hardware, áudio e PTT

## Cadeia básica

Uma estação típica usa:

- transceptor VHF/UHF;
- interface de áudio USB;
- saída de áudio do rádio para entrada da placa;
- saída da placa para entrada de modulação do rádio, quando TX é usado;
- conversor USB/serial ou interface equivalente para PTT;
- computador Ubuntu ou Raspberry Pi.

## Áudio USB

Verifique:

```bash
lsusb
arecord -l
aplay -l
cat /proc/asound/cards
```

O `ADEVICE` deve apontar para o dispositivo correto, por exemplo:

```text
ADEVICE plughw:0,0
```

O dashboard também registra VID/PID da placa quando o instalador consegue descobrir esses valores no sysfs.

## Nível de RX

O VU RX do dashboard utiliza o valor relativo publicado pelo Direwolf. Ele **não é um medidor calibrado em dBFS**.

O objetivo é facilitar:

- perceber ausência de áudio;
- identificar nível excessivamente baixo;
- comparar alterações;
- observar atividade do canal.

Faça o ajuste final conforme a documentação do Direwolf e a qualidade real de decodificação.

## VU TX

O Direwolf não fornece ao dashboard a amplitude PCM real da transmissão. Portanto, o VU TX representa atividade de transmissão e não deve ser interpretado como medição absoluta de nível.

## PTT via serial

O projeto suporta a diretiva padrão do Direwolf para linhas de controle serial.

Exemplos:

```text
PTT /dev/ttyUSB0 DTR
PTT /dev/ttyUSB0 RTS
PTT /dev/ttyUSB0 -DTR
PTT /dev/ttyUSB0 -RTS
```

## Usar /dev/serial/by-id

Para uma instalação permanente:

```bash
ls -l /dev/serial/by-id/
```

Quando existir um nome persistente, prefira-o no lugar de `/dev/ttyUSB0`.

Assim, uma reconexão que faça o kernel trocar `ttyUSB0` por `ttyUSB1` não quebra a configuração.

## DTR/RTS e transistor

Não conecte uma linha RS-232 clássica diretamente ao PTT sem entender os níveis elétricos envolvidos.

Em interfaces USB-TTL, DTR/RTS normalmente acionam um transistor, optoacoplador ou circuito de chaveamento apropriado.

Verifique:

- polaridade;
- isolamento;
- terra;
- corrente de PTT;
- retorno de RF;
- nível lógico do adaptador.

## EMI / RF

Uma queda de serial acompanhada no host por mensagens como:

```text
USB disconnect
device descriptor read/64, error -71
Device not responding to setup address
```

acontece abaixo do Direwolf e deve ser investigada como problema de USB, alimentação, contato, cabo ou interferência eletromagnética.

Medidas úteis:

- cabo USB curto;
- ferrites;
- bom aterramento;
- separar cabos RF e USB;
- evitar loops de terra;
- testar outra porta USB;
- testar outro conversor;
- testar com PTT desconectado do rádio;
- comparar logs do host e da VM.

## VM / passthrough

Em virtualização, confirme a presença do dispositivo tanto no host quanto na VM.

Host:

```bash
lsusb -t
journalctl -k -f
```

Guest:

```bash
lsusb
arecord -l
dmesg -wT
```

Se o host perde a enumeração física, alterar o Direwolf dentro da VM não corrige a causa.
