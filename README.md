# BlinkWell

BlinkWell is an assistive software made to help people suffering from dry eye disease. It leverages blink detection through the user's webcam in order to promote healthy blinking habits. These can help alleviate dry eye symptoms as well as help treat the underlying cause of the disease.

The software is developed as a Computer Science undergraduate thesis in UFRJ (Universidade Federal do Rio de Janeiro) and is thereby available as an open source piece of software. 

Feedback is being collected and any input is greatly appreciated. [Google Forms link.](https://forms.gle/LfMF4KMoSud2wL46A)
![image](https://github.com/andregaeta/BlinkWell/assets/58143276/7dfb9b3f-5605-4df2-b54c-efb95f13833a)

## Features

BlinkWell comes with three main features.

### Blink Reminder

Your blink patterns are constantly analyzed and whenever necessary the app reminds you to blink.

![image](https://github.com/andregaeta/BlinkWell/assets/58143276/3bf33dc1-6837-4af5-9af3-906086ce4bb7)


### Break Reminder

The program reminds you to take breaks regularly.

![image](https://github.com/andregaeta/BlinkWell/assets/58143276/72593253-2ffa-4a31-8743-ccddd4756017)


### Stats Overlay

Your statistics are shown in a small overlay in your screen.

![image](https://github.com/andregaeta/BlinkWell/assets/58143276/235b52ad-50f3-4ad9-a4d0-08861715f064)


## Settings

#### Target Blink Rate

The amount of blinks per minute the software will help you maintain.

#### Blink Reminder Rigidness

Controls how much the blink rate will be projected into the future. More rigidness will result in lower weight for the user’s current blink rate, while less rigidness
will allow it to more heavily influence the calculated value.

#### Blink Threshold

How closed your eye needs to be in order to be detected as a blink. Lower values require fuller blinks, while higher values will parse lighter blinks.

#### Session Duration

How long you can be on screen until you're reminded to take a break, in minutes.

#### Snooze Duration

How long to snooze the break reminder, in minutes.

#### Break Duration

The mininum amount of time a break session will last, in seconds.
