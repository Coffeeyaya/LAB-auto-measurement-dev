#include <Servo.h>

Servo shutterServo;
const int servoPin = 9; 

void setup() {
  Serial.begin(9600); 
  
  // The 50ms timeout prevents lag but gives the USB cable 
  // plenty of time to deliver the full packet without desyncing.
  Serial.setTimeout(50); 
  
  shutterServo.attach(servoPin);
  
  // --- YOUR CRITICAL FIX ---
  // Instantly lock the servo to 90 degrees (OFF) the moment it powers on
  // so the laser is safely blocked while you load your Python scripts.
  shutterServo.write(90); 
}

void loop() {
  if (Serial.available() > 0) {
    
    // Read the ENTIRE message at once, automatically stopping at '\n'
    String input = Serial.readStringUntil('\n');
    
    // Convert that perfectly clean text string into a number
    int angle = input.toInt();
    
    // Safety check: force the angle to be between 0 and 180
    angle = constrain(angle, 0, 180);
    
    // Move the motor
    shutterServo.write(angle);
  }
}