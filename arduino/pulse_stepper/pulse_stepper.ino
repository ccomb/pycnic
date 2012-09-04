
// set arduino pins
#define X_PULSE 4
#define X_PULSE_PORT PORTD
#define X_DIRECTION 8
#define X_ENABLE 6
#define X_SWITCH 5

#define X_PULSE_BIT (1<<4)

long x = 0; // current step position
int speed = 8000;   // default speed (steps/s) max = 32750
int direction = 1;
int go = 1;

int rampsteps = 200;
int curspeed = 0;

void moveTo(int target, boolean ramp) {

  if (target == x) return;
  if (target > x) {
    direction = 1;
    digitalWrite(X_DIRECTION, HIGH);
  } else {
    direction = -1;
    digitalWrite(X_DIRECTION, LOW);
  }
  int cur = 0;
  for (int i=x; i!=target+direction; i+=direction) {
    curspeed = speed;
    if (ramp && (cur <= rampsteps)) {
      curspeed = (speed / (float) rampsteps) * cur;
    }
    //digitalWrite(X_PULSE, HIGH);
    X_PULSE_PORT |= X_PULSE_BIT;
    delayMicroseconds(1000000/curspeed/2);
    //digitalWrite(X_PULSE, LOW);
    X_PULSE_PORT &=~ X_PULSE_BIT;
    delayMicroseconds(1000000/curspeed/2);
    x = i;
    cur ++;
  }
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

char curval;

void check_messages() {
  if (Serial.available()) {
    curval = Serial.read();
    boolean ramp = false;
    if (curval == 'E') {
      x = 0;
    }
    if (curval == 'R') {
      while (!Serial.available()) {};
      curval = Serial.read();
      if (curval == 'X') {
        Serial.println(x);
      }
      if (curval == 'I') {
        Serial.println(String("arduino"));
      }
      if (curval == 'V') {
        while (!Serial.available()) {};
        curval = Serial.read();
        if (curval == 'H') {   
          Serial.println(String("0"));
        }
        if (curval == 'L') {   
          Serial.println(String("1"));
        }
      }
    }
    if (curval == 'V') {
      while (!Serial.available()) {};
      curval = Serial.read();
      if (curval == 'V') {
        speed = Serial.parseInt();
      }
    }
    if (curval == 'W') {
      while (!Serial.available()) {};
      curval = Serial.read();
      if (curval == 'X') {
        x = Serial.parseInt();
      }
    }
    if (curval == 'L') {
      while (!Serial.available()) {};
      curval = Serial.read();
      if (curval == 'L')
      {
        ramp = true;
        while (!Serial.available()) {};
        curval = Serial.read();
      }
      
      if (curval == 'X') {
        /*String value = String("");
        for (int i = 0; i < 5; i ++) {
          while (!Serial.available()) {};
          value += (char) Serial.read();
        }
        int xval = value.toInt();*/
        int xval = Serial.parseInt();
        moveTo(xval, ramp);
      }
    }
  }
  
  
}

void loop() {
  
  check_messages();
  /*
  go = digitalRead(X_SWITCH);
  Serial.println(go);
  //if (go == HIGH) {
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
  //}*/
  delay(50);
}
