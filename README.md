# Muro Humano

> Jogo em tempo real em que o jogador precisa encaixar o corpo no buraco de uma parede que se aproxima, usando visão computacional com MediaPipe. *(Nome provisório.)*

## Descrição

O projeto é uma versão do jogo "Hole in the Wall": uma parede com um buraco em formato de pose vem na tela e o jogador, de frente para a webcam, precisa imitar a pose para passar por ela.

O sistema usa o MediaPipe Pose Landmarker para obter a silhueta do jogador e mede quanto do corpo ficou fora do buraco. Se passar de um limite, o jogador perde uma vida. Quando as vidas acabam, ele "cai na água" e o jogo termina.

Os buracos não são desenhados à mão: são gerados a partir de poses capturadas pela própria webcam.

## Objetivos

- Detectar a silhueta do jogador em tempo real.
- Comparar a silhueta com o buraco da parede e decidir se o jogador passou.
- Gerar as fases a partir de poses capturadas pela webcam.
- Medir a precisão do veredito do jogo e o desempenho (FPS).

## Como funciona


<img width="981" height="2296" alt="image" src="https://github.com/user-attachments/assets/9619c309-187f-4ef0-86d9-1dadccef2243" />


**Resumo do fluxo:**

1. As fases são criadas antes do jogo: o jogador faz uma pose, o sistema captura a silhueta, engrossa o contorno e salva como buraco.
2. Durante o jogo, cada frame da webcam é espelhado e processado pelo MediaPipe, que devolve a silhueta do jogador.
3. A silhueta é comparada com o buraco da fase atual, e o sistema calcula a porcentagem do corpo que ficou fora dele.
4. Quando a parede chega ao jogador, se a porcentagem estiver abaixo do limite, ele pontua e avança. Se não, perde uma vida.

## Tecnologias

- Python
- OpenCV
- MediaPipe (Pose Landmarker)
- NumPy

## Validação

Plano de validação:

- Cerca de 50 tentativas com pessoas diferentes.
- Para cada tentativa, comparar o veredito do jogo ("passou" ou "caiu") com o julgamento de uma pessoa observando.
- Métrica de precisão: taxa de concordância entre o jogo e o julgamento humano.
- Métrica de desempenho: FPS médio durante o jogo.


## Escopo e limitações

- Um jogador por vez.
- O corpo inteiro precisa aparecer na câmera, então é preciso uma distância que permita esse enquadramento.
- Fundo muito poluído, pouca luz e roupa parecida com o fundo podem prejudicar a detecção da silhueta.


## Integrantes

- Luiz Fabiano Nascimento Vale da Silva — RM 553529 — [github.com/euLuizinho](https://github.com/euLuizinho)


