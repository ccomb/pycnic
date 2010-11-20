
// set arduino pins
#define X_PULSE 4
#define X_DIRECTION 8
#define X_ENABLE 6

long x = 0; // current step position
int speed = 30000;   // default speed (steps/s) max = 32750
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
  
  for (int i=x; i!=target; i+=direction) {
    digitalWrite(X_PULSE, HIGH);
    delayMicroseconds(1000000/speed/2);
    digitalWrite(X_PULSE, LOW);
    delayMicroseconds(1000000/speed/2);
    digitalWrite(X_PULSE, HIGH);
    delayMicroseconds(1000000/speed/2);
    digitalWrite(X_PULSE, LOW);
    delayMicroseconds(1000000/speed/2);
    x = i;
  }
}

void setup() {
  direction = HIGH;
  pinMode(X_PULSE, OUTPUT);
  pinMode(X_DIRECTION, OUTPUT);
  pinMode(X_ENABLE, OUTPUT);
  Serial.begin(9600);
  //digitalWrite(X_DIRECTION, HIGH);
  //digitalWrite(X_ENABLE, HIGH);
}

void loop() {
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
