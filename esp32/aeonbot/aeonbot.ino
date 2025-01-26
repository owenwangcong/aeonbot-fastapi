#include <Arduino.h>
#include <WiFi.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"
#include <Adafruit_NeoPixel.h>

#define LED_COUNT 8
#define LED_PIN 5 // Connect to the DIN pin of the WS2812 stick

// Define control pins connected to BTS7960
#define L_F_PWM 16  // Forward PWM control pin
#define L_B_PWM 17  // Reverse PWM control pin
#define R_F_PWM 25  // Forward PWM control pin
#define R_B_PWM 26  // Reverse PWM control pin

// Define the input pins we want to read
#define L_INPUT_PIN_1 18
#define L_INPUT_PIN_2 19
#define R_INPUT_PIN_1 34
#define R_INPUT_PIN_2 35

// PWM parameters
const uint32_t PWM_FREQUENCY  = 1000; // 1 kHz
const uint8_t  PWM_RESOLUTION = 8;    // 8-bit resolution (0-255)

// Define duty cycle values for partial speeds
const uint8_t DUTY_10  = 26;  // ~10%
const uint8_t DUTY_50  = 128; // ~50%
const uint8_t DUTY_75  = 192; // ~75%
const uint8_t DUTY_100 = 255; // 100%

// Add these constants after the PWM parameters
const unsigned long RAMP_TIME = 100;  // Time to reach target speed in milliseconds
const uint8_t RAMP_STEPS = 10;       // Number of steps for ramping

// Create a NeoPixel object
Adafruit_NeoPixel strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// WiFi credentials
const char* SSID     = "MyAccessPoint";
const char* PASSWORD = "StrongPassword123";
                
// MQTT Broker settings
#define MQTT_SERVER      "192.168.4.1"  // Your broker IP
#define MQTT_PORT        1883
#define MQTT_TOPIC      "motor/control"
#define MQTT_STATUS_TOPIC "motor/status"

// Create instances
WiFiClient client;
Adafruit_MQTT_Client mqtt(&client, MQTT_SERVER, MQTT_PORT);
Adafruit_MQTT_Subscribe motorControl = Adafruit_MQTT_Subscribe(&mqtt, MQTT_TOPIC);

// Add these global variables before handleMotorCommand
struct MotorState {
    int currentSpeed = 0;
    int targetSpeed = 0;
    unsigned long lastUpdate = 0;
    uint8_t forwardPin;
    uint8_t backwardPin;
    
    MotorState(uint8_t fPin, uint8_t bPin) : forwardPin(fPin), backwardPin(bPin) {}
    
    void setTarget(int speed) {
        targetSpeed = speed;
    }
    
    void update() {
        if (currentSpeed == targetSpeed) return;
        
        unsigned long now = millis();
        unsigned long timeElapsed = now - lastUpdate;
        int stepSize = (RAMP_TIME / RAMP_STEPS);
        
        if (timeElapsed >= stepSize) {
            lastUpdate = now;
            
            if (currentSpeed < targetSpeed) {
                currentSpeed += max(1, (targetSpeed - currentSpeed) / RAMP_STEPS);
                if (currentSpeed > targetSpeed) currentSpeed = targetSpeed;
            } else {
                currentSpeed -= max(1, (currentSpeed - targetSpeed) / RAMP_STEPS);
                if (currentSpeed < targetSpeed) currentSpeed = targetSpeed;
            }
            
            // Apply the new speed
            if (currentSpeed >= 0) {
                ledcWrite(forwardPin, currentSpeed);
                ledcWrite(backwardPin, 0);
            } else {
                ledcWrite(forwardPin, 0);
                ledcWrite(backwardPin, abs(currentSpeed));  // Use abs() for negative speeds
            }
        }
    }
};

// Initialize motor states
MotorState leftMotor(L_F_PWM, L_B_PWM);
MotorState rightMotor(R_F_PWM, R_B_PWM);

