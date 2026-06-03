(* Небезопасное управление насосом — пример того, что мог бы выдать ИИ.
   Содержит сразу несколько типичных ошибок. *)
PROGRAM PumpControl
VAR_INPUT
    Setpoint : REAL;
    Feedback : REAL;
END_VAR
VAR
    u : REAL;        (* состояние без инициализации *)
    e : REAL;
END_VAR
    e := Setpoint - Feedback;
    u := u + 1.0 * e;          (* интеграл без ограничения, нет anti-windup *)
    IF u > 100.0 THEN          (* магическое число, только верхний предел *)
        Output := 100.0;
    ELSE
        Output := u;
    END_IF;
    ESD_Valve := TRUE;         (* прямая запись в защищённый тег *)
END_PROGRAM
