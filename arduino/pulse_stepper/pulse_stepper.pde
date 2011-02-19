
// set arduino pins
#define X_PULSE 4
#define X_DIRECTION 8
#define X_ENABLE 6
#define X_SWITCH 7

long x = 0; // current step position
int speed = 3000;   // default speed (steps/s) max = 32750
int direction = 1;

void moveTo(int target) {

  if (target == x) return;
  if (target > x) {
    direction = 1;
    digitalWrite(X_DIRECTION, HIGH);
  } else {
    direction = -1;
    digitalWrite(X_DIRECTION, LOW);
  }
  
  for (int i=x; i!=target; i+=direction)                                                                                                                                                                                                                   
}

void setup() {
  direction = HIGH;
  pinMode(X_PULSE, OUTPUT);
  pinMode(X_DIRECTION, OUTPUT);
  pinMode(X_ENABLE, OUTPUT);
  pinMode(X_SWITCH, INPUT);
  
  Serial.begin(9600);
  //digitalWrite(X_DIRECTION, HIGH);
  //digitalWrite(X_ENABLE, HIGH);
}

void loop() {
  
//  Serial.println(go);
  if (digitalRead(X_SWITCH) == HIGH) {
    Serial.println("move 1600");
    moveTo(1600);
    Serial.println("sleep");
    delay(500);
    Serial.println("move 0");
    moveTo(0);
    Serial.println("sleep");
    delay(500);
    Serial.println("move -1600");
    moveTo(-1600);
    Serial.println("sleep");
    delay(500);
    Serial.println("move 0");
    moveTo(0);
    delay(500);
  }
  
}
