(* Исправленный вариант: инициализация, anti-windup, оба предела,
   обработка аварийного сигнала. Должен пройти проверку. *)
PROGRAM PumpControl
VAR_INPUT
    Setpoint : REAL;
    Feedback : REAL;
    EStop    : BOOL;
END_VAR
VAR
    integral : REAL := 0.0;
    u        : REAL := 0.0;
    e        : REAL := 0.0;
    OUT_MAX  : REAL := 100.0;
    OUT_MIN  : REAL := 0.0;
END_VAR
    IF EStop THEN
        Output := OUT_MIN;
    ELSE
        e := Setpoint - Feedback;
        integral := integral + e;
        u := integral;
        IF u > OUT_MAX THEN
            u := OUT_MAX;
            integral := OUT_MAX;   (* anti-windup: зажимаем интеграл *)
        ELSIF u < OUT_MIN THEN
            u := OUT_MIN;
            integral := OUT_MIN;
        END_IF;
        Output := u;
    END_IF;
END_PROGRAM
