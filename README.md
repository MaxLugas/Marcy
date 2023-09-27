# Marcy (Luna update)
Simple Voice Assistant made as an experiment using [Silero](https://github.com/snakers4/silero-models), [Vosk](https://pypi.org/project/vosk/), [Picovoice Porcupine Wake Word Detection](https://picovoice.ai/platform/porcupine/) & [ChatGPT](https://chat.openai.com/)


![image](https://static.wikia.nocookie.net/arrow/images/c/cb/Gideon_appearing_in_full-size_in_front_of_Barry%2C_Caitlin%2C_and_Cisco.png/revision/latest?cb=20150509005459)


# Installation
First, install the requirements, the `requirements.txt` file is just an output of `pip freeze` from my test venv 'k.<br>
Second, check `config.py` and set required values (api key, device index).<br>
Third, create `dev.env`.<br>
Next, run the `main.py` script and Voilà, as simple as that.<br><br>

And don't forget to put models of Vosk to main folder.<br>
You can get the latest from the [official website.](https://alphacephei.com/vosk/models)
<br>The one I was using is `small`.

# Python version
`3.11`.

# ToDo 
- Задержка воспроизведения звука на основе реальной длительности .wav файла
- Модель самого голосового ассистента для визуального эффекта
- Отслеживание движения головы пользователя
