# Mapas offline

## Objetivo

O dashboard pode armazenar tiles no próprio servidor para que a visualização do mapa continue disponível quando o provedor online estiver indisponível.

Isso não torna o APRS-IS offline; apenas mantém as cartas locais já baixadas.

## Camadas

O sistema oferece pacotes de:

- ruas;
- satélite.

Os arquivos ficam em:

```text
/home/aprs/aprs-dashboard/data/offline-maps/
```

## Download pela página de configuração

Na página `/config`:

1. escolha o centro do mapa;
2. defina o raio;
3. selecione o zoom máximo;
4. solicite a estimativa;
5. inicie o download.

O centro do pacote offline é independente da posição oficial da estação.

## Limite de segurança

O backend limita o número de tiles por pacote para evitar downloads acidentais gigantes.

Quanto maior:

- o raio;
- o zoom;
- a quantidade de camadas;

maior será o uso de disco.

## Raspberry Pi

Em cartões SD pequenos, seja conservador. Zoom alto sobre grande área pode consumir muito espaço e aumentar escrita no cartão.

## Exclusão

Pacotes podem ser removidos pela interface. A exclusão apaga o cache correspondente no servidor.

## Fallback

O dashboard tenta a fonte online normalmente. Quando um tile remoto falha, pode utilizar o tile local equivalente, se ele estiver presente.
