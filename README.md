# Jarvis

## Overview

Jarvis is an AI assistant designed to run on an Orange Pi Zero 2W. It will use cloud computing whenever possible to run the AI, but it will also have a local backup protocol just in case an internet connection or cloud service is unavailable.

The basic idea behind the code is fairly simple: take what the user says, send it off to an AI, and then speak the response. However, actually making this work is a much more complex problem than it sounds, especially when it comes to speech-to-text. Getting reliable voice recognition and making the whole system work together has been one of the bigger challenges.

## Hardware

The main components of Jarvis include:

- **Orange Pi Zero 2W:** The brains of the device. I chose this instead of a Raspberry Pi because Raspberry Pi prices are really bad right now.
- **I2S Class D Amplifier:** Handles the audio output to the speaker.
- **Speaker:** Allows Jarvis to speak its responses.
- **I2S MEMS Microphone:** Captures the user's voice input.

## Case Design

The case uses a three-piece design, with each piece serving a different purpose.

### Top Piece

The top piece is essentially just a top cover with a speaker mesh. This keeps the device looking nice while still allowing sound to pass through.

### Middle Piece

The middle piece holds the speaker itself. It has holes for heat-set inserts, which allow screws to be threaded in and used to mount the speaker securely.

### Bottom Piece

The bottom piece holds all of the electronics. This is where the Orange Pi, amplifier, and microphone live.

There are also ventilation slots along the sides of this section. These allow air to naturally flow through the case and carry away heat. I decided not to use fans because the electronics shouldn't generate all that much heat.

## Software and AI

Jarvis is designed to use cloud computing whenever possible, with a local backup protocol available when cloud services cannot be reached.

The software needs to handle several stages:

1. Capture the user's voice through the microphone.
2. Convert speech into text.
3. Send the text to an AI service.
4. Receive the AI's response.
5. Convert the response into speech.
6. Play the response through the speaker.

Although this sounds straightforward, speech recognition and getting all the different pieces working together make it a surprisingly complicated project.

## Challenges and What I Learned

One of the biggest things I've learned from this project is just how complicated voice-controlled AI assistants can be.

The basic concept is simple, but speech-to-text is not exactly an easy problem to solve. There are also several different hardware and software components that all need to communicate properly.

I'm also working on balancing cloud computing with local processing so that Jarvis can still have a backup option if the cloud isn't available.

## Bill of Materials (BOM)

| Part | Qty | Unit Cost | Total Cost | Vendor |
| --- | ---: | ---: | ---: | --- |
| [Orange Pi Zero 2W](https://www.aliexpress.us/item/3256805833810906.html?gatewayAdapt=glo2usa4itemAdapt) | 1 | $34.13 | $34.13 | AliExpress |
| [Adafruit I2S 3W Class D Amplifier Breakout](https://www.adafruit.com/product/3006) | 1 | $5.95 | $5.95 | Adafruit |
| [Speaker](https://www.adafruit.com/product/1314) | 1 | $1.95 | $1.95 | Adafruit |
| [Adafruit I2S MEMS Microphone Breakout](https://www.adafruit.com/product/3421) | 1 | $6.95 | $6.95 | Adafruit |
| [Custom Case](https://printlegion.hackclub.com/) | 1 | $10.00 | $10.00 | Print Legion |
| **Estimated tax and shipping** | — | — | **$30.00** | — |
| **Grand Total** | | | **$88.98** | |

*Tax and shipping are listed as $30.00, calculated from the supplied grand total minus the listed parts.*

## Project Gallery

### Case Design and Assembly

<img width="632" height="458" alt="Jarvis case design" src="https://github.com/user-attachments/assets/b56a261f-e34d-46c8-97aa-8394f31cad63" />

<img width="621" height="407" alt="Jarvis case design detail" src="https://github.com/user-attachments/assets/5de70bac-dd63-41bb-b420-c78080256ade" />

<img width="643" height="412" alt="Jarvis case design detail" src="https://github.com/user-attachments/assets/7903937c-f316-4a99-9910-44c61fc2448b" />

<img width="629" height="390" alt="Jarvis case design detail" src="https://github.com/user-attachments/assets/c1bced7c-83dd-473b-afe4-32f985259e50" />

<img width="494" height="381" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/d5ae3ddc-98fd-4600-bbab-d58eae0ff33d" />

<img width="1192" height="790" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/e96e8e3a-99dd-48de-abe5-b4c515d79361" />

<img width="796" height="578" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/478f0115-9ced-4023-93fa-4006a53b1ed3" />

<img width="833" height="599" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/63fe085b-b0fd-4f6b-8f22-d82c2a55f705" />

<img width="486" height="553" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/b0b8e348-c8c4-44d8-b129-5348e0320601" />

<img width="674" height="452" alt="Jarvis case design screenshot" src="https://github.com/user-attachments/assets/b9acd64e-ffe4-4d6a-badc-55e335f30e0f" />

### Additional Development Screenshots

<img width="558" height="445" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/bcaab10f-f3e7-45bf-bffc-991827042170" />

<img width="512" height="371" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/09cdc991-dc38-4994-9fba-8a7b56a3628c" />

<img width="652" height="361" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/129dffb5-ee41-4cd6-aa79-be860fd86142" />

<img width="1032" height="776" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/db32b5a0-976d-49c9-a5b5-a695b3a642f8" />

<img width="1014" height="637" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/fa626739-9f44-43fd-9604-9db07b196cea" />

<img width="988" height="643" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/e2cac050-8e98-45ed-9bcf-4f7a357a8072" />

<img width="943" height="606" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/25b2cc0d-c90c-4bab-86fa-37ea590e13dc" />

<img width="689" height="732" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/002246b6-076e-4d59-89de-6b2d009a6803" />

<img width="939" height="654" alt="Jarvis development screenshot" src="https://github.com/user-attachments/assets/c75f1b2d-a780-4891-9944-62cfa3fcc039" />
