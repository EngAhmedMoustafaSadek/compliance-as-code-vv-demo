Feature: Signal quality
  A poor-quality signal must never produce a displayed pulse rate.

  @REQ-004 @RC-01
  Scenario: A flat signal is flagged
    Given a flat signal sampled at 100 Hz for 10 seconds
    When signal quality is assessed
    Then signal quality is inadequate because of "flatline"

  @REQ-005 @RC-01
  Scenario: A clipped signal is flagged
    Given a clipped pulsatile signal at 70 bpm sampled at 100 Hz for 10 seconds
    When signal quality is assessed
    Then signal quality is inadequate because of "clipping"

  @REQ-006 @RC-01
  Scenario: A signal with missing samples is flagged
    Given a pulsatile signal at 70 bpm with missing samples
    When signal quality is assessed
    Then signal quality is inadequate because of "dropout"

  @REQ-004 @REQ-005 @REQ-006 @RC-01
  Scenario: A clean signal is not flagged
    Given a clean pulsatile signal at 70 bpm sampled at 100 Hz for 10 seconds
    When signal quality is assessed
    Then signal quality is adequate

  @REQ-007 @RC-02
  Scenario Outline: No pulse rate is shown for a poor-quality signal
    Given a <condition> poor-quality signal
    When the monitor evaluates the signal
    Then no pulse rate is output
    And the "SIGNAL_QUALITY" alarm is raised

    Examples:
      | condition |
      | flat      |
      | clipped   |
      | dropout   |
