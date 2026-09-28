# Segurança

## Credenciais

Nunca publique:

- passcode APRS-IS;
- tokens;
- senhas;
- chaves SSH;
- arquivos `.env` reais.

O `.gitignore` bloqueia arquivos `.env`, mas isso não substitui revisão antes do commit.

## Página de configuração

A API de escrita da configuração foi projetada para rede privada/loopback. Mesmo assim:

- não faça port-forward de 8088 para a Internet;
- prefira VPN para acesso remoto;
- use firewall;
- mantenha o sistema atualizado.

## TX RF

Qualquer alteração que habilite transmissão deve ser considerada sensível operacionalmente.

O instalador mantém TX desabilitado por padrão.

## Reportar vulnerabilidade

Não abra issue pública contendo credenciais ou detalhes que exponham uma estação.

Para bugs sem informação sensível, use Issues normalmente.