// Replace the handleMotorCommand function
void handleMotorCommand(char *data, uint16_t len) {
    String message = String(data);
    Serial.print("Received command: ");
    Serial.println(message);
    
    int colonIndex = message.indexOf(':');
    String command = message;
    int speed = DUTY_100; // Default to full speed
    int turnSpeed = DUTY_75; // Default to 75% for turns
    
    if (colonIndex != -1) {
        command = message.substring(0, colonIndex);
        speed = message.substring(colonIndex + 1).toInt();
        speed = map(speed, 0, 100, 0, 255);
    }
    
    // Store current speeds to enable smooth transitions
    int leftTarget = leftMotor.currentSpeed;
    int rightTarget = rightMotor.currentSpeed;
    
    if (command == "forward") {
        leftTarget = speed;
        rightTarget = speed;
    } 
    else if (command == "backward") {
        leftTarget = -speed;
        rightTarget = -speed;
    }
    else if (command == "left") {
        leftTarget = -turnSpeed;
        rightTarget = turnSpeed;
    }
    else if (command == "right") {
        leftTarget = turnSpeed;
        rightTarget = -turnSpeed;
    }
    else if (command == "stop") {
        leftTarget = 0;
        rightTarget = 0;
    }
    
    // Apply new targets with ramping
    leftMotor.setTarget(leftTarget);
    rightMotor.setTarget(rightTarget);
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\nMotor Control System Starting...");

    // Initialize the NeoPixel library
    strip.begin();
    strip.show(); // Initialize all pixels to 'off'
    strip.setBrightness(50); // Adjust brightness (0-255)
    blinkAll(strip.Color(255, 0, 0)); // Red blink

    // Initialize PWM using ledcAttach
    ledcAttach(L_F_PWM, PWM_FREQUENCY, PWM_RESOLUTION);
    ledcAttach(L_B_PWM, PWM_FREQUENCY, PWM_RESOLUTION);
    ledcAttach(R_F_PWM, PWM_FREQUENCY, PWM_RESOLUTION);
    ledcAttach(R_B_PWM, PWM_FREQUENCY, PWM_RESOLUTION); 
    
    // Initialize input pins
    pinMode(L_INPUT_PIN_1, INPUT);
    pinMode(L_INPUT_PIN_2, INPUT);
    pinMode(R_INPUT_PIN_1, INPUT);
    pinMode(R_INPUT_PIN_2, INPUT);

    // Connect to WiFi
    Serial.printf("Connecting to WiFi: %s ", SSID);
    WiFi.begin(SSID, PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
      blinkAll(strip.Color(0, 0, 255)); // Green blink
    }
    Serial.println("\nWiFi connected!");
    setAllOn(strip.Color(0, 255, 0));
    
    // Print network information
    Serial.println("\nNetwork Information:");
    Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Subnet Mask: %s\n", WiFi.subnetMask().toString().c_str());
    Serial.printf("Gateway IP: %s\n", WiFi.gatewayIP().toString().c_str());
    Serial.printf("DNS Server: %s\n", WiFi.dnsIP().toString().c_str());
    Serial.printf("MAC Address: %s\n", WiFi.macAddress().c_str());
    Serial.printf("MQTT Broker: %s:%d\n\n", MQTT_SERVER, MQTT_PORT);

    // Setup MQTT subscription
    motorControl.setCallback(handleMotorCommand);
    mqtt.subscribe(&motorControl);
}

void MQTT_connect() {
    int8_t ret;

    // Stop if already connected
    if (mqtt.connected()) {
        return;
    }

    Serial.print("Connecting to MQTT... ");
    
    // Set keep-alive to 60 seconds
    mqtt.setKeepAliveInterval(60000);
    
    uint8_t retries = 3;
    while ((ret = mqtt.connect()) != 0) { // connect will return 0 for connected
        Serial.println(mqtt.connectErrorString(ret));
        Serial.println("Retrying MQTT connection in 5 seconds...");
        mqtt.disconnect();
        delay(5000);  // wait 5 seconds
        retries--;
        if (retries == 0) {
            // Instead of waiting forever, just return and let the loop try again
            Serial.println("Failed to connect to MQTT, will try again later");
            return;
        }
    }
    Serial.println("MQTT Connected!");
}

