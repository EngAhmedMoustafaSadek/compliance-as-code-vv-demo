Feature: Pulse rate alarms
  Abnormal pulse rates must be brought to the clinician's attention.

  @REQ-008 @RC-03
  Scenario Outline: A rate outside the default limits raises the matching alarm
    Given a clean pulsatile signal at <bpm> bpm sampled at 100 Hz for 10 seconds
    When the monitor evaluates the signal
    Then the "<alarm>" alarm is raised
    And a pulse rate is output

    Examples:
      | bpm | alarm     |
      | 35  | LOW_RATE  |
      | 70  | NONE      |
      | 160 | HIGH_RATE |

  @REQ-008 @RC-03
  Scenario: Configured limits are respected
    Given alarm limits of 80 to 120 bpm
    And a clean pulsatile signal at 70 bpm sampled at 100 Hz for 10 seconds
    When the monitor evaluates the signal
    Then the "LOW_RATE" alarm is raised
