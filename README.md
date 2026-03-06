# OK Micro Dock

<img align="right" width="300" alt="image" src="https://github.com/user-attachments/assets/c98b8e6e-953a-41f8-bec4-78f9ba202b05"/>

This repository includes hardware designs and a software driver library for a "dock" baseboard for standard-format microcontroller boards ([Adafruit Feather](https://www.adafruit.com/category/943)). This dock adds a power supply, I/O screw terminals, and a tiny screen/button interface to the micro. Also included are some auxiliary carrier and utility boards.

These designs are all intended for "prod-otyping" environments like escape rooms which benefit from flexible but robust wiring, status observability, and quick part swapping.

For simple screw terminal breakout, first consider these more professional offerings...
- Adafruit: Terminal Block for [Feather](https://www.adafruit.com/product/2926), ScrewShield for [Uno](https://www.adafruit.com/product/196)
- Arduino official: [Nano Screw Terminal Adapter](https://store-usa.arduino.cc/products/nano-screw-terminal)
- DFRobot: [Screw](https://www.dfrobot.com/product-659.html) and [Screwless](https://www.dfrobot.com/product-659.html) Shields for Uno, Terminal Shield for [Uno](https://www.dfrobot.com/product-2576.html) and [Mega](https://www.dfrobot.com/product-2574.html)
- Electronics-Salon: [many terminal block breakout options](https://www.electronics-salon.com/collections/arduino-gpio-breakout-board-696)
- Treedix: Screw Terminal Block for [Uno](https://treedix.com/products/treedix-screw-terminal-block-breakout-module-board-for-arduino-uno-r3) and [Mega](https://treedix.com/products/treedix-screw-terminal-block-breakout-moduleor-for-arduino-mega-2560-r3), Spring Terminal Block for [Uno](https://treedix.com/products/treedix-spring-terminal-block-breakout-module-expansion-board-compatible-with-arduino-uno-r3)
- 52Pi: Terminal Shield for [Uno](https://52pi.com/products/ep-0130), [Mega](https://52pi.com/products/screw-terminal-block-breakout-board-hat-with-reset-button-and-led-indicator-gpio-expansion-board-breakout-module-for-arduino-mega-2560-r3), and [Pico RP2040](https://52pi.com/products/52pi-screw-terminal-expansion-board-for-raspberry-pi-pico)
- or just [solder screw terminals to the bottom of a board](https://www.adafruit.com/product/3173)!

What this dock adds (besides a questionable supply chain) is
- a switching power supply that takes 4.2V to 60V(!) (diode-mixed with USB input) to deliver 2A of 3.3V
- a tiny display (with an easy driver library), so you can see what your board is "thinking"
- tiny buttons (with an easy driver library), so you can configure board settings as needed
- two [QWIIC/Stemma QT](https://www.sparkfun.com/qwiic) connectors tied to SDA/SCL (with pullups)
- it's a base board, not a shield, so you can swap the controller while leaving hookups in place
- it's a compact board that doesn't take more space than needed
- nice generous M3 screw holes

Collectively this is useful to me for random builds in the escape room/immersive industry. Your mileage will surely vary.