bool isMQTTConnected() {
    return mqtt.connected();  // Simply check if MQTT is connected
}

void loop() {
    static unsigned long lastMotorUpdate = 0;
    const unsigned long MOTOR_UPDATE_INTERVAL = 10; // Update every 10ms
    static unsigned long lastMqttCheck = 0;
    static unsigned long lastInputCheck = 0;
    static uint8_t failedPings = 0;
    const unsigned long MQTT_CHECK_INTERVAL = 5000;  // Check MQTT every 5 seconds
    const unsigned long INPUT_CHECK_INTERVAL = 100;  // Check inputs every 100ms
    const uint8_t MAX_FAILED_PINGS = 3;  // Number of failed pings before disconnect
    
    unsigned long currentMillis = millis();
    
    // Handle motor speed updates
    if (currentMillis - lastMotorUpdate >= MOTOR_UPDATE_INTERVAL) {
        lastMotorUpdate = currentMillis;
        leftMotor.update();
        rightMotor.update();
    }

    // Handle MQTT connection and maintenance
    if (currentMillis - lastMqttCheck >= MQTT_CHECK_INTERVAL) {
        lastMqttCheck = currentMillis;
        
        if (!mqtt.connected()) {
            MQTT_connect();
        } else {
            // Only ping if connected
            if (!mqtt.ping()) {
                failedPings++;
                Serial.printf("Failed ping %d/%d\n", failedPings, MAX_FAILED_PINGS);
                if (failedPings >= MAX_FAILED_PINGS) {
                    Serial.println("Too many failed pings, disconnecting");
                    mqtt.disconnect();
                    failedPings = 0;
                }
            } else {
                failedPings = 0;  // Reset failed pings counter on successful ping
            }
        }

        // Update LED status based on MQTT connection
        if (mqtt.connected()) {
            setAllOn(strip.Color(0, 255, 0));  // Green when connected
        } else {
            setAllOn(strip.Color(255, 0, 0));  // Red when disconnected
        }
    }

    // Process any incoming MQTT messages
    mqtt.processPackets(10);  // Reduced from 10000 to 10ms to be more responsive

    // Read and publish input pin states at regular intervals
    if (currentMillis - lastInputCheck >= INPUT_CHECK_INTERVAL) {
        lastInputCheck = currentMillis;
        
        int input1 = digitalRead(L_INPUT_PIN_1);
        int input2 = digitalRead(L_INPUT_PIN_2);
        int input3 = digitalRead(R_INPUT_PIN_1);
        int input4 = digitalRead(R_INPUT_PIN_2);
        
        // Create JSON-like status message
        char statusMsg[50];
        snprintf(statusMsg, sizeof(statusMsg), 
                "{\"L1\":%d,\"L2\":%d,\"R1\":%d,\"R2\":%d}", 
                input1, input2, input3, input4);
                
        // Publish status if connected
        if (mqtt.connected()) {
            mqtt.publish(MQTT_STATUS_TOPIC, statusMsg);
        }
        
        Serial.printf("Input1: %d, Input2: %d, Input3: %d, Input4: %d\n", 
                     input1, input2, input3, input4);
    }
}

// Fill the strip one LED at a time with a color
void colorWipe(uint32_t color, int wait) {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, color);
    strip.show();
    delay(wait);
  }
}

void setAllOn(uint32_t color) {
  for (int i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, color);
  }
  strip.show();
}

void blinkAll(uint32_t color) {
  static bool ledState = false;
  static unsigned long previousMillis = 0;
  const long blinkInterval = 300;  // Blink every 500ms
  
  unsigned long currentMillis = millis();
  
  if (currentMillis - previousMillis >= blinkInterval) {
    previousMillis = currentMillis;
    
    if (ledState) {
      for (int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, 0);  // Turn off
      }
    } else {
      for (int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, color);  // Turn on
      }
    }
    strip.show();  // Update the LEDs
    ledState = !ledState;
  }
}

